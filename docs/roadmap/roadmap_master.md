株探し 開発ロードマップ Ver3.0
1. 開発理念

株探しは、日本株スイングトレードにおける自分専用AIトレーダーの構築を目的とする。

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
MA20
MA60
MA300
出来高平均
出来高倍率
週足・月足リサンプル

※ MA5/20/60/300（indicators/moving_average.py）・出来高平均/出来高倍率（indicators/volume.py）・週足月足リサンプル（indicators/resample.py）実装済み。指標はDBへ永続化せず日次バッチで都度計算する方針とした（詳細はentry_signal_spec.md）。run_all_indicators.pyへの組み込みは未着手。

Ver2.1
Analysis Layer
MA並び順
ゴールデンクロス
デッドクロス
MA傾き
上昇トレンド判定
出来高急増
出来高減少
支持線・抵抗線検出（日足1年／週足3年／月足7年、config変更可）
半分シグナル判定

※ 支持線・抵抗線検出は当初Phase3 Ver3.2で予定していたが、エントリー判定に必須のためVer2.1へ前倒しする。詳細は docs/specifications/entry_signal_spec.md と docs/specifications/support_resistance_spec.md を参照。

※ 支持線・抵抗線検出（特に月足7年）に対応するため、当初は初回データ取得期間を7年へ延長する計画だったが、実際には東証プライム全銘柄（1,559銘柄）と大型株100銘柄（TOPIX Core30+Large70）について10年分へ延長取得を実施済み（1,461/1,462銘柄成功、失敗1銘柄: 8303）。それ以外の銘柄は約3年分のまま。

※ 支持線・抵抗線検出（スイングポイント抽出・価格帯クラスタリング・採用条件・ブレイク判定・リセット条件）を analysis/swing_points.py・analysis/price_zones.py・analysis/support_resistance.py として実装済み。

※ MA並び順・MA傾き・上昇/下降トレンド判定（analysis/ma_trend.py）、ゴールデンクロス・デッドクロス（analysis/ma_cross.py）、半分シグナル判定（analysis/half_signal.py）を実装済み。Ver2.1のAnalysis Layerはこれで一通り完了。

※ エントリー候補の反発1・2発目カウント（rules/bounce_count.py）を実装済み。世代管理（ライン役割転換）はVer3.0以降に先送り。詳細は support_resistance_spec.md 7〜8章を参照。

※ エントリー条件（rules/entry_rule.py）を実装済み。トレンド判定・半分シグナル・60日線フィルタ・反発回数制限・出来高/株価フィルタ（rules/screening_filters.py）を統合し、エントリー候補か見送りかを理由付きで判定する。時価総額フィルタはstock_masterに時価総額データが無いため未実装（Data Layer拡張が必要）。見送り条件はエントリー判定のreasonとして実質実装済み。

※ 利確条件（前回高値/節目のうち近い方）・損切条件（前回底値/20日線のうちエントリー時点で近い方）・リスクリワード比（参考値）を rules/exit_rule.py として実装済み。詳細は docs/specifications/exit_rule_spec.md を参照。

※ 保有条件（rules/holding_rule.py）を実装済み。利確・損切いずれにも未到達のまま20営業日（config: MAX_HOLDING_DAYS、数週間〜1ヶ月のスイング想定）を超えたら「見直し候補」として警告するのみで、強制決済はしない。

Ver2.2 Rule Engineはこれで一通り完了（エントリー/見送り/利確/損切/保有）。ポジション自体を記録・追跡する仕組み（いつ・いくらでエントリーしたか）はまだ無く、holding_rule.pyはentry_dateを外部から渡す前提。

※ Scoring Engine（scoring/entry_score.py）を実装済み。MAスコア（反発回数）+出来高スコア（出来高倍率）+リスクスコア（リスクリワード比）=100点満点。rules/entry_rule.pyのevaluate_entryがエントリー候補成立時に`score`として結果へ含める。詳細は docs/specifications/entry_score_spec.md を参照。支持線・抵抗線の信頼度スコア（タッチ回数・上位足一致等）は未統合、Ver3.0以降で検討。

