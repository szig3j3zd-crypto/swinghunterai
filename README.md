# SwingHunter AI

日本株スイングトレード向けの自分専用売買判断システム。

移動平均線と出来高だけで売買候補を抽出するアプリを最短で完成させ、その後にテクニカル分析・バックテスト・AI分析を段階的に追加していく。

要件定義・ロードマップ・システム構成などの詳細は [docs/](docs/) を参照。

## セットアップ

```bash
pip install -r requirements.txt
```

`.env` に以下を設定する。

```
JQUANTS_API_KEY=your_api_key
```

## 実行

```bash
# 銘柄マスタ作成（初回のみ）
python scripts/create_stock_master.py

# 株価初期取得（初回のみ、約3年分）
python scripts/initialize_stock_data.py

# 日次更新
python scripts/update_stock_data.py

# DB再構築（テーブル作成のみ）
python scripts/rebuild_database.py
```
