SWINGHUNTERAI/    システム全体を管理するフォルダ
│
├── __pycache__/
│   └── Python実行時に自動生成されるキャッシュファイル
│
├── .venv/    プログラムの実行速度を向上させるためのキャッシュ
│   ├── Python仮想環境
│   ├── ライブラリ・Python実行環境
│   └── 開発環境専用
│
├── ai/    AI機能を管理するフォルダ
│   └── AIコメント生成・AI分析機能（今後実装）
│
├── analysis/    分析処理を管理するフォルダ
│   ├── 分析処理
│   └── check_stock_data.py        株価データ確認・分析用
│
├── backtest/    バックテストを管理するフォルダ
│   └── 売買ルールのバックテスト
│
├── config/    システム設定を管理するフォルダ
│   ├── config.py                  共通設定
│   └── settings.py                APIキー・各種設定
│
├── data/    データ取得フォルダ
│   │
│   ├── providers/    銘柄・株価取得フォルダ
│   │   ├── base_provider.py       Provider共通クラス
│   │   ├── jquants_auth.py        J-Quants認証
│   │   ├── jquants_provider.py    J-Quantsから株価取得
│   │   └── yahoo_provider.py      Yahoo Financeから株価取得
│   │
│   ├── stock_data/    取得したCSVデータを保存
│   │   ├── daily/                 CSV株価保存
│   │   └── master/                銘柄マスタCSV
│   │
│   ├── validator/    取得したデータが正常か確認
│   │   └── data_validator.py      取得データの品質チェック
│   │
│   ├── csv_reader.py              CSV読込
│   ├── csv_writer.py              CSV保存
│   ├── data_provider.py           データ取得共通処理
│   ├── download_manager.py        株価取得管理
│   ├── failed_download_manager.py 失敗銘柄管理
│   ├── provider_manager.py        Yahoo/J-Quants切替管理
│   └── stock.db                   SQLiteデータベース
│
├── database/  データベースを操作するフォルダ（SQLiteへの保存・読込・更新のみ担当）
│   ├── __init__.py
│   ├── db.py                          DB接続管理
│   ├── stock_master_reader.py         銘柄マスタ読込
│   ├── stock_master_repository.py     銘柄マスタ登録・更新
│   ├── stock_price_reader.py          株価読込
│   └── stock_price_repository.py      株価保存
│
├── docs/　　　　システム設計書・開発資料を管理するフォルダ
│   │
│   ├── architecture/　　　　システム設計
│   │   ├── Folder_structure.md        フォルダ構成説明
│   │   └── system_configuration       システム構成
│   │       └── ver1.0.md              システム構成履歴
│   │
│   ├── development/　　　　開発ルール
│   │   ├── coding_rules.md            コーディング規約
│   │   ├── git_workflow.md            Git運用ルール
│   │   └── notepad.md                 メモ帳
│   │
│   ├── requirements_definition/　　　　要件定義書
│   │   └── requirements_definition.md　要件定義書
│   │
│   └── roadmap/　　　　開発ロードマップ
│       ├── roadmap_master.md          全体ロードマップ
│       └── roadmap_ver1.0.md          Ver1.0開発計画
│
├── specifications/　　　　分析仕様書を管理するフォルダ
│   └── 分析仕様書・判定ロジック仕様
│
├── indicators/　　　　テクニカル指標を計算するフォルダ
│   └── テクニカル指標計算（移動平均・RSI・MACD等）
│
├── logs/　　　　ログを管理するフォルダ（実行履歴やエラー履歴などを保存）
│   ├── app.log                    アプリログ
│   ├── download_history.csv       ダウンロード履歴
│   ├── failed_download.csv        更新失敗銘柄
│   ├── failed_initialize.csv      初回取得失敗銘柄
│   └── logger.py                  ログ出力管理
│
├── rules/    売買ルールを管理するフォルダ
│   └── 売買ルール判定
│
├── scoring/    スコアリングを管理するフォルダ（各ルールの結果を点数化）
│   └── スコアリング処理
│
├── scripts/    実行用スクリプトを管理するフォルダ
│   ├── create_stock_master.py     銘柄マスタを新規作成
│   ├── initialize_stock_data.py   初回3年分の株価データ取得
│   ├── rebuild_database.py        DBを再構築
│   ├── retry_failed_download.py   取得失敗銘柄のみ再取得
│   ├── run_all_indicators.py      全テクニカル指標を計算
│   ├── update_stock_data.py       株価データを日次更新
│   └── update_stock_master.py     銘柄マスタを更新
│
├── service/    サービス層を管理するフォルダ
│   └── stock_service.py           システム全体から利用するサービス層
│
├── tests/    テストコードを管理するフォルダ
│   └── テストコード
│
├── .env                           APIキー等の環境変数
├── .gitignore                     Git管理対象外設定
├── main.py                        メインプログラム
├── README.md                      プロジェクト概要
├── requirements.txt               Pythonライブラリ一覧
└── yfinance_cache.sqlite          yfinanceキャッシュ