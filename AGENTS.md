# エージェント向けメモ（新刊チェック）

- 入口は `scripts/suggest_candidates.py`（楽天ブックス）。新刊順は `--sort=-releaseDate`。
- **共通の罠（再刊と初刊年・海外作品・レーベル判別など）は `../AGENTS.md` の
  「姉妹DBサイト」節を必ず読むこと。**楽天の新着上位は文庫化・新装版・予約が大半。
- Windows では `PYTHONUTF8=1` が要る。
