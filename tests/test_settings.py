from config.settings import JQUANTS_API_KEY


def test_jquants_api_key_is_string():
    # 値そのものはログに出さない（APIキー漏洩防止）。型のみ検証する。
    assert isinstance(JQUANTS_API_KEY, str)
