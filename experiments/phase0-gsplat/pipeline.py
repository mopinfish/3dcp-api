"""
Phase 0 PoC: video → 3D Gaussian Splatting pipeline on Modal.

Reads a video from local, uploads to a Modal Volume, runs the full pipeline
on GPU, and downloads the resulting PLY/SPZ + metrics back to local.

This file is grown task-by-task per the plan at
docs/superpowers/plans/2026-05-08-gsplat-pipeline-phase-0.md
Task 3 only adds the Image and Volume definitions plus a tiny smoke-test
function used to force the image build during this task.
"""
from __future__ import annotations
import time

import modal

APP_NAME = "gsplat-poc"
VOLUME_NAME = "gsplat-poc-vol"
GPU_TYPE = "A10G"  # 24 GB VRAM, ~$1.10/hr — Phase 0 で十分
TIMEOUT_S = 60 * 60  # 1 hour cap for a single scene

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04",
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
def smoke_test() -> dict:
    """Trivial function to force the image to build during Task 3.
    Verifies that key tools are installed inside the image."""
    import shutil
    import subprocess
    info: dict = {"ok": True}
    for tool in ["ffmpeg", "colmap", "node", "splat-transform"]:
        info[tool] = shutil.which(tool)
    info["python"] = subprocess.check_output(
        ["python", "--version"], text=True
    ).strip()
    info["timestamp"] = int(time.time())
    return info


@app.local_entrypoint()
def main() -> None:
    """Build/verify the image. Replaced in later tasks with real pipeline."""
    result = smoke_test.remote()
    print(result)
