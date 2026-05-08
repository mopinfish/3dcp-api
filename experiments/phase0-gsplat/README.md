# Phase 0: gsplat パイプライン PoC

[Issue #12](https://github.com/mopinfish/3dcp-api/issues/12) Phase 0 の作業ディレクトリ。

## セットアップ

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
modal token new      # Modal アカウントの API トークン設定
```

## 実行

```bash
# 動画を input/ に配置してから
modal run pipeline.py --video-path input/sample.mp4 --scene-name sample
```

成果物は `output/` に PLY と SPZ で出力される。
計測結果は `metrics/run-{timestamp}.json` に記録される。
