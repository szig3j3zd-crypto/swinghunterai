import sys
from datetime import date
from pathlib import Path

# streamlit run はプロジェクトルートをsys.pathへ自動追加しないため、
# `from config.config import ...` 等の絶対importが解決できるよう明示的に追加する。
# これにより `PYTHONPATH` の設定なしで `streamlit run ui/dashboard.py` を実行できる。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from config.config import MAX_PRICE, MIN_MARKET_CAP, MIN_PRICE, MIN_VOLUME
from database.stock_master_reader import get_active_stocks
from database.trade_repository import (
    add_trade,
    create_table as create_trades_table,
    delete_trade,
    get_all_trades,
    has_open_trade,
    update_trade,
)
from database.watchlist_repository import (
    add_watchlist_stock,
    create_table as create_watchlist_table,
    delete_watchlist_stock,
    delete_watchlist_stocks_by_code,
    get_all_watchlist_stocks,
    update_watchlist_timeframe,
)
from service.screening_service import (
    DEFAULT_MODULES,
    MODULE_LABELS,
    evaluate_single_stock,
    format_reason,
    get_jpx400_stocks,
    get_nikkei225_stocks,
    get_prime_stocks,
    get_stock_chart_data,
    get_today_candidates,
)
from service.trade_service import calculate_pnl, group_by_year_and_month, total_pnl
from ui.chart import (
    PLOTLY_CONFIG,
    PLOTLY_CURSOR_OVERRIDE_CSS,
    build_price_chart,
    build_scroll_sync_script,
    compute_visible_window,
)

UNIVERSE_OPTIONS = {
    "東証プライム全体": get_prime_stocks,
    "日経225": get_nikkei225_stocks,
    "JPX日経400": get_jpx400_stocks,
}

SKIP_REASON_LABELS = {
    "volume_too_low": "出来高フィルタ未達",
    "price_out_of_range": "株価フィルタの範囲外",
    "not_in_trend": "トレンド条件未達（移動平均線の並び順・傾き）",
    "no_signal_today": "本日は選択した基準の条件が揃っていません",
    "trend_period_not_found": "トレンド期間を特定できず",
    "below_sma60": "60日線より下",
    "above_sma60": "60日線より上",
    "bounce_limit_exceeded": "反発回数が上限を超過",
}

MA_MODE_LABELS = {"full": "3本版（5>20>60）", "two_line": "2本版（5>20のみ）"}
MA_MODE_LABELS_INVERSE = {v: k for k, v in MA_MODE_LABELS.items()}

DIRECTION_LABELS = {"long": "ロング（買い）", "short": "ショート（売り）"}
TIMEFRAME_LABELS = {"daily": "日足", "weekly": "週足"}
TIMEFRAME_LABELS_INVERSE = {v: k for k, v in TIMEFRAME_LABELS.items()}

# チャートの表示期間（読み込む・横スクロールできる範囲全体）の選択肢。
# 「n年」は1〜10年を1年刻み
CHART_PERIOD_OPTIONS = ["1ヶ月", "3ヶ月", "6ヶ月"] + [f"{n}年" for n in range(1, 11)]

# チャート画面に一度に表示する幅（表示期間の範囲内を、この幅を保ったまま
# 横スクロールして見る）の選択肢。「nヶ月」は3〜11ヶ月を1ヶ月刻み、
# 「n年」は1〜5年を1年刻み
CHART_DISPLAY_WIDTH_OPTIONS = (
    [f"{n}ヶ月" for n in range(3, 12)] + [f"{n}年" for n in range(1, 6)]
)

# 時間足ごとのデフォルト表示期間・表示幅（日足は直近半年、週足は直近3年が
# 読み取りやすいため。表示幅も同じ値をデフォルトにすることで、初期表示は
# 従来どおり期間全体がそのまま見える見た目になる）
CHART_PERIOD_DEFAULT = {"daily": "6ヶ月", "weekly": "3年"}
CHART_DISPLAY_WIDTH_DEFAULT = {"daily": "6ヶ月", "weekly": "3年"}

# 日単位で見たい短い表示幅では「月/日」、それより長い表示幅では「年/月」で
# 出来高チャート下の日付軸ラベルを表示する
CHART_TICK_FORMAT_SHORT_WIDTHS = {"3ヶ月"}


def _period_label_to_offset(label):

    """
    "6ヶ月" / "3年" のような表示期間ラベルをpandas.DateOffsetに変換する
    """

    if label.endswith("ヶ月"):
        return pd.DateOffset(months=int(label[:-2]))

    return pd.DateOffset(years=int(label[:-1]))


def _combine_universes(labels):

    """
    選択された採用指数それぞれの銘柄一覧を結合する（コード重複は除去、和集合）
    """

    frames = [UNIVERSE_OPTIONS[label]() for label in labels]

    return (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset="code")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600)
def _load_stock_search_options():

    """
    銘柄検索用の選択肢一覧を作る（"コード 銘柄名" 形式）

    st.selectboxはラベルの部分一致で絞り込めるため、
    コード・銘柄名のどちらで入力しても候補が絞り込まれる
    """

    stocks = get_active_stocks()

    labels = [
        f"{code} {name}"
        for code, name in zip(stocks["code"], stocks["company_name"])
    ]

    return dict(zip(labels, stocks["code"]))


