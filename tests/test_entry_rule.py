import pandas as pd
import pytest

from rules.entry_rule import evaluate_entry, evaluate_ma_cross_watch, evaluate_ma_order_watch

# テスト用の合成株価（数十〜数百円台）はconfig.MIN_PRICE/MAX_PRICEの
# デフォルト範囲（1000〜5000円）外のため、価格フィルタを検証する目的の
# テスト以外では明示的に無効化する
NO_PRICE_FILTER = {"min_price": 0, "max_price": float("inf")}


def _base_df(sma5, sma20, sma60=None, sma100=None, close=None):
    length = len(sma5)
    close = close if close is not None else list(sma20)

    # sma100は反発モジュール（監視銘柄判定でMA100上昇トレンドを見る）が
    # 常に参照するため、明示指定が無ければcloseより十分低い単調増加のダミー値を
    # 既定にしておく（MA100上昇トレンド条件を常に満たし、full_100モード関連の
    # テストにも影響しないようにする）
    if sma100 is None:
        sma100 = [min(close) - 100 + i for i in range(length)]

    data = {
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "open": close,
        "high": [c + 1 for c in close],
        "low": [c - 1 for c in close],
        "close": close,
        "volume": [600_000] * length,
        "volume_ratio": [2.5] * length,
        "sma5": sma5,
        "sma20": sma20,
        "sma100": sma100,
    }

    if sma60 is not None:
        data["sma60"] = sma60

    return pd.DataFrame(data)


