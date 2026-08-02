from data.provider_manager import ProviderManager


manager = ProviderManager()

provider, df = manager.get_stock_list()

print()
print(f"Provider : {provider}")

print()

print(df.head())

print()

print(df.columns)

print()

print(f"件数 : {len(df)}")
