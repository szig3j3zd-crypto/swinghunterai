from jquantsapi import ClientV2

from config.settings import JQUANTS_API_KEY

client = ClientV2(
    api_key=JQUANTS_API_KEY
)

for method in dir(client):
    if not method.startswith("_"):
        print(method)