def _candidate_row(candidate):

    """
    候補1件を表示用のdictに変換する
    """

    risk_reward = candidate["risk_reward_ratio"]

    return {
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
    }


def _on_candidate_table_select(table_key, candidates_list):

    """
    候補一覧の行選択コールバック

    on_select="rerun"（戻り値を毎回読んでfocus_modeを設定する方式）だと、
    表の選択状態はウィジェットとして残り続けるため、他の操作（検索など）で
    フォーカスを切り替えた直後でも、この関数の外側で毎回選択行を読み直すと
    "candidate"に戻ってしまう。コールバックにすることで、実際に行を
    クリックしたときだけfocus_modeが更新されるようにする
    """

    selection = st.session_state[table_key]["selection"]["rows"]

    if selection and selection[0] < len(candidates_list):
        st.session_state["focus_mode"] = "candidate"
        st.session_state["focus_candidate"] = candidates_list[selection[0]]



# チャートの表示切替チェックボックスの既定値。「候補を更新」直後など、
# このブロック自体が一度も描画されないスクリプト実行を挟むと、
# st.checkbox側のkeyに紐づくセッション状態はStreamlitによって破棄される
# （非表示のウィジェットの状態はrunをまたいで残らない仕様のため）。
# そのため、ウィジェット自身のkeyには頼らず、ここで管理する独立した
# session_stateの値を毎回value=に渡して手動で維持する
CHART_DISPLAY_PREF_DEFAULTS = {
    "chart_pref_show_candlestick": True,
    "chart_pref_show_sma3": False,
    "chart_pref_show_sma5": True,
    "chart_pref_show_sma7": False,
    "chart_pref_show_sma10": False,
    "chart_pref_show_sma20": True,
    "chart_pref_show_sma60": True,
    "chart_pref_show_volume": True,
    "chart_pref_show_hover_info": True,
}


def _persistent_checkbox(label, base_key, key_prefix):

    """
    「候補を更新」やフォーカス対象の切り替えを挟んでも状態が消えない
    チェックボックス。st.checkbox()自体は毎回新規生成されるが、
    表示するvalue/変更後の値はpref_key下のsession_stateで独自に管理する

    key_prefixは、同じチャートブロック（_render_chart_block）が
    スキャン/売買銘柄/監視銘柄の各タブで同時に呼ばれてもウィジェットの
    keyが衝突しないようにするための区別用（表示設定はタブごとに独立して覚える）
    """

    pref_key = f"{base_key}_{key_prefix}"

    # ウィジェット自身のkeyとpref_keyを分ける。同じキーを両方に使うと、
    # 「ウィジェットが持つsession_stateは生成後に手動で書き換えられない」
    # というStreamlitの制約に反してStreamlitAPIExceptionになるため
    value = st.checkbox(
        label,
        value=st.session_state.get(pref_key, CHART_DISPLAY_PREF_DEFAULTS[base_key]),
        key=f"{pref_key}_widget",
    )
    st.session_state[pref_key] = value
    return value


def _render_focus_block(label, result, code, chart_timeframe):

    """
    選択中銘柄（個別銘柄検索 or 候補一覧からの選択）の判定結果とチャートを描画する
    """

    st.subheader(f"銘柄詳細: {label}")

    if "error" in result:
        st.error(result["error"])
        return

    if result["is_entry_candidate"]:
        st.success("本日のエントリー候補です")
        st.dataframe(
            pd.DataFrame([_candidate_row(result)]),
            use_container_width=True,
            hide_index=True,
        )
    elif result.get("is_watch_candidate"):
        price = result.get("price")
        price_note = f"　現在の株価: {price}円" if price is not None else ""
        ma20_note = "MA20を上回っています" if result.get("direction") == "short" else "MA20を下回っています"
        st.warning(
            f"監視銘柄です（反発モジュール: {ma20_note}。"
            f"回復すればエントリー候補に昇格します）{price_note}"
        )
    else:
        reason_label = SKIP_REASON_LABELS.get(result["reason"], result["reason"])
        price = result.get("price")
        price_note = f"　現在の株価: {price}円" if price is not None else ""
        st.info(
            f"本日はエントリー候補ではありません"
            f"（理由: {reason_label}）{price_note}"
        )

    _render_chart_block(code, chart_timeframe, key_prefix="scan")


@st.cache_data(ttl=3600)
def _get_cached_chart_data(code, timeframe):

    """
    get_stock_chart_data()のキャッシュ付きラッパー

    表示期間・表示幅・チェックボックスの切替はStreamlitの再実行を伴うが、
    そのたびにDB読込・移動平均/出来高の再計算をやり直すと重く感じるため、
    同じ(code, timeframe)の結果をキャッシュして再描画を軽くする
    """

    return get_stock_chart_data(code, timeframe=timeframe)


