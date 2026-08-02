import os
import pandas as pd


FAILED_FILE = "logs/failed_download.csv"


class FailedDownloadManager:
    """
    ダウンロード失敗銘柄管理
    """

    def save(self, failed_list):
        """
        失敗銘柄をCSVへ保存（毎回上書き）
        """

        df = pd.DataFrame(
            failed_list,
            columns=[
                "code",
                "ticker",
                "company_name"
            ]
        )

        os.makedirs("logs", exist_ok=True)

        df.to_csv(
            FAILED_FILE,
            index=False,
            encoding="utf-8-sig"
        )

        print()
        print("失敗ログ保存")
        print(FAILED_FILE)

    def load(self):
        """
        失敗銘柄読込
        """

        if not os.path.exists(FAILED_FILE):

            return pd.DataFrame(
                columns=[
                    "code",
                    "ticker",
                    "company_name"
                ]
            )

        return pd.read_csv(
            FAILED_FILE,
            dtype=str
        )

    def clear(self):
        """
        失敗CSV削除
        """

        if os.path.exists(FAILED_FILE):

            os.remove(FAILED_FILE)