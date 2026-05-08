# Phase 0: gsplat パイプライン PoC

[Issue #12](https://github.com/mopinfish/3dcp-api/issues/12) Phase 0 の作業ディレクトリ。

## セットアップ

```bash
# uv で venv 作成 + 依存インストール
uv venv
uv pip install -r requirements.txt

# Modal アカウントの API トークン設定（初回のみ）
uv run modal token new
```

## 実行

```bash
# 動画を input/ に配置してから
uv run modal run pipeline.py --video-path input/sample.mp4 --scene-name sample
```

> Phase 0 進行中：上記の `--video-path` / `--scene-name` オプションは Task 4 以降で `main()` に追加されます。Task 3 完了時点では `uv run modal run pipeline.py` (引数なし) で smoke test が走ります。

成果物は `output/` に PLY と SPZ で出力される。
計測結果は `metrics/run-{timestamp}.json` に記録される。
