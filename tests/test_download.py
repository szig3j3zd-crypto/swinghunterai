from data.downloader import get_stock_data

print("module :", get_stock_data.__module__)
print("file   :", get_stock_data.__code__.co_filename)
print()

data = get_stock_data("7203.T")

print(data.head())
print()

print("取得件数:", len(data))
print()

print(data.columns)