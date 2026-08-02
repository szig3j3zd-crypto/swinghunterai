from data.download_manager import DownloadManager


manager = DownloadManager()

data = manager.download("7203.T")

if data is None:

    print()

    print("NG")

else:

    print()

    print("OK")

    print(data.head())