※ Ver2.0〜2.3を対象にbacktest/simulator.pyでバックテストを実施（詳細はbacktest/内のスクリプトと本セッションの検証結果を参照）。ロングは日足・週足とも安定して正の期待値（日足+0.66%、週足+0.57%、大型株10〜20銘柄・最大10年分の小規模検証）。ショートは一貫してマイナス（-0.47%〜-0.62%）だった。原因として日経平均が下降トレンドの時だけショートを候補にする市場フィルターを試したが、検証の結果むしろ悪化（-0.47%→-1.25%）したため不採用・実装は削除した（docs/specifications/market_filter_spec.md参照）。当面はショートを保留し、ロング中心で進める方針（ユーザー確認済み）。

※ ロングについて、TOPIX Core30+Large70（大型株98銘柄・最大10年分）でより大規模な検証を実施（4,958トレード）。勝率44.8%、平均リターン+0.62%、平均勝ち+4.93%/平均負け-2.87%となり、小規模検証（10〜20銘柄）とほぼ同じ数値が再現された。年別でも2018・2021・2022年はマイナス〜横ばい、それ以外はプラスと、特定の年に依存しない分散した結果。

Ver2.2
Rule Engine

売買ルール

エントリー条件（半分シグナル・60日線フィルタ・反発1〜2発目のみ）
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

※ service/screening_service.py（get_today_candidates）と ui/dashboard.py（Streamlit）として実装済み。デフォルトの対象銘柄は東証プライム全銘柄（market列で判定、1,559銘柄。ユーザーが実際に売買する市場のため）。大型株のみ（TOPIX Core30+Large70）に絞るget_large_cap_stocksも別途利用可能。`streamlit run ui/dashboard.py` で起動する。Playwrightで実ブラウザ動作確認済み（東証プライム全銘柄を約90秒でスキャンし候補20件を表示）。チャート表示・通知・ポートフォリオ・ダッシュボードの拡張はVer2.4以降で未着手。

※ 2026-08-10、Rule Engine（rules/entry_rule.py）を判断基準ごとに選択式でAND結合する
モジュール方式へ全面改訂（並び順・完全ゴールデンクロス・反発・並走上昇・半分シグナルの
5モジュール。旧パターンA/Bは廃止）。詳細は docs/specifications/entry_signal_spec.md
を参照。改訂後にバックテストを実施し、検証したロング全パターンで正の期待値、
ショートは引き続きマイナスという結果を得た（半分シグナル単体・並走上昇単体は
東証プライム全銘柄10年分で検証、それ以外は大型株40銘柄サンプル。数値詳細は
entry_signal_spec.md 11章参照）。Scoring Engine（entry_score_spec.md）はこの
モジュール化に未対応のままVer3.0以降へ先送り。

🎯 Phase2 完了条件

移動平均線と出来高だけで

毎日

「今日はこの銘柄を買う」

という候補が自動で表示される。

この時点を**株探し Ver1（初期完成版）**とする。

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

水平ラインの高度化（基本の支持線・抵抗線検出はVer2.1へ前倒し済み）

ブレイクアウト

複数期間・複数時間足の比較精度向上

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

※ 2026-08-14、Tailscaleを使い、PC上で起動したダッシュボードへスマホ・他PCから
アクセスできるようにした（`.streamlit/config.toml`でStreamlitを全インターフェース
待受に設定）。株価DB（485MB）やトレード記録はPC上のまま、クラウドDB移行やUI再実装を
伴わずに実現。詳細は docs/architecture/system_configuration/mobile_access.md 参照。
チャートの独自スクロールバーはタッチ操作未対応（既知の制限、同ドキュメント参照）。

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