def _render_chart_block(code, chart_timeframe, key_prefix):

    """
    株価チャート（表示期間・移動平均線等の表示切替を含む）を描画する

    スキャンタブの銘柄詳細（_render_focus_block）、売買銘柄/監視銘柄タブでの
    銘柄選択時のチャート表示から共通で呼び出す。key_prefixは、複数の
    タブで同時に呼ばれてもウィジェットのkeyが衝突しないようにするための
    区別用（"scan" | "trades" | "watchlist"）
    """

    st.markdown("##### 株価チャート")

    chart_df = _get_cached_chart_data(code, chart_timeframe)
    latest_bar = chart_df.iloc[-1]

    # 表示期間（横スクロールできる範囲全体）と表示幅（画面に一度に表示する
    # 幅。この幅を保ったまま表示期間の範囲内を横スクロールする）を1行、
    # チェックボックスをもう1行にまとめる。gap="xxsmall"と、内容ギリギリの
    # 列幅比率＋末尾の空列で、できるだけ隙間を詰めて左に寄せる
    period_col, width_col, _period_spacer = st.columns(
        [1.3, 1.3, 5], gap="xxsmall", vertical_alignment="bottom"
    )
    # 表示期間・表示幅は、ウィジェット自身のkeyだけでなく独立した
    # session_stateで現在値を管理し、このブロックが描画されないrunを
    # 挟んでも維持する
    period_pref_key = f"chart_period_pref_{key_prefix}_{chart_timeframe}"
    with period_col:
        period_label = st.selectbox(
            "表示期間",
            options=CHART_PERIOD_OPTIONS,
            index=CHART_PERIOD_OPTIONS.index(
                st.session_state.get(period_pref_key, CHART_PERIOD_DEFAULT[chart_timeframe])
            ),
            key=f"chart_period_select_{key_prefix}_{chart_timeframe}",
        )
    st.session_state[period_pref_key] = period_label

    width_pref_key = f"chart_display_width_pref_{key_prefix}_{chart_timeframe}"
    with width_col:
        display_width_label = st.selectbox(
            "チャート表示幅",
            options=CHART_DISPLAY_WIDTH_OPTIONS,
            index=CHART_DISPLAY_WIDTH_OPTIONS.index(
                st.session_state.get(
                    width_pref_key, CHART_DISPLAY_WIDTH_DEFAULT[chart_timeframe]
                )
            ),
            key=f"chart_display_width_select_{key_prefix}_{chart_timeframe}",
        )
    st.session_state[width_pref_key] = display_width_label

    # vertical_alignment="bottom"で、ラベル行が無いチェックボックスを
    # チェックボックス自体の高さに揃える。列幅比率は各チェックボックスの
    # ラベル文字数に応じて調整する。"10日線"・"20日線"・"60日線"（数字2桁）・
    # "出来高"（漢字3文字）は"3日線"等（数字1桁）より横幅が必要で、
    # 同じ比率のままだと折り返してラベルが2行になってしまうため、
    # 他より広めの比率を割り当てる
    (
        cb_candle, cb_sma3, cb_sma5, cb_sma7, cb_sma10,
        cb_sma20, cb_sma60, cb_volume, cb_hover, _cb_spacer,
    ) = (
        st.columns(
            [1.4, 0.9, 0.9, 0.9, 1.2, 1.2, 1.2, 1.1, 1.3, 4],
            gap="xxsmall", vertical_alignment="bottom",
        )
    )
    with cb_candle:
        show_candlestick = _persistent_checkbox(
            "ローソク足", "chart_pref_show_candlestick", key_prefix
        )
    with cb_sma3:
        show_sma3 = _persistent_checkbox("3日線", "chart_pref_show_sma3", key_prefix)
    with cb_sma5:
        show_sma5 = _persistent_checkbox("5日線", "chart_pref_show_sma5", key_prefix)
    with cb_sma7:
        show_sma7 = _persistent_checkbox("7日線", "chart_pref_show_sma7", key_prefix)
    with cb_sma10:
        show_sma10 = _persistent_checkbox("10日線", "chart_pref_show_sma10", key_prefix)
    with cb_sma20:
        show_sma20 = _persistent_checkbox("20日線", "chart_pref_show_sma20", key_prefix)
    with cb_sma60:
        show_sma60 = _persistent_checkbox("60日線", "chart_pref_show_sma60", key_prefix)
    with cb_volume:
        show_volume = _persistent_checkbox("出来高", "chart_pref_show_volume", key_prefix)
    with cb_hover:
        show_hover_info = _persistent_checkbox(
            "詳細情報", "chart_pref_show_hover_info", key_prefix
        )

    # 高値・安値・始値・終値は、チェックボックス行とチャートの間に
    # 専用の行として表示する。以前はPlotly側の注釈として凡例の右横に
    # 埋め込んでいたが、移動平均線の表示切替が増えて凡例が伸びると
    # 注釈と重なって読めなくなるため、独立したStreamlit要素に変更した
    ohlc_text = (
        f"高値: {latest_bar['high']:,.1f}　"
        f"安値: {latest_bar['low']:,.1f}　"
        f"始値: {latest_bar['open']:,.1f}　"
        f"終値: {latest_bar['close']:,.1f}"
    )
    st.markdown(
        f'<div style="font-size:15px;color:#31333F;">{ohlc_text}</div>',
        unsafe_allow_html=True,
    )

    visible_ma = [
        key
        for key, show in [
            ("sma3", show_sma3),
            ("sma5", show_sma5),
            ("sma7", show_sma7),
            ("sma10", show_sma10),
            ("sma20", show_sma20),
            ("sma60", show_sma60),
        ]
        if show
    ]

    last_date = chart_df["date"].max()

    # 表示期間の範囲外のデータはチャートに渡さない。これにより、横スクロールで
    # 移動できる範囲そのものが表示期間で区切られる（表示期間より古いデータは
    # そもそもチャート上に存在しないため、それより先へはスクロールできない）
    period_start = last_date - _period_label_to_offset(period_label)
    chart_df_in_period = (
        chart_df[chart_df["date"] >= period_start].reset_index(drop=True)
    )
    total_bar_count = len(chart_df_in_period)

    # 表示幅（カレンダー上の期間）を、実際のローソク足の本数に変換する
    width_start_date = last_date - _period_label_to_offset(display_width_label)
    visible_bar_count = min(
        max(int((chart_df_in_period["date"] >= width_start_date).sum()), 1),
        total_bar_count,
    )
    max_scroll_offset = total_bar_count - visible_bar_count

    # Streamlitが描画する初期表示は常に最新側（表示幅ぶん）。そこから先の
    # 横スクロールは、チャート下に表示するスクロールバー・チャート上の
    # ドラッグ・矢印キーに任せ、ブラウザ側だけで完結させる
    # （ui.chart.build_scroll_sync_script）ため、Streamlitの再実行は伴わない
    start_offset = max_scroll_offset
    start_index = start_offset
    end_index = start_offset + visible_bar_count - 1
    window_start_date = chart_df_in_period["date"].iloc[start_index]
    window_end_date = chart_df_in_period["date"].iloc[end_index]
    x_range, y_range, volume_range = compute_visible_window(
        chart_df_in_period, window_start_date, window_end_date
    )

    st.plotly_chart(
        build_price_chart(
            chart_df_in_period,
            show_candlestick=show_candlestick,
            visible_ma=visible_ma,
            show_volume=show_volume,
            x_range=x_range,
            y_range=y_range,
            volume_range=volume_range,
            show_hover_info=show_hover_info,
            tick_format=(
                "%m/%d"
                if display_width_label in CHART_TICK_FORMAT_SHORT_WIDTHS
                else "%Y/%m"
            ),
            # uirevisionとkey（下）はPlotlyの標準的な「ズーム状態を維持する」
            # 手法だが、st.plotly_chartでは効かず、チェックボックス操作等の
            # 再読み込みのたびに操作前の状態がリセットされる（Streamlit側の
            # 制限）。表示幅はこの後のx_range/y_rangeで都度綺麗にフィット
            # させているため実害は小さいが、手動でのドラッグ→他の操作、の順で
            # 操作するとドラッグした位置は消える
            uirevision=f"{code}-{chart_timeframe}-{period_label}-{display_width_label}",
        ),
        use_container_width=True,
        config=PLOTLY_CONFIG,
        key=f"price_chart_{key_prefix}_{code}",
    )
    components.html(
        build_scroll_sync_script(
            chart_df_in_period["date"],
            chart_df_in_period["high"],
            chart_df_in_period["low"],
            chart_df_in_period["volume"],
            visible_bar_count,
            start_offset,
        ),
        # トラック自体は細い（14px）が、ドラッグ中に多少上下にぶれても
        # このiframe自身の高さの範囲内であればmousemoveを取りこぼさない
        # ため、少し余裕を持たせた高さにする
        height=32,
    )


