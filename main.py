from config.config import PROJECT_NAME, VERSION
from service.stock_service import download_all_stocks


def main():

    print(PROJECT_NAME)
    print(f"Version : {VERSION}")


    download_all_stocks()


    print("全銘柄取得完了")


if __name__ == "__main__":
    main()