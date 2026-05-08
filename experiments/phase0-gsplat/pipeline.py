"""
Phase 0 PoC: video → 3D Gaussian Splatting pipeline on Modal.

Reads a video from local, uploads to a Modal Volume, runs the full pipeline
on GPU, and downloads the resulting PLY/SPZ + metrics back to local.

Grown task-by-task per the plan at
docs/superpowers/plans/2026-05-08-gsplat-pipeline-phase-0.md
- Task 3: Image, Volume, smoke_test
- Task 4: prepare_frames_and_sfm (ffmpeg + COLMAP)
- Task 5+: extends with gsplat training, SPZ conversion, downloads
"""
from __future__ import annotations
import json
import os
import subprocess
import time
from pathlib import Path

import modal

APP_NAME = "gsplat-poc"
VOLUME_NAME = "gsplat-poc-vol"
GPU_TYPE = "A10G"  # 24 GB VRAM, ~$1.10/hr — Phase 0 で十分
TIMEOUT_S = 60 * 60  # 1 hour cap for a single scene

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install(
        "git", "wget", "build-essential", "cmake",
        "ffmpeg",
        "colmap",
        # clang/clang++ needed by fused-ssim / fused-bilagrid CUDA extension builds
        "clang",
        # NOTE: nodejs/npm from Ubuntu 22.04 apt gives Node v12 which is too
        # old for @playcanvas/splat-transform (requires Node >=18). We install
        # Node 20 LTS via NodeSource below instead.
        "ca-certificates", "curl", "gnupg",
    )
    .run_commands(
        # Install Node 20 LTS via NodeSource (Ubuntu 22.04 apt ships Node 12)
        "mkdir -p /etc/apt/keyrings",
        "curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key"
        " | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg",
        "echo 'deb [signed-by=/etc/apt/keyrings/nodesource.gpg]"
        " https://deb.nodesource.com/node_20.x nodistro main'"
        " > /etc/apt/sources.list.d/nodesource.list",
        "apt-get update && apt-get install -y nodejs",
    )
    .pip_install(
        "torch==2.4.0",
        "torchvision",
        "numpy<2",
        "Pillow",
        "tqdm",
        "plyfile",
        "scikit-image",
        "scipy",
        # wheel: pycolmap (setuptools-based) needs bdist_wheel at install time
        "wheel",
    )
    .pip_install(
        "gsplat==1.4.0",
    )
    .run_commands(
        # Pre-clone gsplat repo + install examples deps at image build time
        # so they are cached across container starts (saves ~3-5 min/run on A10G).
        "git clone --depth 1 --branch v1.4.0 "
        "https://github.com/nerfstudio-project/gsplat.git /opt/gsplat",
        "pip install --no-build-isolation -r /opt/gsplat/examples/requirements.txt",
    )
    .run_commands(
        "npm install -g @playcanvas/splat-transform",
    )
)


@app.function(image=image, timeout=120)
def smoke_test() -> str:
    """Trivial function to force the image to build during Task 3.
    Verifies that key tools are installed inside the image.
    Returns a JSON string to avoid cloudpickle needing torch locally."""
    import json
    import shutil
    import subprocess
    info: dict = {"ok": True}
    for tool in ["ffmpeg", "colmap", "node", "splat-transform"]:
        info[tool] = shutil.which(tool)
    info["python"] = subprocess.check_output(["python", "--version"], text=True).strip()
    try:
        import torch
        info["torch_version"] = str(torch.__version__)
        info["torch_cuda_compiled_version"] = str(torch.version.cuda)
        # Note: smoke_test runs without a GPU attached, so cuda.is_available() will be False.
        # We only check the torch build sees a CUDA runtime version.
    except Exception as exc:
        info["torch_error"] = repr(exc)
    info["timestamp"] = int(time.time())
    return json.dumps(info)