# CREATE TABLE IF NOT EXISTS・列追加マイグレーションとも冪等なため、
# 起動のたびに呼んでも問題ない
create_trades_table()
create_watchlist_table()

st.set_page_config(page_title="株探し", layout="wide")
st.markdown(PLOTLY_CURSOR_OVERRIDE_CSS, unsafe_allow_html=True)

st.title("株探し")

with st.sidebar:
    st.header("設定")

    st.subheader("個別銘柄検索")

    stock_search_options = _load_stock_search_options()

    selected_label = st.selectbox(
        "銘柄コードまたは銘柄名で検索",
        options=[""] + list(stock_search_options.keys()),
        index=0,
        help="入力すると候補が絞り込まれます。選択すると下に判定結果を表示します。",
        key="stock_search_select",
        on_change=lambda: st.session_state.update(focus_mode="search"),
    )
    selected_code = stock_search_options.get(selected_label)

    direction = st.radio(
        "方向",
        options=["long", "short"],
        format_func=lambda d: DIRECTION_LABELS[d],
    )

    timeframe = st.radio(
        "時間足",
        options=["daily", "weekly"],
        format_func=lambda t: "日足" if t == "daily" else "週足",
    )

    universe_labels = st.multiselect(
        "採用指数（対象銘柄の絞り込み、複数選択可）",
        options=list(UNIVERSE_OPTIONS.keys()),
        help="複数選択すると、選択した指数すべての銘柄を合わせて対象にします。",
    )

    st.subheader("判断基準")

    module_labels = st.multiselect(
        "候補判断のモジュール（選択した基準をすべて満たす銘柄のみ候補にします）",
        options=list(MODULE_LABELS.values()),
        default=[MODULE_LABELS[name] for name in DEFAULT_MODULES],
        help="entry_signal_spec.md参照。並び順・完全ゴールデンクロス・反発・"
        "並走上昇・半分シグナルから選択します。",
    )
    module_labels_inverse = {v: k for k, v in MODULE_LABELS.items()}
    modules = [module_labels_inverse[label] for label in module_labels]

    ma_mode = "full"
    if "ma_order" in modules:
        ma_mode_label = st.radio(
            "並び順のバリエーション",
            options=list(MA_MODE_LABELS.values()),
        )
        ma_mode = MA_MODE_LABELS_INVERSE[ma_mode_label]

    st.subheader("フィルタ")

    # 「0で無効」は、Noneではなくフィルタ関数がそのまま「制約なし」と
    # 解釈できる値（下限は0、上限はinf）を渡すことで実現する。
    # Noneを渡すとconfig既定値にフォールバックしてしまい、
    # 出来高・時価総額のようにconfig既定値が設定されている項目では
    # 「0で無効」のつもりが無効化されないため。
    min_price_input = st.number_input(
        "株価フィルタ 下限（円、0で無効）",
        min_value=0,
        value=MIN_PRICE or 0,
        step=100,
    )
    max_price_input = st.number_input(
        "株価フィルタ 上限（円、0で無効）",
        min_value=0,
        value=MAX_PRICE or 0,
        step=100,
    )
    min_price = min_price_input
    max_price = max_price_input if max_price_input > 0 else float("inf")

    min_volume = st.number_input(
        "出来高フィルタ（株以上、0で無効）",
        min_value=0,
        value=MIN_VOLUME or 0,
        step=10_000,
    )

    min_market_cap_oku = st.number_input(
        "時価総額フィルタ 下限（億円、0で無効）",
        min_value=0,
        value=int((MIN_MARKET_CAP or 0) / 100_000_000),
        step=100,
        help="他のフィルタを通過した候補にのみ、Yahoo Financeへ問い合わせて絞り込みます"
        "（該当件数分だけ数秒〜十数秒ほど余分に時間がかかります）。",
    )
    min_market_cap = min_market_cap_oku * 100_000_000

    run_button = st.button("候補を更新", type="primary", use_container_width=True)

