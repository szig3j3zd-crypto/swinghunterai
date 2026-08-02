SwingHunter AI 開発ロードマップ Ver3.0
1. 開発理念

SwingHunter AIは、日本株スイングトレードにおける自分専用AIトレーダーの構築を目的とする。

最初からすべての機能を実装するのではなく、

「実際に売買できるアプリケーションを最短で完成させる」

ことを優先し、その後に機能拡張を行う。

2. システム構成
Data Layer
      ↓
Indicator Layer
      ↓
Analysis Layer
      ↓
Rule Engine
      ↓
Scoring Engine
      ↓
BackTest
      ↓
UI
      ↓
AI

AIは最後に追加する。

まずは人間と同じ分析ができるシステムを完成させる。

3. 開発フェーズ
Phase	内容	目的
Phase1	Data Foundation	データ基盤構築
Phase2	Core Trading Engine	売買可能なアプリを完成させる
Phase3	Technical Expansion	テクニカル分析機能拡張
Phase4	Verification	バックテスト・検証
Phase5	UI	操作画面・通知
Phase6	AI	AI分析・自己学習
Phase1 Data Foundation
Ver1.0（完了）
Data Layer
プロジェクト構築
Git管理
SQLite構築
Repository構成
Reader構成
Yahoo Finance取得
J-Quants取得
Provider切替
約3年分初回取得
差分更新
重複登録防止
個別株抽出
CSV保存
ログ管理
ドキュメント整備

完了

Phase2 Core Trading Engine

目的

移動平均線と出来高だけで、

実際に売買候補を抽出できるアプリを完成させる。

Ver2.0
Indicator Layer
MA5
MA25
MA75
MA300
出来高平均
出来高倍率

※ MA5・MA25・MA75は indicators/moving_average.py として先行実装済み（Ver2.0着手前のプロトタイプ、MA300・出来高平均・出来高倍率は未実装）

Ver2.1
Analysis Layer
MA並び順
ゴールデンクロス
デッドクロス
MA傾き
上昇トレンド判定
出来高急増
出来高減少
Ver2.2
Rule Engine

売買ルール

エントリー条件
見送り条件
保有条件
利確条件
損切条件
Ver2.3
Scoring Engine

売買候補ランキング

例

MA +40
出来高 +40
リスク +20

100点満点

Ver2.4
UI

最初の完成版

表示

今日の買い候補
ランキング
スコア
判定理由
エントリー価格
損切価格
利確価格
🎯 Phase2 完了条件

移動平均線と出来高だけで

毎日

「今日はこの銘柄を買う」

という候補が自動で表示される。

この時点を**SwingHunter AI Ver1（初期完成版）**とする。

Phase3 Technical Expansion

完成したアプリへ

必要な分析を順次追加する。

Ver3.0

RSI

MACD

ボリンジャーバンド

ATR

ADX

ストキャスティクス

Ver3.1

ダウ理論

高値更新

安値切上げ

押し目

トレンド分類

Ver3.2

水平ライン

サポート

レジスタンス

ブレイクアウト

Ver3.3

ローソク足

包み足

はらみ足

ピンバー

ギャップ

Ver3.4

市場分析

日経平均

TOPIX

グロース指数

市場トレンド

市場センチメント

Ver3.5

RS分析

市場比較

業種比較

個別比較

Phase4 Verification
バックテスト
売買シミュレーター
売買日誌
ルール改善
Phase5 UI
ダッシュボード
チャート
通知
ポートフォリオ
Phase6 AI
AIコメント
AI売買判断
AIルール最適化
自己学習AI
自分専用AIトレーダー
品質管理（Quality Gate）

各バージョンは以下をすべて満たした場合のみ完了とする。

要件定義・仕様書との整合性確認
実装完了
単体テスト
結合テスト
データ整合性チェック
バックテスト（対象機能がある場合）
パフォーマンス確認
Gitコミット・タグ付け
ドキュメント更新（ロードマップ・変更履歴・仕様書）
レビュー完了

品質ゲートを通過しない限り、次バージョンの開発へ進まない。