def test_ma_order_and_perfect_golden_cross_combo_is_candidate():
    df = _base_df(
        sma5=[90, 100],
        sma20=[92, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order", "perfect_golden_cross"],
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True
    assert result["modules"] == ["ma_order", "perfect_golden_cross"]
    assert result["bounce_number"] is None


def test_combination_and_fails_when_one_module_is_false():
    # ma_orderは満たすが、直近日にゴールデンクロスは発生していない
    df = _base_df(
        sma5=[90, 91],
        sma20=[80, 81],
        sma60=[70, 70.5],
        close=[90.0, 91.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order", "perfect_golden_cross"],
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_signal_today"


def test_two_line_mode_skips_sma60_filter():
    # sma60は並び順を崩しているが、two_lineモードでは60日線を見ないため候補になる
    df = _base_df(
        sma5=[10, 15],
        sma20=[8, 12],
        sma60=[20, 20],
        close=[10.0, 15.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="two_line",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_ma_order_full_mode_rejects_when_below_sma60():
    df = _base_df(
        sma5=[10, 15],
        sma20=[8, 12],
        sma60=[20, 20.1],
        close=[10.0, 15.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "not_in_trend"


def test_full_100_mode_rejects_when_below_sma100():
    df = _base_df(
        sma5=[10, 15],
        sma20=[8, 12],
        sma100=[20, 20.1],
        close=[10.0, 15.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full_100",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "not_in_trend"


def test_full_100_mode_is_candidate_when_above_sma100():
    df = _base_df(
        sma5=[90, 100],
        sma20=[80, 95],
        sma100=[70, 71],
        close=[90.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full_100",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_full_100_mode_short_is_candidate_when_below_sma100():
    df = _base_df(
        sma5=[110, 100],
        sma20=[120, 105],
        sma100=[130, 129],
        close=[110.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="short", modules=["ma_order"], ma_mode="full_100",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_pullback_100_mode_is_candidate_when_above_sma100():
    # 押し目版: 20>5>100の並びでMA5が下向きでも、MA20・MA100が上向きなら候補になる
    df = _base_df(
        sma5=[12, 10],
        sma20=[15, 16],
        sma100=[8, 9],
        close=[12.0, 10.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="pullback_100",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_pullback_100_mode_rejects_when_price_below_sma100():
    # 並び順・傾きは満たしていても、当日の株価が100日線を下回っていれば
    # 9章の100日線フィルタで除外する
    df = _base_df(
        sma5=[12, 10],
        sma20=[15, 16],
        sma100=[8, 9],
        close=[12.0, 8.5],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="pullback_100",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "below_sma100"


def test_pullback_100_mode_short_is_candidate_when_below_sma100():
    df = _base_df(
        sma5=[10, 12],
        sma20=[8, 7],
        sma100=[15, 14],
        close=[10.0, 12.0],
    )

    result = evaluate_entry(
        df, direction="short", modules=["ma_order"], ma_mode="pullback_100",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_bounce_module_alone_returns_watch_candidate():
    # MA20を少し下回った日（回復前）は監視銘柄として扱う
    df = _base_df(
        sma5=[110, 107, 104, 101.5, 102.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2],
    )

    result = evaluate_entry(df, direction="long", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["is_watch_candidate"] is True
    assert result["reason"] == "bounce_below_ma20_watch"


def test_bounce_watch_is_not_shadowed_by_ma_order_not_in_trend():
    # MA20割れ中はma_order（並び順）の「上向きに並ぶ」条件を満たさないため、
    # 反発と並び順を同時に選択した場合でもnot_in_trendスキップより先に
    # 反発の監視状態を優先し、監視銘柄として拾う
    df = _base_df(
        sma5=[110, 107, 104, 101.5, 102.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order", "bounce"], ma_mode="two_line",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["is_watch_candidate"] is True
    assert result["reason"] == "bounce_below_ma20_watch"


def test_bounce_module_alone_returns_approaching_watch_before_reversal():
    # まだMA20を割っておらず反転前（下落3営業日以上＋接近判定）の日は
    # 「反発の手前」として監視銘柄になる
    df = _base_df(
        sma5=[110, 107, 104, 101.5],
        sma20=[100.0, 100.4, 100.8, 101.2],
    )

    result = evaluate_entry(df, direction="long", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["is_watch_candidate"] is True
    assert result["reason"] == "bounce_approaching_watch"


def test_bounce_module_alone_promotes_to_candidate_on_recovery_day():
    df = _base_df(
        sma5=[110, 107, 104, 101.5, 102.0, 103.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2, 102.6],
    )

    result = evaluate_entry(df, direction="long", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True
    assert result["is_watch_candidate"] is False
    assert result["bounce_number"] == 1


def test_bounce_module_alone_returns_watch_candidate_for_short():
    # ショート版: MA5がMA20を少し上回った日（回復前）は監視銘柄として扱う
    df = _base_df(
        sma5=[90, 93, 96, 98.5, 98.0],
        sma20=[100.0, 99.6, 99.2, 98.8, 97.8],
        # ショートの監視判定はMA100下降トレンド（終値がMA100より下）を要求するため、
        # closeより十分高い単調減少のsma100を明示する
        sma100=[150, 149, 148, 147, 146],
    )

    result = evaluate_entry(df, direction="short", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["is_watch_candidate"] is True
    assert result["reason"] == "bounce_above_ma20_watch"


def test_half_signal_module_alone_is_candidate():
    df = _base_df(
        sma5=[100, 100],
        sma20=[90, 90],
        close=[95.0, 105.0],
    )
    df["open"] = [95.0, 105.0]

    result = evaluate_entry(df, direction="long", modules=["half_signal"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True


def test_parallel_rise_module_alone_is_candidate():
    df = _base_df(
        sma5=[9.0, 9.8, 10.6, 11.0, 11.5],
        sma20=[10.0, 10.2, 10.5, 10.8, 11.1],
        close=[9.0, 9.8, 10.6, 11.0, 11.5],
    )

    result = evaluate_entry(df, direction="long", modules=["parallel_rise"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True


def test_skipped_when_volume_too_low():
    df = _base_df(
        sma5=[90, 100],
        sma20=[92, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )
    df.loc[df.index[-1], "volume"] = 100

    result = evaluate_entry(df, direction="long", modules=["ma_order", "perfect_golden_cross"])

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "volume_too_low"


def test_short_perfect_dead_cross_is_candidate():
    df = _base_df(
        sma5=[110, 100],
        sma20=[108, 105],
        sma60=[120, 118],
        close=[110.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="short", modules=["ma_order", "perfect_golden_cross"],
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_golden_cross_module_fires_even_when_ma20_is_declining():
    # 完全ゴールデンクロスと違い、MA20が下降中のクロスも候補にする
    df = _base_df(
        sma5=[90, 96],
        sma20=[100, 95],
        close=[90.0, 96.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["golden_cross"], **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is True


def test_perfect_golden_cross_does_not_fire_when_ma20_is_declining():
    # 同じデータでも、完全ゴールデンクロス（MA20上向き必須）は候補にならない
    df = _base_df(
        sma5=[90, 96],
        sma20=[100, 95],
        close=[90.0, 96.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["perfect_golden_cross"], **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_signal_today"


def test_golden_cross_module_short_fires_even_when_ma20_is_rising():
    df = _base_df(
        sma5=[110, 94],
        sma20=[100, 105],
        close=[110.0, 94.0],
    )

    result = evaluate_entry(
        df, direction="short", modules=["golden_cross"], **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is True


def test_empty_modules_raises():
    df = _base_df(sma5=[100], sma20=[90])

    with pytest.raises(ValueError):
        evaluate_entry(df, direction="long", modules=[], **NO_PRICE_FILTER)


def test_unknown_module_raises():
    df = _base_df(sma5=[100], sma20=[90])

    with pytest.raises(ValueError):
        evaluate_entry(df, direction="long", modules=["not_a_real_module"], **NO_PRICE_FILTER)


def test_ma_cross_watch_module_alone_is_never_entry_candidate():
    # ma_cross_watchは監視専用（WATCH_ONLY_MODULES）のため、これだけを選択しても
    # 状態・イベント条件の根拠が無く、毎日候補になってしまってはいけない
    # （並び順も上向きに揃えた条件を使い、単なるフォールバック漏れでないか確認する）
    df = _base_df(
        sma5=[90, 100],
        sma20=[80, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_cross_watch"], **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_signal_today"


def test_ma_cross_watch_module_does_not_affect_ma_order_combination():
    # ma_cross_watchを他モジュールと組み合わせても、エントリー候補判定
    # （AND結合）には一切影響しない
    df = _base_df(
        sma5=[90, 100],
        sma20=[80, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )

    result_without = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full",
        **NO_PRICE_FILTER,
    )
    result_with = evaluate_entry(
        df, direction="long", modules=["ma_order", "ma_cross_watch"], ma_mode="full",
        **NO_PRICE_FILTER,
    )

    assert result_with["is_entry_candidate"] == result_without["is_entry_candidate"]


def test_evaluate_ma_cross_watch_before_cross_reason():
    # 前提条件（MA5>MA20>MA60）も満たす
    df = _base_df(
        sma5=[120, 121],
        sma20=[110, 111],
        sma60=[103.5, 104.5],
        sma100=[104, 105],
    )

    result = evaluate_ma_cross_watch(df, direction="long")

    assert result["is_cross_watch_candidate"] is True
    assert result["reason"] == "cross_watch_before"


def test_evaluate_ma_cross_watch_after_cross_reason():
    df = _base_df(
        sma5=[120, 120, 120, 120],
        sma20=[110, 110, 110, 110],
        sma60=[101, 104, 105, 106],
        sma100=[102, 103, 104, 105],
    )

    result = evaluate_ma_cross_watch(df, direction="long")

    assert result["is_cross_watch_candidate"] is True
    assert result["reason"] == "cross_watch_after"


def test_evaluate_ma_cross_watch_no_signal():
    df = _base_df(
        sma5=[100, 100],
        sma20=[90, 90],
        sma60=[70, 71],
        sma100=[104, 105],
    )

    result = evaluate_ma_cross_watch(df, direction="long")

    assert result["is_cross_watch_candidate"] is False
    assert result["reason"] is None


def test_evaluate_ma_cross_watch_precondition_blocks_when_ma20_below_ma60():
    # 実際に報告された不具合の再現: MA60はMA100に接近していても、MA5・MA20が
    # MA60より大きく下にある（実質下降中の）銘柄は監視対象にしない
    df = _base_df(
        sma5=[100, 100],
        sma20=[90, 90],
        sma60=[103.5, 104.5],
        sma100=[104, 105],
    )

    result = evaluate_ma_cross_watch(df, direction="long")

    assert result["is_cross_watch_candidate"] is False
    assert result["reason"] is None


def test_evaluate_ma_order_watch_after_cross_reason_full_mode():
    # "full"バリエーション（5>20>60）はMA20とMA60を監視する
    # （前提条件のMA5>MA20も満たす）。day3でMA20がMA60を上抜け、
    # day6まで1%以内を維持する
    df = _base_df(
        sma5=[120] * 7,
        sma20=[99.5, 100.3, 101.2, 103.5, 104.3, 105.2, 106.4],
        sma60=[100, 101, 102, 103, 104, 105, 106],
    )

    result = evaluate_ma_order_watch(df, direction="long", ma_mode="full")

    assert result["is_order_watch_candidate"] is True
    assert result["reason"] == "order_watch_after"


def test_evaluate_ma_order_watch_before_cross_is_not_watch():
    # クロス前（接近中。MA20がMA60をまだ下回ったまま）は並び順ウォッチの
    # 対象にしない（並び順としては未完成のため）
    df = _base_df(
        sma5=[120, 120],
        sma20=[102.5, 103.5],
        sma60=[103, 104],
    )

    result = evaluate_ma_order_watch(df, direction="long", ma_mode="full")

    assert result["is_order_watch_candidate"] is False
    assert result["reason"] is None


def test_evaluate_ma_order_watch_after_cross_reason_full_100_mode():
    # "full_100"バリエーション（5>20>100）はMA20とMA100を監視する
    # （前提条件のMA5>MA20も満たす）
    df = _base_df(
        sma5=[110, 110, 110, 110],
        sma20=[101, 104, 105, 106],
        sma100=[102, 103, 104, 105],
    )

    result = evaluate_ma_order_watch(df, direction="long", ma_mode="full_100")

    assert result["is_order_watch_candidate"] is True
    assert result["reason"] == "order_watch_after"


def test_evaluate_ma_order_watch_no_signal():
    df = _base_df(
        sma5=[110, 110],
        sma20=[70, 71],
        sma60=[103, 104],
    )

    result = evaluate_ma_order_watch(df, direction="long", ma_mode="full")

    assert result["is_order_watch_candidate"] is False
    assert result["reason"] is None


def test_evaluate_ma_order_watch_precondition_blocks_when_ma5_below_ma20():
    # 実際に報告された不具合の再現: MA20とMA60はクロス済み・1%以内でも、
    # MA5がMA20を下回ったまま（並び順としてはショート寄り）の銘柄は
    # 監視対象にしない
    df = _base_df(
        sma5=[90] * 7,
        sma20=[99.5, 100.3, 101.2, 103.5, 104.3, 105.2, 106.4],
        sma60=[100, 101, 102, 103, 104, 105, 106],
    )

    result = evaluate_ma_order_watch(df, direction="long", ma_mode="full")

    assert result["is_order_watch_candidate"] is False
    assert result["reason"] is None


def test_evaluate_ma_order_watch_does_not_affect_entry_candidate_and_combination():
    # 並び順ウォッチはevaluate_entry()のAND結合とは無関係の独立関数のため、
    # 呼び出してもentry_candidate判定には一切影響しない
    df = _base_df(
        sma5=[90, 100],
        sma20=[80, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )

    result_before = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full", **NO_PRICE_FILTER,
    )
    evaluate_ma_order_watch(df, direction="long", ma_mode="full")
    result_after = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full", **NO_PRICE_FILTER,
    )

    assert result_before["is_entry_candidate"] == result_after["is_entry_candidate"]
