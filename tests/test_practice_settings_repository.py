from database.practice_settings_repository import (
    create_table,
    get_initial_capital,
    get_practice_settings,
    update_initial_capital,
    update_last_practice_view,
)


def test_get_initial_capital_defaults_to_zero_when_unset():
    create_table()

    # クリーンな状態を保証するため、明示的に0へ戻してから確認する
    # （他のテスト・手動確認で値が変わっている可能性があるため）
    update_initial_capital(0)

    assert get_initial_capital() == 0


def test_update_initial_capital_roundtrip():
    create_table()

    update_initial_capital(1_000_000)
    assert get_initial_capital() == 1_000_000

    update_initial_capital(500_000)
    assert get_initial_capital() == 500_000

    # 元の状態（0）に戻す
    update_initial_capital(0)
    assert get_initial_capital() == 0


def test_get_practice_settings_defaults_when_unset():
    create_table()
    update_last_practice_view(
        code=None, period_label=None, width_label=None, search_date=None
    )

    settings = get_practice_settings()

    assert settings["last_code"] is None
    assert settings["last_period_label"] is None
    assert settings["last_width_label"] is None
    assert settings["last_search_date"] is None


def test_update_last_practice_view_roundtrip_does_not_touch_capital():
    create_table()
    update_initial_capital(123_000)

    update_last_practice_view(
        code="7203",
        period_label="5年",
        width_label="6ヶ月",
        search_date="2026-09-13",
    )

    settings = get_practice_settings()
    assert settings["last_code"] == "7203"
    assert settings["last_period_label"] == "5年"
    assert settings["last_width_label"] == "6ヶ月"
    assert settings["last_search_date"] == "2026-09-13"
    # 軍資金はupdate_last_practice_viewの影響を受けない
    assert settings["initial_capital"] == 123_000

    # 後始末（他のテストへ影響しないよう既定値に戻す）
    update_initial_capital(0)
    update_last_practice_view(
        code=None, period_label=None, width_label=None, search_date=None
    )
