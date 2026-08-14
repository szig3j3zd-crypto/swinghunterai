# スマホ・他PCからのアクセス（PCの電源が切れていても可、Turso + Streamlit Community Cloud）

---

# 概要

[mobile_access.md](mobile_access.md)（Tailscale方式）はPCが起動している間しか使えない。
本方式は、株価DB・売買記録・監視銘柄をクラウドDB（[Turso](https://turso.tech/)、
SQLite互換）へ移し、ダッシュボード自体もStreamlit Community Cloudへデプロイすることで、
**PCの電源が入っていなくてもスマホ・他PCからアクセスできる**ようにする。無料枠内で
完結する。

```
PC（株探し起動.bat / scripts/update_stock_data.py 等）
  └─ database/db.py: Turso Embedded Replica
       （ローカルファイル data/stock_replica.db + 自動同期。読み書きはローカル並みに高速）

Turso（クラウド上のSQLite互換DB。株価・トレード記録・監視銘柄すべての一次データ）

Streamlit Community Cloud（ui/dashboard.py をデプロイ、GitHub連携）
  └─ database/db.py: Tursoへ直接リモート接続
       （コンテナのディスクが永続化されないためEmbedded Replicaは使わない）
  └─ 「Who can view this app」で自分のGoogleアカウントのみ閲覧可に制限
```

`database/db.py`の`create_connection()`1箇所で接続先を切り替えており、Repository層
（`database/*_repository.py`）は無改修で動く。理由はlibsql（Tursoの接続クライアント）が
`sqlite3`とほぼ同じAPI（`cursor().execute()`/`executemany()`/`commit()`）を提供するため。

---

# 前提知識・ハマったポイント

再構築する際に同じ問題を踏まないよう記録しておく。

- **Python 3.14ではlibsqlがインストールできない**（Windows向けビルド済みwheelが無く、
  Rustツールチェインが無いとソースビルドにも失敗する）。プロジェクトの`.venv`を
  Python 3.13で作り直した（`runtime.txt`でStreamlit Community Cloud側も3.13を指定）
- **Turso CLIはWindowsではWSLが必須**。WSLを入れずに済ませるため、DB作成・接続情報の
  発行はTursoのWeb画面（https://turso.tech ）から行い、既存データの移行は
  `scripts/migrate_to_turso.py`（Python、`libsql`パッケージ使用）で行った
- **`executemany()`をTursoへのリモート接続に対して使うと、1行ごとに1回通信してしまい
  極端に遅い**（1000行で約40秒）。`scripts/migrate_to_turso.py`は複数行をまとめた
  1回のSQL文（`INSERT INTO ... VALUES (...),(...),...`）を発行する方式にして解決した
  （同条件で約0.3秒）。1文あたりのバインド変数が20,000〜40,000個の間でエラーになった
  実測結果から、バッチサイズは2000行にしている
- **libsql経由だとSQLエラーの例外型が`sqlite3.OperationalError`ではなく素の
  `ValueError`になる**。`database/trade_repository.py`・`watchlist_repository.py`・
  `stock_master_repository.py`の`create_table()`内、既存DBへの列追加マイグレーション
  （`ALTER TABLE ... ADD COLUMN`を試して失敗を無視する処理）が`sqlite3.OperationalError`
  のみを捕まえていたため、Turso接続時に未捕捉のまま例外が飛んでいた
  （`except (sqlite3.OperationalError, ValueError):`に修正済み）
- **Embedded Replicaは初回接続時に丸ごと初期同期する**。ローカルの
  `data/stock_replica.db`が存在しない最初の1回は、リモートDB全体
  （現状485MB）をダウンロードするため数分Streamlitサーバーが応答しなくなる。
  2回目以降は差分同期のみなので一瞬で終わる

---

# セットアップ手順（再構築する場合）

## 1. Turso

1. https://turso.tech でアカウント作成
2. Web画面から「Create Database」で空のDBを作成
3. 作成後のDB詳細ページから接続URL（`libsql://...`）と認証トークンを発行
4. `.env`に追記
   ```
   TURSO_DATABASE_URL=libsql://xxxxx.turso.io
   TURSO_AUTH_TOKEN=xxxxx
   TURSO_EMBEDDED_REPLICA=true
   ```
   （`TURSO_EMBEDDED_REPLICA=true`はPC用。Streamlit Community Cloud側のSecretsには
   これを含めない＝リモート直結モードになる）
5. 既存の`data/stock.db`から移行
   ```
   python scripts/migrate_to_turso.py
   ```
   560万行規模で15〜20分程度かかる。再実行しても安全（`INSERT OR IGNORE`）

## 2. GitHub

1. プライベートリポジトリを作成
2. `git remote add origin <URL>` → `git push -u origin main`
   （初回pushでブラウザ認証が求められる場合がある）

## 3. Streamlit Community Cloud

1. https://share.streamlit.io にGitHubアカウントでサインイン
2. 「Create app」→「GitHubから公開アプリをデプロイする」
   - Repository: `<自分のリポジトリ>`
   - Branch: `main`
   - Main file path: `ui/dashboard.py`
3. デプロイ前に「詳細設定」→「Secrets」に以下を貼り付け
   ```
   TURSO_DATABASE_URL = "libsql://xxxxx.turso.io"
   TURSO_AUTH_TOKEN = "xxxxx"
   ```
4. デプロイ後、アプリ設定（右下「⋮」→ Settings）から閲覧制限
   （「Who can view this app」に近い項目）を開き、自分のGoogleアカウントの
   メールアドレスのみ許可する

---

# 日々のデータ更新

これまでどおりPC側で`scripts/update_stock_data.py`等を実行すればよい。Embedded Replica
が自動的にTursoへ同期する（`database/db.py`の`TURSO_SYNC_INTERVAL_SECONDS`、5秒間隔で
バックグラウンド同期）ため、Streamlit Community Cloud側は次にアクセスしたときには
最新データを直接Tursoから読む。

---

# 既知の制限

- **スマホ（Streamlit Cloud側）からの「候補を更新」フルスキャンは、PCでの実行より
  大幅に遅くなる**（東証プライム全銘柄約1,559銘柄それぞれの株価をネットワーク経由で
  Tursoへ問い合わせるため）。日々のスキャンは引き続きPC側（Embedded Replicaで高速）で
  行い、スマホ・他PCは「今日の候補の閲覧」「売買銘柄・監視銘柄の追加編集」用と
  割り切る想定
- Turso無料枠の容量・帯域上限は変動するため、定期的にTursoのダッシュボードで
  使用量を確認する
- [mobile_access.md](mobile_access.md)の「スマホでの操作に関する既知の制限」
  （チャートの独自スクロールバーがタッチ未対応等）はこちらの方式でも同様に当てはまる