# 個別銘柄検索の判定は、どのタブが表示中でも使えるようタブの外で評価しておく
lookup_result = None

if selected_code and modules:
    lookup_result = evaluate_single_stock(
        selected_code,
        direction=direction,
        timeframe=timeframe,
        modules=modules,
        ma_mode=ma_mode,
        min_volume=min_volume,
        min_price=min_price,
        max_price=max_price,
    )

if run_button and not universe_labels:
    st.error("サイドバーの「採用指数」を1つ以上選択してください。")
elif run_button and not modules:
    st.error("サイドバーの「判断基準」を1つ以上選択してください。")
elif run_button:
    universe_display = "・".join(universe_labels)

    with st.spinner(f"{universe_display}をスキャン中..."):
        st.session_state["candidates"] = get_today_candidates(
            direction=direction,
            timeframe=timeframe,
            stocks=_combine_universes(universe_labels),
            modules=modules,
            ma_mode=ma_mode,
            min_volume=min_volume,
            min_price=min_price,
            max_price=max_price,
            min_market_cap=min_market_cap,
        )
        st.session_state["direction"] = direction
        st.session_state["timeframe"] = timeframe
        st.session_state["universe_label"] = universe_display

        # 新しいスキャン結果が出たら、検索/前回選択していた銘柄のチャートは消し、
        # 候補一覧を表示する（候補一覧のkeyも変えて選択状態をリセットする）
        st.session_state["focus_mode"] = None
        st.session_state["focus_candidate"] = None
        st.session_state["scan_version"] = st.session_state.get("scan_version", 0) + 1

candidates = st.session_state.get("candidates")


tab_scan, tab_trades, tab_watchlist = st.tabs(["スキャン", "売買銘柄", "監視銘柄"])

