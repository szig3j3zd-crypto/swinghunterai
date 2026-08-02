from data.provider_manager import ProviderManager

manager = ProviderManager()

df, provider = manager.get_stock_list()

codes = []

duplicates = []

for code in df["Code"]:

    code = str(code)[:4]

    if code in codes:
        duplicates.append(code)
    else:
        codes.append(code)

print("重複件数 :", len(duplicates))

print()

print(duplicates)