from data.providers.jquants_auth import JQuantsAuth


auth = JQuantsAuth()

if auth.login():

    print()

    print("ログイン成功")

else:

    print()

    print("ログイン失敗")