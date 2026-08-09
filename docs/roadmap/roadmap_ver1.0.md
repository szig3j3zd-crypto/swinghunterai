株探し Ver1.0（Data Foundation）
概要

Ver1.0では、株探し の基盤となる Data Layer を構築した。

目的は、東証上場銘柄の情報と株価データを安定して取得・保存し、今後のテクニカル分析やAI分析で利用できるデータ基盤を完成させることである。

実装内容
1. プロジェクト構築
実装内容
Pythonプロジェクト作成
フォルダ構成作成
main.py作成
requirements.txt作成
.gitignore作成
.env作成
目的

今後機能追加しても保守しやすい構成にする。

2. Git管理
実装内容
Git初期化
GitHub管理開始
バージョン管理ルール作成
目的

ソースコード変更履歴を管理する。

3. SQLite構築
実装内容

SQLiteを採用し、

以下のテーブルを作成。

stock_master

保存内容

証券コード
ティッカー
会社名
市場区分
JPX400
active
stock_prices

保存内容

証券コード
日付
始値
高値
安値
終値
出来高
主な改善
UNIQUE(code,date)
INSERT OR IGNORE
日付フォーマット統一
4. Repository構成
実装内容

Repositoryパターンを採用。

作成ファイル

stock_master_repository.py
stock_price_repository.py
役割

SQLiteへの

登録
更新

のみ担当する。

SQLをRepositoryへ集約した。

5. Reader構成
実装内容

Readerパターンを採用。

作成ファイル

stock_master_reader.py
stock_price_reader.py
役割

SQLiteから

必要なデータのみ取得する。

6. Yahoo Finance取得
実装内容

Yahoo Finance APIから

株価取得機能を実装。

取得項目

Date
Open
High
Low
Close
Volume

リトライ処理も実装。

7. J-Quants取得
実装内容

J-Quants API対応。

Yahoo取得失敗時に利用する。

調整後価格にも対応。

8. Provider切替
実装内容

ProviderManagerを実装。

取得順

Yahoo

↓

J-Quants

目的

Yahoo障害時でも

取得を継続できる。

9. 約3年分初回取得
実装内容

initialize_stock_data.py を作成。

分析対象全銘柄について

約3年分の株価データを取得。

SQLiteへ保存。

10. 差分更新
実装内容

update_stock_data.py を作成。

SQLiteの最新保存日を取得し、

不足データのみ取得。

11. 重複登録防止
実装内容

SQLite

UNIQUE(code,date)

INSERT OR IGNORE

cursor.rowcount

により重複登録を防止。

12. 個別株抽出
実装内容

分析対象を

プライム（内国株式）
スタンダード（内国株式）
グロース（内国株式）

に限定。

ETF

REIT

PRO Market

外国株

は分析対象から除外。

最終分析対象

3716銘柄

13. CSV保存
実装内容

SQLite保存とは別に

CSVも保存。

用途

デバッグ
バックアップ
データ確認
14. ログ管理
実装内容

ログ機能を実装。

保存内容

download_history.csv
failed_download.csv
failed_initialize.csv
app.log
15. ドキュメント整備
作成資料
要件定義書
ロードマップ
フォルダ構成
システム構成
開発ルール
バージョン管理
Git運用ルール
Ver1.0 完了条件
Data Layer完成
約3年分の株価データ取得完了
差分更新動作確認
Repository構成完成
Reader構成完成
Provider切替完成
SQLite保存確認
個別株3716銘柄対応
ドキュメント更新完了
Ver1.0 開発成果

Data Layerが完成し、今後のテクニカル分析・売買ルール・バックテスト・AI分析の基盤が整った。