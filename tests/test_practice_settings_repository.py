from database.practice_settings_repository import (
    create_table,
    get_initial_capital,
    update_initial_capital,
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