with tab_scan:
    st.caption("今日の買い候補一覧")

    # チャート・判定結果の表示位置は候補一覧より上のまま固定する。
    # 検索 or 候補一覧からの選択、どちらで内容を決めるかは候補一覧を
    # 描画した後（選択イベントを受け取った後）に確定するため、
    # 表示位置だけ先に確保しておいて後から中身を描画する
    focus_slot = st.container()

    if candidates is None:
        st.info("サイドバーの「候補を更新」を押してください。")
    elif not candidates:
        st.warning("本日の候補はありません。")
    else:
        rows = [
            {"順位": rank, **_candidate_row(candidate)}
            for rank, candidate in enumerate(candidates, start=1)
        ]

        # scan_versionをkeyに含めることで、新しいスキャンのたびに
        # 選択状態がリセットされた新しい表として扱われる
        table_key = f"candidates_table_{st.session_state.get('scan_version', 0)}"

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            on_select=lambda: _on_candidate_table_select(table_key, candidates),
            selection_mode="single-row",
            key=table_key,
        )

        timeframe_label = "日足" if st.session_state["timeframe"] == "daily" else "週足"
        st.caption(
            f"{len(candidates)}件の候補"
            f"（{st.session_state['direction']} / {timeframe_label} / "
            f"{st.session_state['universe_label']}） "
            "行をクリックするとチャートを表示します。"
        )

    # 確保しておいた表示位置に、確定したフォーカス銘柄（検索 or 候補選択）を描画する
    focus_mode = st.session_state.get("focus_mode")

    with focus_slot:
        if focus_mode == "search" and selected_code:
            _render_focus_block(
                label=selected_label,
                result=lookup_result,
                code=selected_code,
                chart_timeframe=timeframe,
            )
            st.divider()
        elif focus_mode == "candidate" and st.session_state.get("focus_candidate"):
            focus_candidate = st.session_state["focus_candidate"]
            _render_focus_block(
                label=f"{focus_candidate['code']} {focus_candidate['company_name']}",
                result=focus_candidate,
                code=focus_candidate["code"],
                chart_timeframe=st.session_state.get("timeframe", timeframe),
            )
            st.divider()

    # 売買銘柄・監視銘柄への追加は、上のチャートで表示中の銘柄（focus_mode）
    # とだけ連動させる。候補一覧から独立して選び直せる欄を持たせると、
    # チャートで確認した銘柄と違う銘柄を誤って追加できてしまうため
    add_candidate = None

    if focus_mode == "search" and selected_code and lookup_result is not None \
            and "error" not in lookup_result:
        add_candidate = lookup_result
    elif focus_mode == "candidate" and st.session_state.get("focus_candidate"):
        add_candidate = st.session_state["focus_candidate"]

    if add_candidate is not None:
        st.divider()
        st.subheader("売買銘柄・監視銘柄に追加")

        add_label = f"{add_candidate['code']} {add_candidate['company_name']}"
        st.caption(f"追加対象: {add_label}（上に表示中のチャートと同じ銘柄）")

        add_timeframe_label = (
            "日足" if add_candidate["timeframe"] == "daily" else "週足"
        )

        col_trade, col_watch = st.columns(2)

        with col_trade:
            with st.form("add_trade_form"):
                st.write("売買銘柄として追加")
                st.caption(f"時間足: {add_timeframe_label}")

                trade_date_input = st.date_input("取引日", value=date.today())
                entry_price_input = st.number_input(
                    "購入株価", min_value=0.0, value=float(add_candidate["price"])
                )
                quantity_input = st.number_input(
                    "株数", min_value=1, value=100, step=100
                )
                exit_price_input = st.number_input(
                    "決済株価（利確/損切。未決済なら0のまま）",
                    min_value=0.0,
                    value=0.0,
                )

                if st.form_submit_button("売買銘柄に追加"):
                    add_trade(
                        code=add_candidate["code"],
                        company_name=add_candidate["company_name"],
                        direction=add_candidate["direction"],
                        timeframe=add_candidate["timeframe"],
                        trade_date=str(trade_date_input),
                        entry_price=entry_price_input,
                        exit_price=(
                            exit_price_input if exit_price_input > 0 else None
                        ),
                        quantity=int(quantity_input),
                    )

                    # 監視から保有へ卒業したとみなし、監視銘柄に残っていれば
                    # 自動で削除する（手動削除の手間・二重登録を防ぐため）
                    removed_from_watchlist = delete_watchlist_stocks_by_code(
                        add_candidate["code"]
                    )

                    if removed_from_watchlist:
                        st.success(
                            f"{add_label} を売買銘柄（{add_timeframe_label}）に追加し、"
                            "監視銘柄からは削除しました"
                        )
                    else:
                        st.success(
                            f"{add_label} を売買銘柄（{add_timeframe_label}）に追加しました"
                        )

        with col_watch:
            st.write("監視銘柄として追加")
            st.caption(
                f"方向: {DIRECTION_LABELS[add_candidate['direction']]}　"
                f"時間足: {add_timeframe_label}"
            )

            if st.button("監視銘柄に追加", use_container_width=True):
                # 既に保有中（未決済）の銘柄は、売買銘柄と監視銘柄の二重登録に
                # なるため追加しない
                if has_open_trade(add_candidate["code"]):
                    st.error(
                        f"{add_label} は既に保有中（未決済）の売買銘柄として"
                        "登録されているため、監視銘柄には追加できません"
                    )
                else:
                    add_watchlist_stock(
                        code=add_candidate["code"],
                        company_name=add_candidate["company_name"],
                        direction=add_candidate["direction"],
                        timeframe=add_candidate["timeframe"],
                        added_date=str(date.today()),
                    )
                    st.success(f"{add_label} を監視銘柄（{add_timeframe_label}）に追加しました")
    elif candidates or (lookup_result is not None and "error" not in lookup_result):
        st.divider()
        st.info(
            "候補一覧の行を選択するか、個別銘柄検索で銘柄を選ぶと、"
            "チャートを確認したうえで売買銘柄・監視銘柄に追加できます。"
        )