@app.function(
    image=image,
    # No gpu= — this function uses CPU SIFT and ffmpeg only
    timeout=TIMEOUT_S,
    volumes={"/workspace": volume},
)
def prepare_frames_and_sfm(scene_name: str, video_filename: str, fps: int = 2) -> dict:
    """Extract frames + run COLMAP SfM. CPU-only (no GPU SIFT in headless Modal containers).

    Reads /workspace/{scene_name}/{video_filename} via ffmpeg,
    then runs COLMAP feature extraction + matching + sparse reconstruction.

    Returns a dict of metrics (timings, frame count, COLMAP analyzer output).
    """
    base = Path("/workspace") / scene_name
    video = base / video_filename
    assert video.exists(), f"video not found: {video}"

    frames_dir = base / "frames"
    sfm_dir = base / "sfm"
    sparse_dir = sfm_dir / "sparse"
    frames_dir.mkdir(parents=True, exist_ok=True)
    sfm_dir.mkdir(parents=True, exist_ok=True)
    sparse_dir.mkdir(parents=True, exist_ok=True)

    # --- SfM skip optimization: reuse cached reconstruction if present ---
    sentinel = sfm_dir / "sparse" / "0" / "cameras.bin"
    if sentinel.exists():
        print(f"[sfm] skip: existing reconstruction at {sentinel}")
        frames_count = len(list(frames_dir.glob("frame_*.jpg"))) if frames_dir.exists() else 0
        return {
            "scene_name": scene_name,
            "video_filename": video_filename,
            "fps": fps,
            "frames_count": frames_count,
            "frame_extract_sec": 0,
            "sfm_sec": 0,
            "colmap_analyzer_output": "skipped (reconstruction already exists in Volume)",
            "skipped": True,
        }

    # --- Frame extraction ---
    t0 = time.time()
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video),
            "-vf", f"fps={fps}",
            "-qscale:v", "2",
            str(frames_dir / "frame_%05d.jpg"),
        ],
        check=True,
    )
    frame_extract_sec = time.time() - t0
    frames_count = len(list(frames_dir.glob("frame_*.jpg")))
    assert frames_count > 0, f"ffmpeg produced no frames for {video}"
    print(f"[frames] extracted {frames_count} frames in {frame_extract_sec:.1f}s")

    # --- COLMAP SfM ---
    # NOTE: COLMAP's GPU SIFT path requires an OpenGL context which is not
    # available in Modal's headless GPU containers. Fall back to CPU SIFT
    # (use_gpu=0). The GPU is still used by gsplat training in later tasks.
    colmap_env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}

    sfm_t0 = time.time()

    # Feature extraction (CPU SIFT — no OpenGL context available in container)
    subprocess.run(
        [
            "colmap", "feature_extractor",
            "--database_path", str(sfm_dir / "database.db"),
            "--image_path", str(frames_dir),
            "--ImageReader.single_camera", "1",
            "--SiftExtraction.use_gpu", "0",
        ],
        check=True,
        env=colmap_env,
    )
    print("[colmap] feature_extractor done")

    # Sequential matching (CPU SIFT) — appropriate for video frames (temporal order).
    # Exhaustive matching was too slow for 135 frames (9 blocks × ~100s each).
    subprocess.run(
        [
            "colmap", "sequential_matcher",
            "--database_path", str(sfm_dir / "database.db"),
            "--SiftMatching.use_gpu", "0",
        ],
        check=True,
        env=colmap_env,
    )
    print("[colmap] sequential_matcher done")

    # Mapper
    subprocess.run(
        [
            "colmap", "mapper",
            "--database_path", str(sfm_dir / "database.db"),
            "--image_path", str(frames_dir),
            "--output_path", str(sparse_dir),
        ],
        check=True,
        env=colmap_env,
    )
    sfm_sec = time.time() - sfm_t0
    print(f"[colmap] SfM done (feature_extractor + matcher + mapper) in {sfm_sec:.1f}s")

    # Verify outputs
    # COLMAP numbers sub-models 0, 1, … in descending size order. We always pick "0".
    # If the scene splits into multiple models, sub-models 1+ are silently ignored here.
    cameras_bin = sparse_dir / "0" / "cameras.bin"
    images_bin = sparse_dir / "0" / "images.bin"
    assert cameras_bin.exists(), f"cameras.bin not found: {cameras_bin}"
    assert images_bin.exists(), f"images.bin not found: {images_bin}"

    # Model analyzer
    analyzer_result = subprocess.run(
        ["colmap", "model_analyzer", "--path", str(sparse_dir / "0")],
        capture_output=True,
        text=True,
        check=True,
        env=colmap_env,
    )
    # Last 2000 chars: COLMAP's analyzer prints the Cameras/Images/Points summary at the end.
    colmap_analyzer_output = (analyzer_result.stdout + analyzer_result.stderr)[-2000:]
    print("[colmap] model_analyzer output:")
    print(colmap_analyzer_output)

    volume.commit()

    return {
        "scene_name": scene_name,
        "video_filename": video_filename,
        "fps": fps,
        "frames_count": frames_count,
        "frame_extract_sec": round(frame_extract_sec, 2),
        "sfm_sec": round(sfm_sec, 2),
        "colmap_analyzer_output": colmap_analyzer_output,
    }


