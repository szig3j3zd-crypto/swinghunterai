from data.download_manager import DownloadManager

manager = DownloadManager()

provider_name, data = manager.download("7203.T")

print("provider:", provider_name)
print()

print(data.head())
print()

print("取得件数:", len(data))
print()

print(data.columns)