def _render_trades_section():

    """
    売買銘柄タブを描画する

    日足・週足は分けず1つの表にまとめ、「時間足」列で見分ける。
    合計損益・削除・監視銘柄への移動も日足/週足を問わず一括で扱う。

    銘柄の選択は表内の「表示」チェックボックス列で行う（スキャンタブの
    候補一覧の行選択と同じ考え方）。チャートは表より上（focus_slot）に
    表示し、位置もスキャンタブと揃える。「表示」はDBには保存しない
    UI専用の選択状態で、session_state["trades_chart_focus_id"]で管理する
    """

    trades = get_all_trades()

    if not trades:
        st.info(
            "まだ売買銘柄が登録されていません。"
            "「スキャン」タブの候補から追加してください。"
        )
        return

    focus_slot = st.container()

    groups = group_by_year_and_month(trades)

    for year_index, (year, year_pnl, month_groups) in enumerate(groups):
        with st.expander(
            f"{year}年（年間損益: {year_pnl:+,.0f}円）",
            expanded=(year_index == 0),
        ):
            for month, month_pnl, month_trades in month_groups:
                st.markdown(f"**{month}月　月間損益: {month_pnl:+,.0f}円**")

                current_focus_id = st.session_state.get("trades_chart_focus_id")

                display_df = pd.DataFrame(
                    [
                        {
                            "表示": trade["id"] == current_focus_id,
                            "コード": trade["code"],
                            "銘柄名": trade["company_name"],
                            "方向": DIRECTION_LABELS[trade["direction"]],
                            "時間足": TIMEFRAME_LABELS[trade["timeframe"]],
                            "取引日": trade["trade_date"],
                            "購入株価": trade["entry_price"],
                            "決済株価": trade["exit_price"],
                            "株数": trade["quantity"],
                            "損益": calculate_pnl(trade),
                        }
                        for trade in month_trades
                    ],
                    index=[trade["id"] for trade in month_trades],
                )

                edited_df = st.data_editor(
                    display_df,
                    # keyにcurrent_focus_idを含める: 選択が変わるたびに
                    # ウィジェットを新規生成させ、st.data_editorが「表示」列の
                    # 過去の編集状態を引きずって選択が正しく切り替わらない
                    # （チェックが更新されず再実行が終わらない）事象を避ける
                    key=f"trade_editor_{year}_{month}_{current_focus_id}",
                    use_container_width=True,
                    disabled=["コード", "銘柄名", "方向", "取引日", "損益"],
                    column_config={
                        "表示": st.column_config.CheckboxColumn(
                            help="チェックした銘柄のチャートを上に表示します"
                        ),
                        "決済株価": st.column_config.NumberColumn(
                            help="空欄のままなら未決済として扱われます"
                        ),
                        "時間足": st.column_config.SelectboxColumn(
                            options=list(TIMEFRAME_LABELS.values()),
                            help="日足/週足を間違えて登録した場合はここで修正できます",
                        ),
                    },
                )

                month_trade_ids = [trade["id"] for trade in month_trades]
                newly_checked_ids = [
                    trade_id for trade_id in month_trade_ids
                    if bool(edited_df.loc[trade_id, "表示"]) and trade_id != current_focus_id
                ]

                if newly_checked_ids:
                    st.session_state["trades_chart_focus_id"] = newly_checked_ids[0]
                    st.rerun()
                elif (
                    current_focus_id in month_trade_ids
                    and not bool(edited_df.loc[current_focus_id, "表示"])
                ):
                    st.session_state["trades_chart_focus_id"] = None
                    st.rerun()

                for trade in month_trades:
                    row = edited_df.loc[trade["id"]]
                    new_exit_price = (
                        None if pd.isna(row["決済株価"]) else float(row["決済株価"])
                    )
                    new_timeframe = TIMEFRAME_LABELS_INVERSE[row["時間足"]]

                    if (
                        row["購入株価"] != trade["entry_price"]
                        or new_exit_price != trade["exit_price"]
                        or row["株数"] != trade["quantity"]
                        or new_timeframe != trade["timeframe"]
                    ):
                        update_trade(
                            trade["id"],
                            entry_price=float(row["購入株価"]),
                            exit_price=new_exit_price,
                            quantity=int(row["株数"]),
                            timeframe=new_timeframe,
                        )
                        st.rerun()

    focus_id = st.session_state.get("trades_chart_focus_id")
    focus_trade = next((t for t in trades if t["id"] == focus_id), None)

    with focus_slot:
        if focus_trade is not None:
            st.markdown(f"##### {focus_trade['code']} {focus_trade['company_name']}")
            _render_chart_block(
                focus_trade["code"], focus_trade["timeframe"], key_prefix="trades"
            )
            st.divider()
        else:
            st.info(
                "表の「表示」列にチェックを入れると、その銘柄のチャートを"
                "ここに表示します。"
            )
            st.divider()

    st.metric("全期間の損益合計", f"{total_pnl(trades):+,.0f}円")

    st.divider()

    if focus_trade is None:
        st.info(
            "削除・監視銘柄への移動を行うには、表の「表示」列で対象の"
            "銘柄にチェックを入れてください。"
        )
        return

    col_delete, col_move = st.columns(2)

    with col_delete:
        if st.button(
            "選択した取引を削除",
            key="delete_trade_button",
            use_container_width=True,
        ):
            delete_trade(focus_trade["id"])
            st.session_state["trades_chart_focus_id"] = None
            st.rerun()

    with col_move:
        if st.button(
            "選択した取引を監視銘柄に移動",
            key="move_trade_button",
            use_container_width=True,
            help="登録を間違えた場合の修正用。この取引を削除し、"
            "同じ銘柄・方向・時間足で監視銘柄に登録し直します",
        ):
            add_watchlist_stock(
                code=focus_trade["code"],
                company_name=focus_trade["company_name"],
                direction=focus_trade["direction"],
                timeframe=focus_trade["timeframe"],
                added_date=str(date.today()),
            )
            delete_trade(focus_trade["id"])
            st.session_state["trades_chart_focus_id"] = None
            st.rerun()


