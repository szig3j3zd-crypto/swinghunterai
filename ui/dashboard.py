import sys
from pathlib import Path

# streamlit run はプロジェクトルートをsys.pathへ自動追加しないため、
# `from config.config import ...` 等の絶対importが解決できるよう明示的に追加する。
# これにより `PYTHONPATH` の設定なしで `streamlit run ui/dashboard.py` を実行できる。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config.config import MAX_PRICE, MIN_PRICE, MIN_VOLUME
from service.screening_service import format_reason, get_today_candidates

st.set_page_config(page_title="SwingHunter AI", layout="wide")

st.title("SwingHunter AI")
st.caption("今日の買い候補一覧")

with st.sidebar:
    st.header("設定")

    direction = st.radio(
        "方向",
        options=["long", "short"],
        format_func=lambda d: "ロング（買い）" if d == "long" else "ショート（売り）",
    )

    st.caption(
        f"出来高フィルタ: {MIN_VOLUME:,}株以上\n\n"
        f"株価フィルタ: {MIN_PRICE if MIN_PRICE else 'なし'} 〜 "
        f"{MAX_PRICE if MAX_PRICE else 'なし'}"
    )

    run_button = st.button("候補を更新", type="primary", use_container_width=True)

if run_button:
    with st.spinner("東証プライム銘柄をスキャン中..."):
        st.session_state["candidates"] = get_today_candidates(direction=direction)
        st.session_state["direction"] = direction

candidates = st.session_state.get("candidates")

if candidates is None:
    st.info("サイドバーの「候補を更新」を押してください。")
elif not candidates:
    st.warning("本日の候補はありません。")
else:
    rows = []

    for rank, candidate in enumerate(candidates, start=1):
        risk_reward = candidate["risk_reward_ratio"]

        rows.append({
            "順位": rank,
            "コード": candidate["code"],
            "銘柄名": candidate["company_name"],
            "スコア": candidate["score"]["total_score"],
            "判定理由": format_reason(candidate),
            "株価": candidate["price"],
            "損切価格": candidate["stop_loss_price"],
            "利確価格": candidate["take_profit_price"],
            "リスクリワード比": (
                round(risk_reward, 2) if risk_reward is not None else None
            ),
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"{len(candidates)}件の候補（{st.session_state['direction']}）")