@app.function(
    image=image,
    gpu=GPU_TYPE,
    timeout=TIMEOUT_S,
    volumes={"/workspace": volume},
)
def train_gsplat(scene_name: str, max_steps: int = 30000) -> dict:
    """gsplat の simple_trainer を使って 3DGS を学習する。
    入力: /workspace/{scene_name}/{frames,sfm/sparse/0/}
    出力: /workspace/{scene_name}/output.ply
    返り値: 計測値 dict（プリミティブ型のみ）。
    """
    base = Path("/workspace") / scene_name

    # Verify SfM outputs exist
    sfm_sparse_0 = base / "sfm" / "sparse" / "0"
    assert (sfm_sparse_0 / "cameras.bin").exists(), (
        f"cameras.bin not found at {sfm_sparse_0} — run prepare_frames_and_sfm first"
    )

    out_dir = base / "gsplat_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # gsplat repo + examples/requirements.txt are pre-installed at image build time
    # (see .run_commands in the image definition above) — no clone needed at runtime.
    gsplat_dir = Path("/opt/gsplat")
    # (No clone, no pip install — both done at image build time)

    # --- Run simple_trainer ---
    # simple_trainer expects {data_dir}/sparse/0/ for COLMAP data and
    # {data_dir}/images/ (or similar) for source images.
    # Our layout puts COLMAP under {base}/sfm/sparse/0/ and frames under
    # {base}/frames/.  We symlink to match simple_trainer's expected layout:
    #   {base}/sfm/sparse  →  already exists
    #   {base}/sfm/images  →  symlink to {base}/frames
    sfm_dir = base / "sfm"
    images_link = sfm_dir / "images"
    # Refresh any existing symlink to ensure correct target on warm containers
    if images_link.is_symlink():
        images_link.unlink()
    if not images_link.exists():
        images_link.symlink_to(base / "frames")
        print(f"[gsplat] created symlink {images_link} → {base / 'frames'}")

    log_path = out_dir / "train.log"
    train_cmd = [
        "python", "examples/simple_trainer.py", "default",
        "--data_dir", str(sfm_dir),  # simple_trainer looks for sparse/0/ here
        "--data_factor", "1",
        "--result_dir", str(out_dir),
        "--max_steps", str(max_steps),
        "--save_steps", str(max_steps),
        "--eval_steps", str(max_steps),
        "--disable_viewer",
    ]
    print(f"[gsplat] running: {' '.join(train_cmd)}")
    train_t0 = time.time()
    with open(log_path, "w") as log_f:
        result = subprocess.run(
            train_cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            cwd=str(gsplat_dir),
        )
    train_sec = time.time() - train_t0
    print(f"[gsplat] training finished in {train_sec:.1f}s (returncode={result.returncode})")

    if result.returncode != 0:
        # Dump last 100 lines of log to help debug
        with open(log_path) as lf:
            lines = lf.readlines()
        print("[gsplat] last 100 lines of train.log:")
        print("".join(lines[-100:]))
        raise RuntimeError(f"simple_trainer.py exited with code {result.returncode}")

    # --- Convert .pt checkpoint → standard 3DGS PLY ---
    ckpt_candidates = sorted((out_dir / "ckpts").glob("ckpt_*_rank0.pt"))
    if not ckpt_candidates:
        raise RuntimeError(f"No .pt checkpoint found under {out_dir / 'ckpts'}")
    ckpt_path = ckpt_candidates[-1]
    dest_ply = base / "output.ply"
    ply_size_bytes = _checkpoint_to_ply(ckpt_path, dest_ply)

    # --- Parse PSNR lines from log tail ---
    with open(log_path) as lf:
        all_lines = lf.readlines()
    tail_lines = all_lines[-200:]
    psnr_log_tail = [
        line.rstrip()
        for line in tail_lines
        if "psnr" in line.lower()
    ]

    volume.commit()

    return {
        "scene": scene_name,
        "train_sec": round(train_sec, 2),
        "max_steps": max_steps,
        "ply_size_bytes": ply_size_bytes,
        "psnr_log_tail": psnr_log_tail,
    }