def _render_watchlist_section():

    """
    監視銘柄タブを描画する（_render_trades_sectionと同様、日足/週足は
    「時間足」列で見分けるだけで表・削除・移動は一括で扱う）。

    銘柄の選択は表内の「表示」チェックボックス列で行い、チャートは表より
    上（focus_slot）に表示する。session_state["watchlist_chart_focus_id"]で
    選択状態を管理する（DBには保存しないUI専用の状態）
    """

    watchlist_stocks = get_all_watchlist_stocks()

    if not watchlist_stocks:
        st.info(
            "まだ監視銘柄が登録されていません。"
            "「スキャン」タブの候補から追加してください。"
        )
        return

    focus_slot = st.container()

    current_focus_id = st.session_state.get("watchlist_chart_focus_id")

    watchlist_display_df = pd.DataFrame(
        [
            {
                "表示": w["id"] == current_focus_id,
                "コード": w["code"],
                "銘柄名": w["company_name"],
                "方向": DIRECTION_LABELS[w["direction"]],
                "時間足": TIMEFRAME_LABELS[w["timeframe"]],
                "追加日": w["added_date"],
            }
            for w in watchlist_stocks
        ],
        index=[w["id"] for w in watchlist_stocks],
    )

    edited_watchlist_df = st.data_editor(
        watchlist_display_df,
        # keyにcurrent_focus_idを含める理由は_render_trades_sectionのコメント参照
        key=f"watchlist_editor_{current_focus_id}",
        use_container_width=True,
        disabled=["コード", "銘柄名", "方向", "追加日"],
        column_config={
            "表示": st.column_config.CheckboxColumn(
                help="チェックした銘柄のチャートを上に表示します"
            ),
            "時間足": st.column_config.SelectboxColumn(
                options=list(TIMEFRAME_LABELS.values()),
                help="日足/週足を間違えて登録した場合はここで修正できます",
            ),
        },
    )

    all_ids = [w["id"] for w in watchlist_stocks]
    newly_checked_ids = [
        wid for wid in all_ids
        if bool(edited_watchlist_df.loc[wid, "表示"]) and wid != current_focus_id
    ]

    if newly_checked_ids:
        st.session_state["watchlist_chart_focus_id"] = newly_checked_ids[0]
        st.rerun()
    elif (
        current_focus_id in all_ids
        and not bool(edited_watchlist_df.loc[current_focus_id, "表示"])
    ):
        st.session_state["watchlist_chart_focus_id"] = None
        st.rerun()

    for stock in watchlist_stocks:
        new_timeframe = TIMEFRAME_LABELS_INVERSE[
            edited_watchlist_df.loc[stock["id"], "時間足"]
        ]

        if new_timeframe != stock["timeframe"]:
            update_watchlist_timeframe(stock["id"], new_timeframe)
            st.rerun()

    focus_id = st.session_state.get("watchlist_chart_focus_id")
    focus_stock = next((w for w in watchlist_stocks if w["id"] == focus_id), None)

    with focus_slot:
        if focus_stock is not None:
            st.markdown(f"##### {focus_stock['code']} {focus_stock['company_name']}")
            _render_chart_block(
                focus_stock["code"], focus_stock["timeframe"], key_prefix="watchlist"
            )
            st.divider()
        else:
            st.info(
                "表の「表示」列にチェックを入れると、その銘柄のチャートを"
                "ここに表示します。"
            )
            st.divider()

    if focus_stock is None:
        st.info(
            "削除・売買銘柄への移動を行うには、表の「表示」列で対象の"
            "銘柄にチェックを入れてください。"
        )
        return

    if st.button("選択した監視銘柄を削除", key="delete_watchlist_button"):
        delete_watchlist_stock(focus_stock["id"])
        st.session_state["watchlist_chart_focus_id"] = None
        st.rerun()

    st.markdown("##### 選択した監視銘柄を売買銘柄に移動")

    with st.form("move_watchlist_to_trade_form"):
        move_trade_date_input = st.date_input("取引日", value=date.today())
        move_entry_price_input = st.number_input(
            "購入株価", min_value=0.0, value=0.0
        )
        move_quantity_input = st.number_input(
            "株数", min_value=1, value=100, step=100
        )
        move_exit_price_input = st.number_input(
            "決済株価（利確/損切。未決済なら0のまま）",
            min_value=0.0,
            value=0.0,
        )

        if st.form_submit_button("売買銘柄に移動"):
            add_trade(
                code=focus_stock["code"],
                company_name=focus_stock["company_name"],
                direction=focus_stock["direction"],
                timeframe=focus_stock["timeframe"],
                trade_date=str(move_trade_date_input),
                entry_price=move_entry_price_input,
                exit_price=(
                    move_exit_price_input if move_exit_price_input > 0 else None
                ),
                quantity=int(move_quantity_input),
            )
            delete_watchlist_stock(focus_stock["id"])
            st.session_state["watchlist_chart_focus_id"] = None
            st.rerun()


with tab_trades:
    st.subheader("売買銘柄（トレード記録）")

    _render_trades_section()


with tab_watchlist:
    st.subheader("監視銘柄")

    _render_watchlist_section()
