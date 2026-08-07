from scoring.entry_score import (
    calculate_ma_score,
    calculate_risk_score,
    calculate_total_score,
    calculate_volume_score,
)


def test_ma_score_first_bounce_is_full_points():
    assert calculate_ma_score(1) == 40


def test_ma_score_second_bounce_is_half_points():
    assert calculate_ma_score(2) == 20


def test_volume_score_surge_is_full_points():
    assert calculate_volume_score(2.5) == 40


def test_volume_score_above_average_is_half_points():
    assert calculate_volume_score(1.5) == 20


def test_volume_score_below_average_is_zero():
    assert calculate_volume_score(0.8) == 0


def test_volume_score_none_is_zero():
    assert calculate_volume_score(None) == 0


def test_risk_score_meets_target_ratio():
    assert calculate_risk_score(2.0) == 20


def test_risk_score_positive_but_below_target():
    assert calculate_risk_score(1.2) == 10


def test_risk_score_below_one_is_zero():
    assert calculate_risk_score(0.5) == 0


def test_risk_score_none_is_zero():
    assert calculate_risk_score(None) == 0


def test_total_score_sums_all_components():
    result = calculate_total_score(
        bounce_number=1, volume_ratio=2.5, risk_reward_ratio=2.0
    )

    assert result == {
        "ma_score": 40,
        "volume_score": 40,
        "risk_score": 20,
        "total_score": 100,
    }


def test_total_score_can_be_zero():
    result = calculate_total_score(
        bounce_number=3, volume_ratio=0.5, risk_reward_ratio=0.3
    )

    assert result["total_score"] == 0