def _checkpoint_to_ply(ckpt_path: Path, dest_path: Path) -> int:
    """Convert a gsplat .pt checkpoint to a standard inria/3DGS PLY file.

    Imports torch/numpy/plyfile inside the function body so they are only
    resolved when called from inside a Modal container (they are not present
    on the local machine).

    Args:
        ckpt_path: Path to the gsplat checkpoint file (ckpt_*_rank0.pt).
        dest_path: Destination path for the output PLY file.

    Returns:
        Size of the written PLY file in bytes.
    """
    # Imports are kept local — torch/numpy only exist inside the Modal container.
    import numpy as np
    import torch
    from plyfile import PlyData, PlyElement

    print(f"[gsplat] converting checkpoint → PLY: {ckpt_path}")
    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    if "splats" not in ckpt:
        raise RuntimeError(f"Unexpected checkpoint structure. Top-level keys: {list(ckpt.keys())}")
    splats = ckpt["splats"]

    means = splats["means"].float().numpy()          # [N, 3]
    scales = splats["scales"].float().numpy()        # [N, 3] — stored as log(scale)
    quats = splats["quats"].float().numpy()          # [N, 4]  w,x,y,z or x,y,z,w
    opacities = splats["opacities"].float().numpy()  # [N,]   — stored as logit
    sh0 = splats["sh0"].float().numpy()              # [N, 1, 3]
    shN = splats["shN"].float().numpy()              # [N, K, 3]

    N = means.shape[0]
    normals = np.zeros((N, 3), dtype=np.float32)

    # SH coefficients: flatten to [N, (1+K)*3] then split into dc/rest
    sh_all = np.concatenate([sh0, shN], axis=1)  # [N, 1+K, 3]
    sh_dc = sh_all[:, :1, :]                      # [N, 1, 3]
    sh_rest = sh_all[:, 1:, :]                    # [N, K, 3]

    # Build PLY vertex data following inria 3DGS convention
    n_sh_rest = sh_rest.shape[1] * 3
    dtype_list = (
        [("x", "f4"), ("y", "f4"), ("z", "f4")]
        + [("nx", "f4"), ("ny", "f4"), ("nz", "f4")]
        + [(f"f_dc_{i}", "f4") for i in range(3)]
        + [(f"f_rest_{i}", "f4") for i in range(n_sh_rest)]
        + [("opacity", "f4")]
        + [(f"scale_{i}", "f4") for i in range(3)]
        + [(f"rot_{i}", "f4") for i in range(4)]
    )
    vertex_data = np.empty(N, dtype=dtype_list)
    vertex_data["x"] = means[:, 0]
    vertex_data["y"] = means[:, 1]
    vertex_data["z"] = means[:, 2]
    vertex_data["nx"] = normals[:, 0]
    vertex_data["ny"] = normals[:, 1]
    vertex_data["nz"] = normals[:, 2]
    vertex_data["f_dc_0"] = sh_dc[:, 0, 0]
    vertex_data["f_dc_1"] = sh_dc[:, 0, 1]
    vertex_data["f_dc_2"] = sh_dc[:, 0, 2]
    sh_rest_flat = sh_rest.reshape(N, -1)  # [N, K*3]
    for i in range(n_sh_rest):
        vertex_data[f"f_rest_{i}"] = sh_rest_flat[:, i]
    vertex_data["opacity"] = opacities
    for i in range(3):
        vertex_data[f"scale_{i}"] = scales[:, i]
    for i in range(4):
        vertex_data[f"rot_{i}"] = quats[:, i]

    ply_el = PlyElement.describe(vertex_data, "vertex")
    PlyData([ply_el]).write(str(dest_path))
    ply_size_bytes = dest_path.stat().st_size
    print(f"[gsplat] PLY written: {dest_path} ({ply_size_bytes} bytes, {N} gaussians)")
    return ply_size_bytes


@app.local_entrypoint()
def main(
    video_path: str = "input/sample.mov",
    scene_name: str = "sample",
    fps: int = 2,
    max_steps: int = 30000,
) -> None:
    """Phase 0 pipeline entry — SfM → gsplat training."""
    src = Path(video_path)
    assert src.exists(), f"video not found: {src}"

    dest_filename = f"input{src.suffix}"
    print(f">>> Uploading {src} as {scene_name}/{dest_filename}")
    with volume.batch_upload(force=True) as batch:
        batch.put_file(src, f"{scene_name}/{dest_filename}")

    print(">>> Running SfM step")
    sfm_metrics = prepare_frames_and_sfm.remote(scene_name, dest_filename, fps)
    print(json.dumps(sfm_metrics, indent=2, ensure_ascii=False))

    print(f">>> Running gsplat training ({max_steps} steps)")
    train_metrics = train_gsplat.remote(scene_name, max_steps=max_steps)
    print(json.dumps(train_metrics, indent=2, ensure_ascii=False))
