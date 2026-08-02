from data.provider_manager import ProviderManager

manager = ProviderManager()

print()

print("===== Provider一覧 =====")

for provider in manager.providers:

    print(provider.name)