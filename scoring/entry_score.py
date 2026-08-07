def calculate_ma_score(bounce_number):

    """
    MAスコア（最大40点）

    反発が浅い（1発目）ほど、支持線/抵抗線や20日線から離れておらず
    上昇・下落余力が大きいとみなして高得点にする。
    """

    if bounce_number == 1:
        return 40

    if bounce_number == 2:
        return 20

    return 0


def calculate_volume_score(volume_ratio):

    """
    出来高スコア（最大40点）

    出来高倍率（当日出来高 ÷ 出来高平均）が高いほど高得点にする。
    """

    if volume_ratio is None:
        return 0

    if volume_ratio >= 2.0:
        return 40

    if volume_ratio >= 1.5:
        return 20

    return 0


def calculate_risk_score(risk_reward_ratio):

    """
    リスクスコア（最大20点）

    リスクリワード比が目安の2:1以上なら満点にする。
    """

    if risk_reward_ratio is None:
        return 0

    if risk_reward_ratio >= 2.0:
        return 20

    if risk_reward_ratio >= 1.0:
        return 10

    return 0


def calculate_total_score(bounce_number, volume_ratio, risk_reward_ratio):

    """
    売買候補の合計スコアを計算する（100点満点）

    MA(反発回数) + 出来高(出来高倍率) + リスク(リスクリワード比)

    Returns
    -------
    result
        ma_score, volume_score, risk_score, total_score を持つdict
    """

    ma_score = calculate_ma_score(bounce_number)
    volume_score = calculate_volume_score(volume_ratio)
    risk_score = calculate_risk_score(risk_reward_ratio)

    return {
        "ma_score": ma_score,
        "volume_score": volume_score,
        "risk_score": risk_score,
        "total_score": ma_score + volume_score + risk_score,
    }
