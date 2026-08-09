# 株探し コーディング規約

---

# 1. 目的

本プロジェクトでは、

「誰が見ても分かりやすく、修正しやすいコード」

を書くことを目的とする。

機能追加・修正・バグ対応を容易にするため、統一したコーディングルールを採用する。

---

# 2. 基本方針

コードは以下を最優先とする。

- 可読性
- 保守性
- 拡張性
- 責務の分離
- 再利用性

短いコードを書くことより、

読みやすいコードを書くことを優先する。

---

# 3. フォルダ構成

各フォルダには役割を持たせる。

| フォルダ | 役割 |
|----------|------|
| data | データ取得 |
| database | SQLite操作 |
| indicators | テクニカル指標 |
| analysis | 分析ロジック |
| rules | 売買ルール |
| scoring | スコア計算 |
| service | 処理制御 |
| ai | AI機能 |
| scripts | 実行プログラム |
| tests | テストコード |

役割を越えた処理を書かない。

---

# 4. 1ファイル1責務

1つのファイルには1つの役割だけを持たせる。

例

○

stock_price_reader.py

→ 株価読込のみ

○

stock_price_repository.py

→ 保存のみ

×

読込・保存・分析を同じファイルへ書かない。

---

# 5. 関数設計

関数は1つの処理だけを担当する。

例

○

save_stock_data()

get_stock_data()

calculate_ma()

×

save_and_calculate_and_analyze()

長い関数は複数へ分割する。

---

# 6. クラス設計

クラスは責務ごとに分ける。

例

DownloadManager

↓

ProviderManager

↓

YahooProvider

↓

JQuantsProvider

それぞれ役割を混在させない。

---

# 7. 命名規則

## ファイル名

小文字 + アンダースコア

例

```
stock_price_reader.py

moving_average.py

download_manager.py
```

---

## 関数名

動詞から始める。

例

```
get_stock_data()

save_stock_data()

calculate_ma()

update_stock_master()
```

---

## クラス名

パスカルケース

例

```
DownloadManager

ProviderManager

YahooProvider
```

---

## 定数

すべて大文字

```
REQUEST_SLEEP

BATCH_SIZE

DB_PATH
```

---

## 変数

意味が分かる名前にする。

○

```
latest_date

insert_count

duplicate_count
```

×

```
a

tmp

data1
```

---

# 8. コメント

コメントは

「なぜ書いたか」

を書く。

×

```
iを1増やす
```

○

```
Yahoo取得失敗時は
J-Quantsへ切替える
```

関数には必ずDocstringを書く。

例

```python
def save_stock_data(data, code):
    """
    株価データ保存

    Parameters
    ----------
    data
        株価DataFrame

    code
        証券コード

    Returns
    -------
    insert_count
        新規保存件数

    duplicate_count
        重複件数
    """
```

---

# 9. SQL

SQLはRepositoryへ集約する。

Reader

↓

SELECT

Repository

↓

INSERT

UPDATE

DELETE

SQLを複数箇所へ書かない。

---

# 10. エラー処理

例外処理は必ず行う。

```
try

except

finally
```

必要に応じてログへ保存する。

エラーでシステム全体を停止させない。

---

# 11. データ取得

Provider経由で取得する。

```
DownloadManager

↓

ProviderManager

↓

Yahoo

↓

J-Quants
```

直接Yahooを呼ばない。

将来Providerを追加できる構造を維持する。

---

# 12. SQLite

Reader

↓

取得専用

Repository

↓

保存専用

役割を混在させない。

---

# 13. テスト

新しい機能を追加したら

testsへテストコードを追加する。

確認項目

- 正常動作
- 異常動作
- 重複登録
- エラー処理

---

# 14. コードスタイル

インデント

```
4スペース
```

1行

```
79〜100文字程度
```

長い処理は改行する。

例

```python
cursor.execute(
    sql,
    params
)
```

---

# 15. Import順

以下の順番で記述する。

① 標準ライブラリ

```python
import os
import time
```

↓

② 外部ライブラリ

```python
import pandas as pd
import yfinance as yf
```

↓

③ プロジェクト内

```python
from database.db import create_connection
```

---

# 16. 開発ルール

実装前に

- 要件定義
- ロードマップ
- 分析仕様書

を確認する。

設計変更がある場合は

コードより先にドキュメントを更新する。

---

# 17. 品質基準

コード完成後は必ず実施する。

- 動作確認
- 単体テスト
- データ整合性確認
- ログ確認
- ドキュメント更新
- Gitコミット

品質を満たさないコードはコミットしない。

---

# 18. 開発方針

株探しはレイヤー構造を採用する。

```
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
UI
      ↓
AI
```

各レイヤーは独立して開発し、他レイヤーへの影響を最小限に抑える。

新機能は既存コードを書き換えるのではなく、可能な限り追加・拡張できる設計を基本とする。