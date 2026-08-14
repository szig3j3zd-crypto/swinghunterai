# 株探し

日本株スイングトレード向けの自分専用売買判断システム。

移動平均線と出来高だけで売買候補を抽出するアプリを最短で完成させ、その後にテクニカル分析・バックテスト・AI分析を段階的に追加していく。

要件定義・ロードマップ・システム構成などの詳細は [docs/](docs/) を参照。

## セットアップ

```bash
pip install -r requirements.txt
```

Python 3.13を使用する（Turso接続クライアントがPython 3.14向けのWindows wheelを
まだ提供していないため。詳細は
[docs/architecture/system_configuration/cloud_access.md](docs/architecture/system_configuration/cloud_access.md)）。

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

## ダッシュボード

`株探し起動.bat` を実行、または `streamlit run ui/dashboard.py` で起動する。

スマホ・他のPCから使う方法（無料）は2通りある。

- PCの電源が入っていなくてもアクセスしたい場合（推奨）:
  [docs/architecture/system_configuration/cloud_access.md](docs/architecture/system_configuration/cloud_access.md)
  （Turso + Streamlit Community Cloud）
- PCが起動している間だけでよい場合:
  [docs/architecture/system_configuration/mobile_access.md](docs/architecture/system_configuration/mobile_access.md)
  （Tailscale）
