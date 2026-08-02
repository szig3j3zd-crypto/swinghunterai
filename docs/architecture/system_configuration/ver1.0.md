# SwingHunter AI システム構成（Data Layer Ver1.0）

---

# 概要

Data Layer は、銘柄情報と株価データを取得し、SQLiteへ保存する役割を持つ。

システムは以下の流れで処理を行う。

「実行スクリプト」
（処理を開始する）

↓

「サービス・管理クラス」
（処理全体の流れを制御する）

↓

「Provider」
（Yahoo・J-Quantsからデータを取得する）

↓

「Repository」
（取得したデータをSQLiteへ保存する）

↓

「SQLite」
（データを永続保存する）

---

# ① 銘柄マスタ更新

実行

scripts/update_stock_master.py
（銘柄マスタ更新開始）

↓

ProviderManager
（利用可能なProviderを選択）

↓

Yahoo または J-Quants
（東証上場銘柄一覧を取得）

↓

銘柄一覧取得

↓

stock_master_repository.py
（SQLiteへ保存）

↓

SQLite(stock_master)
（銘柄マスタ更新）

↓

完了

### 処理内容

東証上場銘柄一覧を取得し、

SQLiteの stock_master テーブルを更新する。

---

# ② 初回株価取得

実行

scripts/initialize_stock_data.py
（初回データ取得開始）

↓

stock_master_reader.py
（分析対象銘柄を取得）

↓

分析対象銘柄取得

↓

DownloadManager
（株価取得処理を開始）

↓

ProviderManager
（利用可能なProviderを選択）

↓

Yahoo
（株価取得）

↓

J-Quants（Yahoo失敗時のみ）
（Yahoo取得失敗時の代替取得）

↓

DataValidator
（取得データを検証）

↓

stock_price_repository.py
（SQLiteへ保存）

↓

SQLite(stock_prices)
（株価保存）

↓

csv_writer.py
（CSV保存）

↓

CSV保存

↓

logger.py
（処理結果を記録）

↓

ログ保存

↓

完了

### 処理内容

初回のみ約3年分の株価データを取得し、

SQLiteへ保存する。

Yahoo取得失敗時は

自動でJ-Quantsへ切り替える。

---

# ③ 日次更新

実行

scripts/update_stock_data.py
（日次更新開始）

↓

stock_master_reader.py
（分析対象銘柄取得）

↓

分析対象取得

↓

stock_price_reader.py
（最新保存日取得）

↓

最新保存日取得

↓

DownloadManager
（株価取得開始）

↓

ProviderManager
（利用可能なProviderを選択）

↓

Yahoo
（差分データ取得）

↓

J-Quants
（Yahoo失敗時のみ取得）

↓

DataValidator
（取得データ検証）

↓

stock_price_repository.py
（SQLite更新）

↓

SQLite更新

↓

csv_writer.py
（CSV更新）

↓

CSV更新

↓

logger.py
（履歴保存）

↓

履歴保存

↓

完了

### 処理内容

SQLiteに保存されている最新日付を確認し、

不足している株価データのみ取得する。

重複データは保存しない。

---

# Provider構成

DownloadManager
（株価取得を開始）

↓

ProviderManager
（利用可能なProviderを管理）

↓

YahooProvider
（Yahoo Financeから取得）

↓

JQuantsProvider
（J-Quantsから取得）

### 処理内容

DownloadManagerは

データ取得処理を開始する。

ProviderManagerは

利用可能なProviderを順番に呼び出す。

Yahoo取得失敗時のみ

J-Quantsへ自動切替を行う。

---

# Database構成

SQLite
（システム全体のデータ保存先）

│

├── stock_master
（銘柄情報）

└── stock_prices
（株価情報）

### stock_master

銘柄情報を保存

・証券コード

・会社名

・市場区分

・JPX400

など

### stock_prices

株価データを保存

・日付

・始値

・高値

・安値

・終値

・出来高

---

# Reader

stock_master_reader.py

↓

SQLite読込

↓

DataFrame返却

### 処理内容

データベースから

必要な情報を取得する。

※ Readerは「読むだけ」を担当する。

---

# Repository

stock_master_repository.py

↓

SQLite保存

stock_price_repository.py

↓

SQLite保存

### 処理内容

SQLiteへの

登録・更新のみ担当する。

※ Repositoryは「保存するだけ」を担当する。

---

# DataValidator

株価取得

↓

データ品質確認

↓

正常

↓

保存

### 処理内容

欠損データや異常データを検証し、

正常なデータだけを保存する。

---

# Logger

処理終了

↓

download_history.csv
（取得履歴）

↓

app.log
（アプリログ）

↓

failed_download.csv
（取得失敗銘柄）

### 処理内容

処理履歴とエラー履歴を保存し、

後から実行結果を確認できるようにする。

---

# Data Layer 完成図

実行
（処理開始）

↓

Scripts
（実行スクリプト）

↓

Reader
（SQLiteから必要なデータを取得）

↓

DownloadManager
（取得処理開始）

↓

ProviderManager
（Provider選択）

↓

Yahoo

↓

J-Quants

↓

DataValidator
（データ検証）

↓

Repository
（SQLiteへ保存）

↓

SQLite
（永続保存）

↓

CSV
（バックアップ保存）

↓

Logger
（実行結果保存）

↓

終了