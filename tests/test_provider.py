from data.provider_manager import ProviderManager


manager = ProviderManager()

# テスト銘柄
ticker = "7203.T"

data, provider = manager.get_stock_data(ticker)

print()

print(f"Provider : {provider}")

if data.empty:

    print("取得失敗")

else:

    print(data.head())

    print()

    print(f"件数 : {len(data)}")