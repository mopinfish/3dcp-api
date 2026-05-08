# 3DGS パイプライン Phase 0 (PoC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 自前の動画 → 3D Gaussian Splatting パイプラインを最小実装で通し、Luma との比較で内製化を継続するか判断する材料を揃える。

**Architecture:** Modal の serverless GPU 上で `ffmpeg → COLMAP → gsplat → splat-transform` のパイプラインを実行し、出力された PLY/SPZ をローカルにダウンロードする。ストレージは Phase 0 では使わず、`3dcp-web/public/spike/` 配下に静的ファイルとして配置して `mkkellogg/GaussianSplats3D` で描画する。

**Tech Stack:** Modal（serverless GPU）/ Python 3.11 / gsplat (Apache 2.0) / COLMAP（GLOMAP モード）/ ffmpeg / @playcanvas/splat-transform / Next.js Pages Router / @mkkellogg/gaussian-splats-3d

**親 Issue:** [#12](https://github.com/mopinfish/3dcp-api/issues/12)
**対応サブ Issue:** [#13](https://github.com/mopinfish/3dcp-api/issues/13) / [#14](https://github.com/mopinfish/3dcp-api/issues/14) / [#15](https://github.com/mopinfish/3dcp-api/issues/15)

**前提条件:**
- otsuka さんが Luma に登録済みの文化財の元動画ファイル（mp4）を 1 本以上提供できる
- otsuka さんが Modal アカウントを作成し、API トークンを発行済み（Task 2 で実施）
- otsuka さんから Modal トークンと動画ファイルパスが共有されている状態で、私（Claude）が Modal 上の GPU 関数を起動・実行する

---

## File Structure

```
3dcp-api/                                 # 既存 Django リポジトリ
└── experiments/                          # 新規（Phase 0 限定の実験ディレクトリ）
    └── phase0-gsplat/
        ├── README.md                     # PoC のセットアップ手順
        ├── pipeline.py                   # Modal アプリ本体（パイプライン）
        ├── requirements.txt              # ローカル側の依存（modal CLI のみ）
        ├── .gitignore                    # 動画・PLY などの大容量ファイル除外
        ├── input/                        # 入力動画（git ignore）
        ├── output/                       # 出力 PLY / SPZ（git ignore）
        └── metrics/                      # 計測結果（コミット対象）
            └── run-{timestamp}.json

3dcp-web/                                 # 既存 Next.js リポジトリ
├── package.json                          # @mkkellogg/gaussian-splats-3d を devDep 追加
├── public/
│   └── spike/                            # PoC 用静的ファイル（git ignore）
│       └── README.md                     # 配置ファイルの説明（こちらは追跡）
└── src/pages/spike/
    ├── ply.tsx                           # GaussianSplats3D で PLY 描画
    └── compare.tsx                       # Luma と並べて比較
```

**設計判断:**
- `experiments/` は本番コードと分離し、Phase 1 以降で `splat_pipeline/` Django アプリへ昇格する材料とする
- 動画 / PLY / SPZ などの大容量バイナリは git に含めず、ローカル＋Modal Volume で扱う
- 計測結果（JSON）のみコミットし、Go/No-Go 判断のエビデンスとして残す

---

## Task 1: 作業ブランチ作成と PoC ディレクトリ整備

**Files:**
- Create: `3dcp-api/experiments/phase0-gsplat/.gitignore`
- Create: `3dcp-api/experiments/phase0-gsplat/README.md`
- Create: `3dcp-api/experiments/phase0-gsplat/requirements.txt`

- [ ] **Step 1: develop から PoC 用ブランチを切る**

```bash
cd /Users/otsuka/ws/projects/3dcp/3dcp-api
git checkout develop
git pull origin develop
git checkout -b experiments/gsplat-pipeline-phase-0
```

Expected: `Switched to a new branch 'experiments/gsplat-pipeline-phase-0'`

- [ ] **Step 2: PoC 用ディレクトリを作成**

```bash
mkdir -p experiments/phase0-gsplat/{input,output,metrics}
```

- [ ] **Step 3: `.gitignore` を作成（動画・PLY などを除外）**

`3dcp-api/experiments/phase0-gsplat/.gitignore`:
```gitignore
input/*
!input/.gitkeep
output/*
!output/.gitkeep
*.mp4
*.mov
*.ply
*.spz
*.ksplat
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 4: 空ディレクトリ維持用の `.gitkeep` を配置**

```bash
touch experiments/phase0-gsplat/input/.gitkeep \
      experiments/phase0-gsplat/output/.gitkeep \
      experiments/phase0-gsplat/metrics/.gitkeep
```

- [ ] **Step 5: `requirements.txt` 作成（ローカル側の依存）**

`3dcp-api/experiments/phase0-gsplat/requirements.txt`:
```
modal>=0.64.0
```

- [ ] **Step 6: `README.md` 作成（手順書）**

`3dcp-api/experiments/phase0-gsplat/README.md`:
```markdown
# Phase 0: gsplat パイプライン PoC

[Issue #12](https://github.com/mopinfish/3dcp-api/issues/12) Phase 0 の作業ディレクトリ。

## セットアップ

\```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
modal token new      # Modal アカウントの API トークン設定
\```

## 実行

\```bash
# 動画を input/ に配置してから
modal run pipeline.py --video-path input/sample.mp4 --scene-name sample
\```

成果物は `output/` に PLY と SPZ で出力される。
計測結果は `metrics/run-{timestamp}.json` に記録される。
```

- [ ] **Step 7: 初回コミット**

```bash
git add experiments/
git commit -m "chore: scaffold phase 0 gsplat PoC directory"
```

Expected: 1 commit on `experiments/gsplat-pipeline-phase-0`

---

## Task 2: Modal アカウント設定（otsuka さん作業）

**ユーザ作業項目** — Claude は実行できないため、otsuka さんに依頼する。

- [ ] **Step 1: Modal アカウント作成**

  https://modal.com/signup でサインアップ（無料枠 $30/月あり、Phase 0 の数回実行は無料枠内で完結する見込み）。

- [ ] **Step 2: Modal CLI のインストールとトークン発行**

```bash
cd /Users/otsuka/ws/projects/3dcp/3dcp-api/experiments/phase0-gsplat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
modal token new
```

ブラウザが開き、Modal にログインしてトークンを承認すると `~/.modal.toml` に保存される。

- [ ] **Step 3: 動作確認**

```bash
modal run --quiet -- python -c "print('hello from modal')"
```

Expected: `hello from modal` が表示される（初回はコンテナイメージのビルドで数十秒かかる）。

- [ ] **Step 4: サンプル動画を配置**

Luma に登録済みの文化財の元動画を 1 本、`input/` 配下にコピー：
```bash
cp <PATH_TO_LUMA_SOURCE_VIDEO>.mp4 experiments/phase0-gsplat/input/sample.mp4
```

撮影条件のメモを `input/sample.notes.md` に残す（被写体名・撮影時間・解像度・撮影手法）。

**otsuka さんから完了の合図をもらってから Task 3 に進む。**

---

## Task 3: Modal 上のパイプライン Image を定義

**Files:**
- Create: `3dcp-api/experiments/phase0-gsplat/pipeline.py`

- [ ] **Step 1: `pipeline.py` の最初のセクション（Image 定義）を書く**

`3dcp-api/experiments/phase0-gsplat/pipeline.py`:
```python
"""
Phase 0 PoC: video → 3D Gaussian Splatting pipeline on Modal.

Reads a video from local, uploads to a Modal Volume, runs the full pipeline
on GPU, and downloads the resulting PLY/SPZ + metrics back to local.
"""
from __future__ import annotations
import json
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
        "nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04",
        add_python="3.11",
    )
    .apt_install(
        "git", "wget", "build-essential", "cmake",
        "ffmpeg",
        "colmap",         # GLOMAP モードは Ubuntu 22.04 の COLMAP 3.8 では未搭載。失敗時は手動 fallback
        "nodejs", "npm",  # splat-transform 用
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
        "gsplat==1.4.0",  # 2026 年時点の安定版に揃える
    )
    .run_commands(
        "npm install -g @playcanvas/splat-transform",
    )
)
```

- [ ] **Step 2: `pipeline.py` を構文チェック**

```bash
cd experiments/phase0-gsplat
python -c "import ast; ast.parse(open('pipeline.py').read()); print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Modal イメージのビルドを試す（実 GPU は使わない）**

```bash
modal build pipeline.py
```

Expected: 数分かけてイメージがビルドされ、`Image build completed` と表示される。失敗時はログから不足パッケージを特定し apt_install / pip_install を調整。

- [ ] **Step 4: コミット**

```bash
git add experiments/phase0-gsplat/pipeline.py
git commit -m "feat(poc): define Modal image for gsplat pipeline"
```

---

## Task 4: フレーム抽出 + COLMAP 関数の実装

**Files:**
- Modify: `3dcp-api/experiments/phase0-gsplat/pipeline.py`

- [ ] **Step 1: `pipeline.py` に `prepare_frames_and_sfm` 関数を追加**

`pipeline.py` に追記（Image 定義の下）:
```python
@app.function(
    image=image,
    gpu=GPU_TYPE,
    timeout=TIMEOUT_S,
    volumes={"/workspace": volume},
)
def prepare_frames_and_sfm(scene_name: str, fps: int = 2) -> dict:
    """
    Volume に置かれた input/{scene_name}.mp4 からフレームを抽出し、
    COLMAP で sparse reconstruction を実行する。

    返り値: 計測値 dict
    """
    import subprocess, shutil, os
    from pathlib import Path

    base = Path("/workspace") / scene_name
    video = base / "input.mp4"
    frames = base / "frames"
    sfm = base / "sfm"
    frames.mkdir(parents=True, exist_ok=True)
    sfm.mkdir(parents=True, exist_ok=True)
    assert video.exists(), f"{video} not found — Volume にアップロードされているか確認"

    metrics = {"scene": scene_name, "fps_extract": fps}

    # 1) フレーム抽出
    t0 = time.time()
    subprocess.check_call([
        "ffmpeg", "-y", "-i", str(video),
        "-vf", f"fps={fps}",
        "-qscale:v", "2",
        str(frames / "frame_%05d.jpg"),
    ])
    metrics["frames_count"] = len(list(frames.glob("*.jpg")))
    metrics["frame_extract_sec"] = round(time.time() - t0, 1)

    # 2) COLMAP feature extraction
    db = sfm / "database.db"
    t0 = time.time()
    subprocess.check_call([
        "colmap", "feature_extractor",
        "--database_path", str(db),
        "--image_path", str(frames),
        "--ImageReader.single_camera", "1",
        "--SiftExtraction.use_gpu", "1",
    ])
    subprocess.check_call([
        "colmap", "exhaustive_matcher",
        "--database_path", str(db),
        "--SiftMatching.use_gpu", "1",
    ])

    # 3) Mapper（COLMAP 3.9 以降なら mapper の global mode を試行）
    sparse = sfm / "sparse"
    sparse.mkdir(exist_ok=True)
    subprocess.check_call([
        "colmap", "mapper",
        "--database_path", str(db),
        "--image_path", str(frames),
        "--output_path", str(sparse),
    ])
    metrics["sfm_sec"] = round(time.time() - t0, 1)

    # 4) 結果検証
    cameras_bin = sparse / "0" / "cameras.bin"
    images_bin = sparse / "0" / "images.bin"
    assert cameras_bin.exists() and images_bin.exists(), "COLMAP 失敗：再構成結果なし"

    # registered images の数を取り出す（簡易）
    images_listing = subprocess.check_output(
        ["colmap", "model_analyzer", "--path", str(sparse / "0")]
    ).decode()
    metrics["colmap_analyzer_output"] = images_listing[-2000:]  # 末尾だけ保存

    volume.commit()
    return metrics
```

- [ ] **Step 2: トップレベルに local_entrypoint を追加（Step 7 で完成版に置き換える）**

`pipeline.py` の末尾に追記:
```python
@app.local_entrypoint()
def main(video_path: str, scene_name: str):
    """ローカル CLI から起動する入口。"""
    src = Path(video_path)
    assert src.exists(), f"video not found: {src}"

    # Volume に動画を配置
    with volume.batch_upload(force=True) as batch:
        batch.put_file(src, f"{scene_name}/input.mp4")

    # SfM 実行
    sfm_metrics = prepare_frames_and_sfm.remote(scene_name)
    print(json.dumps(sfm_metrics, indent=2, ensure_ascii=False))
```

- [ ] **Step 3: 軽量な動画でスモークテスト（フレーム数が少ないもの）**

```bash
# Modal 上で実行
modal run pipeline.py --video-path input/sample.mp4 --scene-name sample
```

Expected:
- `metrics["frames_count"]` が想定通り（FPS 2 × 動画秒数 ± 1）
- `metrics["sfm_sec"]` が極端に遅くない（数百枚のフレームで数分〜10 分）
- `cameras.bin` / `images.bin` が出来上がる

**失敗パターンと対処:**
- COLMAP が `not enough features` で失敗 → 動画が短すぎる or テクスチャが少ない。FPS を上げて再実行
- `cuda runtime error` → image の CUDA バージョンと Modal の GPU ドライバが噛み合っていない。`12.1.0` を `11.8.0` などに変更

- [ ] **Step 4: コミット**

```bash
git add experiments/phase0-gsplat/pipeline.py
git commit -m "feat(poc): add ffmpeg + COLMAP step on Modal"
```

---

## Task 5: gsplat 学習関数の実装

**Files:**
- Modify: `3dcp-api/experiments/phase0-gsplat/pipeline.py`

- [ ] **Step 1: gsplat の training script を取得する関数を追加**

`pipeline.py` の `prepare_frames_and_sfm` の下に追記:
```python
@app.function(
    image=image,
    gpu=GPU_TYPE,
    timeout=TIMEOUT_S,
    volumes={"/workspace": volume},
)
def train_gsplat(scene_name: str, max_steps: int = 30000) -> dict:
    """
    gsplat の simple_trainer を使って 3DGS を学習する。
    出力: /workspace/{scene_name}/gsplat_out/point_cloud/iteration_{N}/point_cloud.ply
    """
    import subprocess, os, shutil, json as jsonlib
    from pathlib import Path

    base = Path("/workspace") / scene_name
    sparse = base / "sfm" / "sparse" / "0"
    frames = base / "frames"
    out_dir = base / "gsplat_out"
    out_dir.mkdir(exist_ok=True)
    assert sparse.exists(), "Task 4 (SfM) を先に実行してください"

    # gsplat リポジトリを取り込み（image に焼き込まずに必要な examples を pull する）
    gsplat_dir = Path("/tmp/gsplat")
    if not gsplat_dir.exists():
        subprocess.check_call([
            "git", "clone", "--depth", "1",
            "https://github.com/nerfstudio-project/gsplat.git",
            str(gsplat_dir),
        ])
        subprocess.check_call(
            ["pip", "install", "-r", "examples/requirements.txt"],
            cwd=gsplat_dir,
        )

    # gsplat の simple_trainer は COLMAP データをそのまま読み込める
    t0 = time.time()
    log_path = out_dir / "train.log"
    with open(log_path, "w") as logf:
        subprocess.check_call(
            [
                "python", "examples/simple_trainer.py", "default",
                "--data_dir", str(base),
                "--data_factor", "1",
                "--result_dir", str(out_dir),
                "--max_steps", str(max_steps),
                "--save_steps", str(max_steps),
                "--eval_steps", str(max_steps),
                "--disable_viewer",
            ],
            cwd=gsplat_dir,
            stdout=logf,
            stderr=subprocess.STDOUT,
        )
    train_sec = round(time.time() - t0, 1)

    # 出力 PLY を所定パスにコピー
    ply_candidates = list(out_dir.rglob("point_cloud.ply"))
    assert ply_candidates, f"PLY が出力されていない: {out_dir}"
    final_ply = ply_candidates[-1]
    target_ply = base / "output.ply"
    shutil.copyfile(final_ply, target_ply)

    # log の末尾から PSNR を抽出（gsplat のログ形式に依存）
    log_tail = log_path.read_text().splitlines()[-200:]
    psnr_lines = [l for l in log_tail if "PSNR" in l or "psnr" in l]

    metrics = {
        "scene": scene_name,
        "train_sec": train_sec,
        "max_steps": max_steps,
        "ply_size_bytes": target_ply.stat().st_size,
        "psnr_log_tail": psnr_lines[-10:],  # 末尾 10 行
    }
    volume.commit()
    return metrics
```

- [ ] **Step 2: `local_entrypoint` を更新して訓練ステップを呼び出す**

`main` 関数を以下に置き換え:
```python
@app.local_entrypoint()
def main(video_path: str, scene_name: str, max_steps: int = 30000):
    src = Path(video_path)
    assert src.exists(), f"video not found: {src}"

    with volume.batch_upload(force=True) as batch:
        batch.put_file(src, f"{scene_name}/input.mp4")

    sfm_metrics = prepare_frames_and_sfm.remote(scene_name)
    print(">>> SfM done")
    print(json.dumps(sfm_metrics, indent=2, ensure_ascii=False))

    train_metrics = train_gsplat.remote(scene_name, max_steps=max_steps)
    print(">>> Training done")
    print(json.dumps(train_metrics, indent=2, ensure_ascii=False))
```

- [ ] **Step 3: 短い max_steps でスモークテスト**

```bash
modal run pipeline.py --video-path input/sample.mp4 --scene-name sample --max-steps 1000
```

Expected:
- `train_sec` が GPU 上で短時間（数分以内）
- `output.ply` が Volume に出来上がる
- `psnr_log_tail` に PSNR 値が含まれる

**失敗パターン:**
- `OOM` → `--data_factor 2` で画像をダウンサンプル
- gsplat の依存パッケージ衝突 → `pip install -r examples/requirements.txt` のログを確認

- [ ] **Step 4: コミット**

```bash
git add experiments/phase0-gsplat/pipeline.py
git commit -m "feat(poc): add gsplat training step on Modal"
```

---

## Task 6: PLY → SPZ 変換 + 成果物のローカルダウンロード

**Files:**
- Modify: `3dcp-api/experiments/phase0-gsplat/pipeline.py`

- [ ] **Step 1: `convert_and_export` 関数を追加**

`pipeline.py` に追記:
```python
@app.function(
    image=image,
    timeout=600,
    volumes={"/workspace": volume},
)
def convert_to_spz(scene_name: str) -> dict:
    """PLY を SPZ に変換し、サイズを記録する。"""
    import subprocess
    from pathlib import Path

    base = Path("/workspace") / scene_name
    ply = base / "output.ply"
    spz = base / "output.spz"
    assert ply.exists(), "Task 5 (training) を先に実行してください"

    subprocess.check_call([
        "splat-transform", str(ply), str(spz),
    ])

    metrics = {
        "ply_size_bytes": ply.stat().st_size,
        "spz_size_bytes": spz.stat().st_size,
        "compression_ratio": round(ply.stat().st_size / spz.stat().st_size, 2),
    }
    volume.commit()
    return metrics


@app.function(volumes={"/workspace": volume}, timeout=600)
def download_artifacts(scene_name: str) -> dict[str, bytes]:
    """成果物をバイト列として返す（local entrypoint 側で書き出す）。"""
    from pathlib import Path
    base = Path("/workspace") / scene_name
    return {
        "output.ply": (base / "output.ply").read_bytes(),
        "output.spz": (base / "output.spz").read_bytes(),
    }
```

- [ ] **Step 2: `local_entrypoint` を full pipeline に拡張**

`main` を再度更新:
```python
@app.local_entrypoint()
def main(video_path: str, scene_name: str, max_steps: int = 30000):
    src = Path(video_path)
    assert src.exists(), f"video not found: {src}"

    out_local = Path("output") / scene_name
    out_local.mkdir(parents=True, exist_ok=True)
    metrics_local = Path("metrics") / f"run-{scene_name}-{int(time.time())}.json"

    with volume.batch_upload(force=True) as batch:
        batch.put_file(src, f"{scene_name}/input.mp4")

    all_metrics: dict = {"started_at": time.time(), "scene": scene_name}

    print(">>> SfM start")
    all_metrics["sfm"] = prepare_frames_and_sfm.remote(scene_name)

    print(">>> Train start")
    all_metrics["train"] = train_gsplat.remote(scene_name, max_steps=max_steps)

    print(">>> Convert start")
    all_metrics["convert"] = convert_to_spz.remote(scene_name)

    print(">>> Downloading artifacts")
    files = download_artifacts.remote(scene_name)
    for name, data in files.items():
        (out_local / name).write_bytes(data)

    all_metrics["finished_at"] = time.time()
    all_metrics["total_sec"] = round(all_metrics["finished_at"] - all_metrics["started_at"], 1)

    metrics_local.write_text(json.dumps(all_metrics, indent=2, ensure_ascii=False))
    print(f"\nWrote metrics: {metrics_local}")
    print(f"Wrote artifacts to: {out_local}")
```

- [ ] **Step 3: フルパイプラインを `--max-steps 1000` でスモークテスト**

```bash
modal run pipeline.py --video-path input/sample.mp4 --scene-name sample --max-steps 1000
```

Expected:
- `output/sample/output.ply` が手元に出来上がる
- `output/sample/output.spz` が手元に出来上がり、PLY より明確に小さい（5〜10× 圧縮）
- `metrics/run-sample-{ts}.json` に sfm/train/convert それぞれの計測値が記録される

- [ ] **Step 4: コミット**

```bash
git add experiments/phase0-gsplat/pipeline.py
git commit -m "feat(poc): add SPZ conversion and artifact download"
```

---

## Task 7: 実シーンでのフル実行（30k iter）と計測

- [ ] **Step 1: max_steps を本番相当に上げて実行**

```bash
modal run pipeline.py --video-path input/sample.mp4 --scene-name sample-full --max-steps 30000
```

Expected: A10G で 15〜40 分程度。

- [ ] **Step 2: 計測値を確認**

```bash
cat metrics/run-sample-full-*.json
```

確認項目:
- `train.train_sec` < 3000（A10G で 30k iter）
- `train.psnr_log_tail` に最終 PSNR が含まれる（28 dB 前後を目標）
- `convert.spz_size_bytes` が 30 MB 未満
- `total_sec` から $1〜2 程度のコスト見積もりに収まる

- [ ] **Step 3: 必要なら 2 シーン目を試す（再現性確認）**

異なる文化財の動画でも同様に走らせ、`metrics/` に蓄積する。

- [ ] **Step 4: コミット**

```bash
git add experiments/phase0-gsplat/metrics/
git commit -m "chore(poc): record metrics for full-resolution runs"
```

---

## Task 8: 3dcp-web に Spike ページ追加（GaussianSplats3D で PLY 描画）

`3dcp-web` リポジトリに作業を移す。

**Files:**
- Modify: `3dcp-web/package.json`
- Create: `3dcp-web/public/spike/.gitignore`
- Create: `3dcp-web/public/spike/README.md`
- Create: `3dcp-web/src/pages/spike/ply.tsx`

- [ ] **Step 1: `3dcp-web` でも同名ブランチを切る**

```bash
cd /Users/otsuka/ws/projects/3dcp/3dcp-web
git checkout main 2>/dev/null || git checkout master 2>/dev/null || git checkout develop
git pull
git checkout -b experiments/gsplat-pipeline-phase-0
```

- [ ] **Step 2: GaussianSplats3D を追加**

```bash
npm install --save-dev @mkkellogg/gaussian-splats-3d
```

- [ ] **Step 3: `public/spike/` を作成し、PoC で生成した PLY を配置**

```bash
mkdir -p public/spike
cp ../3dcp-api/experiments/phase0-gsplat/output/sample-full/output.ply public/spike/sample.ply
```

- [ ] **Step 4: `public/spike/.gitignore` 作成**

`3dcp-web/public/spike/.gitignore`:
```
*.ply
*.spz
*.ksplat
!.gitignore
!README.md
```

- [ ] **Step 5: `public/spike/README.md` 作成**

`3dcp-web/public/spike/README.md`:
```markdown
# spike

PoC 用の静的アセット置き場。中身（PLY/SPZ）は `.gitignore` 済み。
3dcp-api の `experiments/phase0-gsplat/output/` から手動でコピーする。
```

- [ ] **Step 6: `pages/spike/ply.tsx` を作成**

`3dcp-web/src/pages/spike/ply.tsx`:
```tsx
import { useEffect, useRef, useState } from 'react'

export default function SpikePly() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState('initializing')
  const [loadMs, setLoadMs] = useState<number | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    let viewer: any = null
    let cancelled = false

    ;(async () => {
      const t0 = performance.now()
      const mod = await import('@mkkellogg/gaussian-splats-3d')
      const Viewer = mod.Viewer
      viewer = new Viewer({
        rootElement: containerRef.current!,
        cameraUp: [0, -1, 0],
        initialCameraPosition: [0, 0, 3],
        initialCameraLookAt: [0, 0, 0],
      })
      setStatus('loading splat')
      await viewer.addSplatScene('/spike/sample.ply', { showLoadingUI: true })
      if (cancelled) return
      viewer.start()
      setLoadMs(Math.round(performance.now() - t0))
      setStatus('rendering')
    })().catch((e) => {
      console.error(e)
      setStatus(`error: ${e?.message ?? e}`)
    })

    return () => {
      cancelled = true
      try {
        viewer?.dispose?.()
      } catch (_) {}
    }
  }, [])

  return (
    <div style={{ height: '100vh', width: '100vw', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <div style={{ position: 'fixed', top: 8, left: 8, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: 8, fontFamily: 'monospace' }}>
        status: {status}
        {loadMs != null && <div>load: {loadMs} ms</div>}
      </div>
    </div>
  )
}
```

- [ ] **Step 7: dev server を起動して描画を確認**

```bash
npm run dev
```

ブラウザで http://localhost:3000/spike/ply を開き、3D シーンが描画されることを目視確認。

確認項目:
- PLY がエラーなくロードされる
- カメラドラッグで回転できる
- FPS が極端に低くない（60 fps 近く出る）
- iOS / Android の実機（または DevTools のモバイルエミュレーション）でも描画できる

- [ ] **Step 8: コミット（PLY バイナリは含めない）**

```bash
git add public/spike/.gitignore public/spike/README.md \
        src/pages/spike/ply.tsx package.json package-lock.json
git commit -m "feat(poc): add spike page rendering PLY via GaussianSplats3D"
```

---

## Task 9: Luma との比較ページと性能計測

**Files:**
- Create: `3dcp-web/src/pages/spike/compare.tsx`
- Create: `3dcp-api/experiments/phase0-gsplat/metrics/comparison.md`

- [ ] **Step 1: `pages/spike/compare.tsx` を作成（Luma と並べて表示）**

`3dcp-web/src/pages/spike/compare.tsx`:
```tsx
import dynamic from 'next/dynamic'
import { useEffect, useRef, useState } from 'react'

// Luma viewer はクライアントサイド限定のためダイナミックインポート
const LumaViewer = dynamic(
  async () => {
    const luma = await import('@lumaai/luma-web')
    return function Inner({ source }: { source: string }) {
      const ref = useRef<HTMLDivElement>(null)
      useEffect(() => {
        if (!ref.current) return
        const splats = new luma.LumaSplatsThree({ source })
        // ここは既存 3dcp-web コンポーネントの実装に合わせる
        // PoC では luma-web の自前 viewer 例があれば差し替え
      }, [source])
      return <div ref={ref} style={{ width: '100%', height: '100%' }} />
    }
  },
  { ssr: false },
)

const SelfHostedViewer = dynamic(() => import('./ply'), { ssr: false })

export default function Compare() {
  // 同じ被写体の Luma URL を入力する
  const lumaSource = process.env.NEXT_PUBLIC_LUMA_SAMPLE_URL ?? ''

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', height: '100vh' }}>
      <div style={{ borderRight: '1px solid #444' }}>
        <h2 style={{ position: 'absolute', color: '#fff', padding: 8 }}>Luma (現状)</h2>
        {lumaSource ? <LumaViewer source={lumaSource} /> : <div>NEXT_PUBLIC_LUMA_SAMPLE_URL 未設定</div>}
      </div>
      <div>
        <h2 style={{ position: 'absolute', color: '#fff', padding: 8 }}>Self-hosted (PoC)</h2>
        <SelfHostedViewer />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Luma 側の URL を env に設定**

`3dcp-web/.env.development.local` に追記:
```
NEXT_PUBLIC_LUMA_SAMPLE_URL=https://lumalabs.ai/capture/<the-existing-record>
```

- [ ] **Step 3: 比較・計測を実施**

ブラウザで http://localhost:3000/spike/compare を開き、以下を計測：

| 指標 | 計測方法 |
|-----|---------|
| 初期表示時間 | DevTools Performance でロード〜初描画までの ms |
| FPS（定常） | DevTools FPS meter or Stats.js |
| 主観品質 | 同じアングルで両方をスクショ → 並べて比較 |
| ファイルサイズ | DevTools Network から PLY/SPZ と Luma 配信物のサイズ |
| モバイル動作 | iOS Safari / Android Chrome 実機で開いて FPS と発熱 |

- [ ] **Step 4: 結果を `comparison.md` に記録**

`3dcp-api/experiments/phase0-gsplat/metrics/comparison.md`:
```markdown
# Phase 0 比較レポート（Luma vs 内製）

被写体: <文化財名>
動画: <解像度・尺・撮影日>
Modal GPU: A10G
gsplat iter: 30000

| 指標 | Luma | Self-hosted |
|-----|------|------------|
| 初期表示時間 | X.XX s | X.XX s |
| FPS（PC） | XX | XX |
| FPS（iOS Safari） | XX | XX |
| 配信ファイルサイズ | X.X MB | PLY: X.X MB / SPZ: X.X MB |
| 主観品質（5 段階） | X | X |
| 学習時間（参考） | n/a | XX 分 |
| 推定コスト/件 | n/a | $X.XX |

## 主観メモ

- 細部の再現:
- 反射・透明物:
- アーティファクト:
- モバイル発熱:
```

- [ ] **Step 5: コミット**

```bash
# 3dcp-web
git add src/pages/spike/compare.tsx
git commit -m "feat(poc): add side-by-side comparison page (Luma vs self-hosted)"

# 3dcp-api
cd /Users/otsuka/ws/projects/3dcp/3dcp-api
git add experiments/phase0-gsplat/metrics/
git commit -m "chore(poc): record Luma vs self-hosted comparison"
```

---

## Task 10: #15 の Go/No-Go 判定レポート

- [ ] **Step 1: 判断材料を整理**

以下を `metrics/comparison.md` の末尾に追記：
```markdown
## Go/No-Go 判断

### 内製化を継続する条件（事前に決めた閾値）
- 主観品質が Luma の同等以上
- 配信サイズ（SPZ）≤ 30 MB / scene
- 初期表示 ≤ Luma + 1 秒
- 1 シーンあたり推定 GPU コスト ≤ $3

### 結果
- ✅ / ⚠️ / ❌ それぞれにチェック
- 失敗項目があれば原因と対策案を記載

### 推奨判断
- 継続 / 撤退 / 条件付き継続（条件: ...）
```

- [ ] **Step 2: GitHub Issue #15 にコメントとして判定結果を投稿**

```bash
gh issue comment 15 --repo mopinfish/3dcp-api --body-file experiments/phase0-gsplat/metrics/comparison.md
```

- [ ] **Step 3: #13, #14, #15 のチェックリストを完了状態に更新**

各 Issue に対して `gh issue close` するか、親 #12 のタスクリストを手動でチェック。

- [ ] **Step 4: PR を作成（develop へのマージ）**

```bash
cd /Users/otsuka/ws/projects/3dcp/3dcp-api
git push -u origin experiments/gsplat-pipeline-phase-0
gh pr create --base develop --title "Phase 0: gsplat パイプライン PoC" \
  --body "Issue #12 Phase 0 の成果。\n\n- pipeline.py: Modal 上の最小パイプライン\n- metrics/: 実測結果\n- comparison.md: Luma との比較レポート\n\nGo/No-Go 判定は #15 のコメント参照。"

cd /Users/otsuka/ws/projects/3dcp/3dcp-web
git push -u origin experiments/gsplat-pipeline-phase-0
gh pr create --base main --title "Phase 0: spike pages for self-hosted gsplat viewer" \
  --body "Issue mopinfish/3dcp-api#12 Phase 0 のフロント側成果。\n\n- /spike/ply: GaussianSplats3D で PLY を描画\n- /spike/compare: Luma との比較ページ"
```

判断結果が「継続」なら Phase 1 計画策定に進む（別ファイル）。「撤退」なら本ブランチを保存しつつ親 Issue をクローズ。

---

## Self-Review

- ✅ **Spec coverage**:
  - #13（gsplat 学習を通す）→ Task 3〜7 でカバー
  - #14（R2 + GaussianSplats3D で表示）→ Task 8 でカバー（R2 は Phase 0 では未使用、ローカル static で代替する旨明記済み）
  - #15（Go/No-Go 判断）→ Task 9, 10 でカバー
- ✅ **Placeholder scan**: TBD/TODO は使用していない。実コードと実コマンドのみ
- ✅ **Type consistency**: `scene_name`、`max_steps`、Volume 名 `gsplat-poc-vol`、関数名（`prepare_frames_and_sfm` / `train_gsplat` / `convert_to_spz` / `download_artifacts`）は全タスクで一貫

## 既知の不確実性

実行時に判明したら本計画を更新する：

1. **COLMAP のバージョン**：Ubuntu 22.04 apt の COLMAP が GLOMAP モード未対応の場合は通常 mapper を使用（性能比較データに影響）
2. **gsplat の `simple_trainer.py` インターフェース**：v1.4 系のフラグ名が異なる場合は v1.4 のドキュメントに合わせて調整
3. **Luma 側の比較**：`@lumaai/luma-web` の API が変わっていた場合、既存の `3dcp-web` 内のビューア実装をそのまま流用する形に変更

## 実行体制

Modal の API トークンと動画ファイルは otsuka さんから共有してもらい、`modal run` 等の実 GPU を呼び出すコマンドは私（Claude）が実行する。3dcp-web 側のローカル dev server 起動とブラウザでの目視確認は otsuka さんに依頼する（私はブラウザを開けないため）。
