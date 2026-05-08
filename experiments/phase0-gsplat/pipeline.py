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
    )
    .pip_install(
        "gsplat==1.4.0",
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
    gpu=GPU_TYPE,
    timeout=TIMEOUT_S,
    volumes={"/workspace": volume},
)
def prepare_frames_and_sfm(scene_name: str, video_filename: str, fps: int = 2) -> dict:
    """Extract frames from /workspace/{scene_name}/{video_filename} via ffmpeg,
    then run COLMAP feature extraction + matching + sparse reconstruction.

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


@app.local_entrypoint()
def main(video_path: str = "input/sample.mov", scene_name: str = "sample", fps: int = 2) -> None:
    """Phase 0 pipeline entry — currently runs SfM only (Tasks 5+ extend this)."""
    src = Path(video_path)
    assert src.exists(), f"video not found: {src}"

    dest_filename = f"input{src.suffix}"
    print(f">>> Uploading {src} as {scene_name}/{dest_filename}")
    with volume.batch_upload(force=True) as batch:
        batch.put_file(src, f"{scene_name}/{dest_filename}")

    print(">>> Running SfM step")
    sfm_metrics = prepare_frames_and_sfm.remote(scene_name, dest_filename, fps)

    print(json.dumps(sfm_metrics, indent=2, ensure_ascii=False))
