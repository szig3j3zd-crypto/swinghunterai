import os
import sys
from datetime import date
from pathlib import Path

# streamlit run はプロジェクトルートをsys.pathへ自動追加しないため、
# `from config.config import ...` 等の絶対importが解決できるよう明示的に追加する。
# これにより `PYTHONPATH` の設定なしで `streamlit run ui/dashboard.py` を実行できる。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

# Streamlit Community Cloudの「Secrets」設定は st.secrets からしか読めないため、
# config/settings.py が使う os.getenv 経由でローカル(.env)と同じコードパスで
# 読めるよう、他のimport（config.settingsをロードする前）で環境変数へ橋渡しする
try:
    for _key, _value in st.secrets.items():
        os.environ.setdefault(_key, str(_value))
except Exception:
    pass

import pandas as pd

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
    update_watchlist_priority,
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
    get_today_scan_results,
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
    "below_sma100": "100日線より下",
    "above_sma100": "100日線より上",
    "bounce_limit_exceeded": "反発回数が上限を超過",
}

WATCH_REASON_LABELS = {
    "bounce_approaching_watch": "MA20に接近中です（反発の反転待ち）。反転すればエントリー候補に昇格します",
    "bounce_below_ma20_watch": "MA20を下回っています。回復すればエントリー候補に昇格します",
    "bounce_above_ma20_watch": "MA20を上回っています。回復すればエントリー候補に昇格します",
    "cross_watch_before": "MA60がMA100に接近中です（クロス待ち）。クロスすれば確認期間として監視を継続します",
    "cross_watch_after": "MA60がMA100を突き抜けています（クロス後の確認期間中です）",
    "order_watch_after": "並び順を構成するMAが交差し、並び順が完成しました（完成後の確認期間中です）",
}

MA_MODE_LABELS = {
    "full": "3本版（5>20>60）",
    "full_100": "3本版（5>20>100）",
    "pullback_100": "押し目版（20>5>100）",
    "two_line": "2本版（5>20のみ）",
}
MA_MODE_LABELS_INVERSE = {v: k for k, v in MA_MODE_LABELS.items()}

DIRECTION_LABELS = {"long": "ロング（買い）", "short": "ショート（売り）"}
TIMEFRAME_LABELS = {"daily": "日足", "weekly": "週足", "monthly": "月足"}
TIMEFRAME_LABELS_INVERSE = {v: k for k, v in TIMEFRAME_LABELS.items()}

# チャートの表示期間（読み込む・横スクロールできる範囲全体）の選択肢。
# 「n年」は1〜10年を1年刻み
CHART_PERIOD_OPTIONS = ["1ヶ月", "3ヶ月", "6ヶ月"] + [f"{n}年" for n in range(1, 11)]

# チャート画面に一度に表示する幅（表示期間の範囲内を、この幅を保ったまま
# 横スクロールして見る）の選択肢。「nヶ月」は2〜11ヶ月を1ヶ月刻み、
# 「n年」は1〜5年を1年刻み
CHART_DISPLAY_WIDTH_OPTIONS = (
    [f"{n}ヶ月" for n in range(2, 12)] + [f"{n}年" for n in range(1, 6)]
)

# 表示期間は日足/週足/月足で切り替えても変えない（値も選択状態も共通）。
# 時間足ごとに個別のデフォルト・選択状態を持たせていた頃は、切り替える
# たびにスクロールできる範囲や初期ズーム幅が変わってしまい、表示位置の
# 復元基準もそのたびにズレて表示が安定しなかったため、時間足に依存しない
# 単一のデフォルト値にした
CHART_PERIOD_DEFAULT = "5年"
CHART_DISPLAY_WIDTH_DEFAULT = "6ヶ月"

# 表示幅ラベル（暦期間）を時間足ごとのローソク足本数に変換する際の、
# 1暦日あたりのおおよその本数。日足は営業日（週5日/7日）、週足は1週間に
# 1本、月足は1ヶ月（平均30.44暦日）に1本という概算値。表示幅を時間足間で
# 揃える（CHART_DISPLAY_WIDTH_OPTIONSから本数が最も近いラベルを選ぶ）ための
# ものであり、実際の本数計算自体は_render_chart_block側で実データ
# （chart_df_in_period）から数える
CHART_BARS_PER_CALENDAR_DAY = {
    "daily": 5 / 7,
    "weekly": 1 / 7,
    "monthly": 1 / 30.4368,
}

# 日単位で見たい短い表示幅では「月/日」、それより長い表示幅では「年/月」で
# 出来高チャート下の日付軸ラベルを表示する
CHART_TICK_FORMAT_SHORT_WIDTHS = {"2ヶ月", "3ヶ月"}

def _compute_bar_edge_padding(dates):

    """
    表示期間の各端（表示幅の左右端）のバーの中心座標ちょうどにx軸の端を
    合わせると、そのバー自身の幅の半分が軸の外にはみ出して半分しか
    描画されなくなる。実際のバー間隔（暦日換算の中央値）の4割を両端に
    余白として足し、端のバーが欠けずに全体表示されるようにする
    （ui.chart.build_scroll_sync_scriptのJS側、及び矢印キー・スクロール
    バーで動かした先でも同様の理由で発生するため、同じ考え方でJS側でも
    バーの実データから同じ倍率を計算している）

    2026-08-30改訂: 以前は日足で実測した固定値（9時間36分＝1日の4割）
    だったが、週足・月足はバー間隔が1日よりずっと長いため、この固定値
    では余白が全く足りず、矢印キーで動かした先や初期表示でローソク足の
    端が半分しか見えない不具合があった。バー間隔の中央値（日足なら
    約1日、週足なら約7日、月足なら約30日）から都度計算することで、
    どの時間足でも同じ比率の余白になるようにした
    """

    diffs = dates.diff().dropna()
    typical_gap = diffs.median() if not diffs.empty else pd.Timedelta(days=1)
    return typical_gap * 0.4


def _period_label_to_offset(label):

    """
    "6ヶ月" / "3年" のような表示期間ラベルをpandas.DateOffsetに変換する
    """

    if label.endswith("ヶ月"):
        return pd.DateOffset(months=int(label[:-2]))

    return pd.DateOffset(years=int(label[:-1]))


# _width_label_to_bar_count()で表示幅ラベルを暦日数に変換する際の基準日。
# DateOffsetの加算結果（月内日数の違い等）が呼び出しのたびにブレないよう
# 固定の日付を使う（本数はあくまで時間足間の比較用の概算値のため、
# 基準日自体に意味はない）
_BAR_COUNT_ANCHOR = pd.Timestamp("2020-01-01")


def _width_label_to_bar_count(label, timeframe):

    """
    表示幅ラベル（"6ヶ月"等）を、指定した時間足でのおおよそのローソク足
    本数に変換する（CHART_BARS_PER_CALENDAR_DAYによる概算。日足/週足/月足で
    表示幅を揃える際の比較に使う）
    """

    offset = _period_label_to_offset(label)
    days = (_BAR_COUNT_ANCHOR + offset - _BAR_COUNT_ANCHOR).days

    return days * CHART_BARS_PER_CALENDAR_DAY[timeframe]


def _closest_width_label_for_bar_count(target_bar_count, timeframe):

    """
    指定した時間足で、目標本数に最も近いローソク足本数になる表示幅ラベルを
    CHART_DISPLAY_WIDTH_OPTIONSから選ぶ
    """

    return min(
        CHART_DISPLAY_WIDTH_OPTIONS,
        key=lambda label: abs(
            _width_label_to_bar_count(label, timeframe) - target_bar_count
        ),
    )


def _is_mobile_viewport():

    """
    User-Agentからスマホでのアクセスかどうかを判定する

    株価チャート（_render_chart_block）の高さを、スマホでは画面幅に対して
    縦長になりすぎないよう縮めるために使う。JS側からチャートの高さを
    後から書き換える方式も試したが、st.plotly_chartが外部からの高さ変更を
    検知するたびに元の高さへ戻してしまい（ちらつきの原因になり）安定
    しなかったため、最初からPython側で小さい高さを生成する方式にした。
    "Mobi"はiPhone・Androidスマホの主要なUAに共通して含まれる文字列
    （タブレットのUAには含まれないことが多く、その場合はPC同様の
    高さになる）
    """

    user_agent = (st.context.headers or {}).get("User-Agent", "")

    return "Mobi" in user_agent


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

    判断基準が未選択（no_modules_selected）の場合は、出来高・株価フィルタを
    通過しただけの銘柄一覧のため、スコアや損切/利確価格は持たない

    既に監視銘柄として登録済みの銘柄（is_already_watchlisted）は、「備考」列に
    目印を付ける（行全体のグレー表示はst.dataframe呼び出し側で行う。
    _watch_candidate_rowと同じ考え方）
    """

    remark = "監視銘柄登録済み" if candidate.get("is_already_watchlisted") else ""

    if candidate.get("no_modules_selected"):
        return {
            "コード": candidate["code"],
            "銘柄名": candidate["company_name"],
            "株価": candidate["price"],
            "備考": remark,
        }

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
        "備考": remark,
    }


def _watch_status_text(candidate):

    """
    監視銘柄候補の状況テキストを組み立てる

    反発（entry_signal_spec.md 6章）・MA60/100接近ウォッチ（14章）・並び順
    ウォッチ（15章）は判定ロジックが別物で、1銘柄が複数の監視条件に同時に
    該当することがあるため、該当する基準をすべて「／」で区切って列挙する
    （1つのみ該当する場合はその基準のみ表示する）
    """

    parts = []

    if candidate.get("is_watch_candidate"):
        reason = WATCH_REASON_LABELS.get(candidate.get("reason"), candidate.get("reason"))
        parts.append(f"[反発] {reason}")

    if candidate.get("is_cross_watch_candidate"):
        reason = WATCH_REASON_LABELS.get(
            candidate.get("cross_watch_reason"), candidate.get("cross_watch_reason")
        )
        parts.append(f"[MA60/100接近] {reason}")

    if candidate.get("is_order_watch_candidate"):
        reason = WATCH_REASON_LABELS.get(
            candidate.get("order_watch_reason"), candidate.get("order_watch_reason")
        )
        parts.append(f"[並び順] {reason}")

    return "／".join(parts)


def _watch_candidate_row(candidate):

    """
    監視銘柄候補1件を表示用のdictに変換する（entry_signal_spec.md 6章の
    「反発の手前」・14章のMA60/100接近ウォッチをまとめた1つの表で使う。
    エントリー候補と違いスコア・損切/利確価格を持たないため
    _candidate_rowとは別の列構成にする）

    既に監視銘柄として登録済みの銘柄（is_already_watchlisted）は、状況欄の
    先頭に目印を付ける（行全体のグレー表示はst.dataframe呼び出し側で行う）
    """

    status = _watch_status_text(candidate)

    if candidate.get("is_already_watchlisted"):
        status = f"[監視銘柄登録済み] {status}" if status else "[監視銘柄登録済み]"

    return {
        "コード": candidate["code"],
        "銘柄名": candidate["company_name"],
        "株価": candidate["price"],
        "状況": status,
    }


def _on_candidate_table_select(table_key, candidates_list):

    """
    候補一覧の行選択コールバック

    on_select="rerun"（戻り値を毎回読んでfocus_modeを設定する方式）だと、
    表の選択状態はウィジェットとして残り続けるため、他の操作（検索など）で
    フォーカスを切り替えた直後でも、この関数の外側で毎回選択行を読み直すと
    "candidate"に戻ってしまう。コールバックにすることで、実際に行を
    クリックしたときだけfocus_modeが更新されるようにする

    既に監視銘柄として登録済みの銘柄（is_already_watchlisted）でも選択でき、
    チャートを表示する（2026-08-30改訂。以前は選択自体を無視していたが、
    グレー表示は登録済みであることが分かればよく、チャート確認まで
    ブロックする必要はないという要望を受けて変更した。グレー表示自体は
    引き続き行う）

    候補一覧・監視銘柄候補一覧は別々のst.dataframeウィジェットのため、
    片方で行を選択しても、もう片方のチェックは自動では外れない。
    watch_selection_versionをインクリメントして監視銘柄候補一覧のkeyを
    変えることで、次のレンダリングでその表を選択状態の無い新しいウィジェット
    として扱わせ、チェックが2つ同時に付いたままにならないようにする
    """

    selection = st.session_state[table_key]["selection"]["rows"]

    if not selection or selection[0] >= len(candidates_list):
        return

    selected_candidate = candidates_list[selection[0]]

    st.session_state["focus_mode"] = "candidate"
    st.session_state["focus_candidate"] = selected_candidate
    st.session_state["watch_selection_version"] = (
        st.session_state.get("watch_selection_version", 0) + 1
    )
    st.session_state["scroll_to_chart"] = True


def _on_watch_candidate_table_select(table_key, candidates_list):

    """
    監視銘柄候補一覧の行選択コールバック

    _on_candidate_table_selectと同様、既に監視銘柄として登録済みの銘柄
    （is_already_watchlisted）でも選択でき、チャートを表示する
    （2026-08-30改訂。グレー表示自体は引き続き行う）

    候補一覧側のチェックが付いたままにならないよう、candidates_selection_version
    をインクリメントして候補一覧のkeyを変える（_on_candidate_table_select参照）
    """

    selection = st.session_state[table_key]["selection"]["rows"]

    if not selection or selection[0] >= len(candidates_list):
        return

    selected_candidate = candidates_list[selection[0]]

    st.session_state["focus_mode"] = "candidate"
    st.session_state["focus_candidate"] = selected_candidate
    st.session_state["candidates_selection_version"] = (
        st.session_state.get("candidates_selection_version", 0) + 1
    )
    st.session_state["scroll_to_chart"] = True


def _style_already_watchlisted_rows(df, candidates_list):

    """
    候補一覧・監視銘柄候補一覧のうち、既に監視銘柄として登録済みの行を
    グレーアウトする

    st.dataframe()はpandas Styler（.style.apply()等で作成）を渡しても
    行選択（on_select）が使えるため、選択機能はそのまま維持しつつ見た目だけ
    変更できる。Styler経由だと数値列がst.dataframeの既定フォーマットを
    通らず末尾に「.000000」等が付いてしまうため、数値列だけ明示的に
    フォーマットし直す（末尾の0を落としつつ、実用上十分な精度は保つ）
    """

    def _style_row(row):
        if candidates_list[row.name].get("is_already_watchlisted"):
            # 既に監視銘柄に登録済みであることを示す表示専用のスタイル。
            # 選択自体は引き続きでき、選択すればチャートも表示される
            # （_on_candidate_table_select等参照。2026-08-30改訂で選択の
            # ブロックをやめた）。文字色だけだと選択可能な行との違いが
            # 分かりにくいため、背景色も付けて一目でわかるようにする
            # （2026-08-29改訂）
            return [
                "color: #999999; font-style: italic; background-color: #ececec"
            ] * len(row)
        return [""] * len(row)

    numeric_columns = df.select_dtypes(include="number").columns

    return (
        df.style
        .apply(_style_row, axis=1)
        .format({column: "{:.10g}" for column in numeric_columns})
    )


def _consume_scroll_flags():

    """
    スクロールが必要かどうかのフラグを読み取り、消費する（session_stateから
    pop。次の再実行ではユーザーが再度操作しない限りスクロールしないように
    するため）。_render_scroll_trigger()と分けているのは、フラグの消費は
    1回だけ行いたい一方、実際のスクロール実行（JS埋め込み）は複数箇所で
    行いたいため（_render_scroll_trigger()のdocstring参照）

    Returns
    -------
    (scroll_to_chart, scroll_to_page_top)
        - scroll_to_chart: 銘柄をチェックしてチャート表示位置（focus_slot）が
          変わった場合に立つ
        - scroll_to_page_top: サイドバーの「銘柄検索を開始」で新しいスキャン結果を
          表示した場合に立つ
    """

    scroll_to_chart = st.session_state.pop("scroll_to_chart", False)
    scroll_to_page_top = st.session_state.pop("scroll_to_page_top", False)

    return scroll_to_chart, scroll_to_page_top


def _render_scroll_trigger(scroll_to_chart, scroll_to_page_top):

    """
    必要なら該当する位置まで自動でスクロールするJSを埋め込む

    - scroll_to_chart: 「株価チャート」の見出し（_render_chart_blockの
      `st.markdown("##### 株価チャート")`）の直前にある見出し（銘柄コード・
      銘柄名、またはスキャンタブの「銘柄詳細: ...」）がビューポート上端に
      来るまでスクロールする（2026-08-29改訂。以前は「株価チャート」の
      見出し自体をスクロール先にしていたため、その上にある銘柄コード・
      銘柄名が画面外に隠れてしまっていた）
    - scroll_to_page_top: ページの一番上までスクロールする

    st.html()呼び出し自体は毎回同じ形で（スクロール不要な場合は空のscriptで）
    行い、呼び出す/呼び出さないを条件分岐しない。st.tabs()より前で呼ぶ
    箇所があるため、要素の有無を再実行のたびに変えると、st.tabs()がキーの
    無いウィジェットとして位置ベースで再識別されてしまい、選択中のタブが
    変わるたびに「スキャン」タブへリセットされてしまう不具合があった
    （2026-08-23発見・修正）

    この関数はスキャン・売買銘柄・監視銘柄それぞれのタブ本文の末尾、および
    st.tabs()の直前の計4箇所から、同じ(scroll_to_chart, scroll_to_page_top)
    を渡して呼ぶ（2026-08-30改訂。念のための多重化。下記のnonceで根本修正
    済みのため実際には最初の呼び出しだけで足りるはずだが、コストが低いため
    保険として残す）。「候補一覧の下の方の行を選択してもチャート画面まで
    戻らない」不具合の原因は2つあり、両方修正した（実機・自動テストで
    再現・複数回の選択を繰り返しても再発しないことを確認済み）
    - iframe（st.components.v1.html）は、ページが大きくスクロールされて
      いて描画対象がビューポートから遠く離れていると、ブラウザ側の描画
      最適化によりiframe内のJSが実行されないことがあった → iframeを
      使わないst.html(unsafe_allow_javascript=True)に変更
    - scroll_to_chart時のスクリプトの中身は、選択した銘柄によらず
      （「株価チャート」の見出しを探すだけの汎用処理のため）毎回まったく
      同じ文字列になる。StreamlitはHTML文字列が前回と同じだとDOMを更新
      しない（＝scriptタグを再実行しない）ため、1回目の選択では動くが
      2回目以降は同じ内容と判定されて実行されなかった → 実行のたびに
      変わる値（連番）をscriptタグの中身に混ぜ込み、内容が必ず変わる
      ようにした（下記nonce参照）
    """

    if scroll_to_chart:
        script = """
            function scrollToChartHeading() {
                var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                for (var i = 0; i < headings.length; i++) {
                    var heading = headings[i];
                    if (heading.textContent.trim() === '株価チャート'
                            && heading.offsetParent !== null) {
                        // 銘柄コード・銘柄名（またはスキャンタブの「銘柄詳細:
                        // ...」）の見出しは「株価チャート」の直前にあるため、
                        // そちらを優先してスクロール先にする（画面上端が
                        // 銘柄コード・銘柄名から始まるようにするため）
                        var target = heading;
                        for (var j = i - 1; j >= 0; j--) {
                            if (headings[j].offsetParent !== null) {
                                target = headings[j];
                                break;
                            }
                        }
                        target.scrollIntoView({behavior: 'instant', block: 'start'});
                        return true;
                    }
                }
                return false;
            }

            if (!scrollToChartHeading()) {
                setTimeout(function() {
                    if (!scrollToChartHeading()) {
                        // メインコンテンツはwindow/bodyではなく、
                        // section[data-testid="stMain"]自身がスクロールする
                        // 独立したコンテナになっている（Streamlitのレイアウト仕様）
                        var mainSection = document.querySelector(
                            'section[data-testid="stMain"]'
                        );
                        if (mainSection) {
                            mainSection.scrollTo({top: 0, behavior: 'instant'});
                        }
                    }
                }, 300);
            }
        """
    elif scroll_to_page_top:
        script = """
            var mainSection = document.querySelector(
                'section[data-testid="stMain"]'
            );
            if (mainSection) {
                mainSection.scrollTo({top: 0, behavior: 'instant'});
            }
        """
    else:
        script = ""

    # position: fixedはドキュメントの通常のフローから外れ、スクロールする
    # 祖先ではなくビューポート自体を基準に配置されるため、DOM上の実際の
    # 位置（大きくスクロールした表の近く等）に関わらず常にビューポート内
    # （左上、0×0）にあるように見せかけられる。nonceはscriptタグの中身を
    # 毎回変えて再実行を強制するためのもの（詳細はdocstring参照）
    nonce = st.session_state.get("_scroll_script_nonce", 0) + 1
    st.session_state["_scroll_script_nonce"] = nonce
    st.html(
        f'<div style="position:fixed;top:0;left:0;width:0;height:0;overflow:hidden;">'
        f"<script>/* {nonce} */(function() {{ {script} }})();</script>"
        f"</div>",
        unsafe_allow_javascript=True,
    )

def _style_delete_buttons_red():

    """
    削除ボタン（取り消せない操作）の文字だけを赤くする（背景・枠線は
    変えない）。2026-08-30改訂: 当初はtype="primary"で背景ごと赤くして
    いたが、「赤文字は文字だけを赤にしてほしい」との指摘を受けてこちらに
    変更した。Streamlitはst.button()のkey引数をDOMに公開しないため、CSSの
    key属性セレクタでは狙えず、ボタンの表示テキストで判定してJSで
    style.colorを直接書き換える。nonceで再実行を強制する理由は
    _render_scroll_trigger()のdocstring参照（同じ内容のHTML文字列は
    Streamlitに再実行されないため）
    """

    nonce = st.session_state.get("_delete_button_style_nonce", 0) + 1
    st.session_state["_delete_button_style_nonce"] = nonce

    labels_js = ", ".join(
        f'"{label}"'
        for label in ["監視銘柄を削除", "選択した取引を削除"]
    )

    script = f"""
        var labels = [{labels_js}];
        document.querySelectorAll('button').forEach(function(btn) {{
            if (labels.indexOf(btn.textContent.trim()) === -1) {{
                return;
            }}
            btn.style.color = '#ff4b4b';
            btn.querySelectorAll('p, div').forEach(function(el) {{
                el.style.color = '#ff4b4b';
            }});
        }});
    """

    st.html(
        f'<div style="position:fixed;top:0;left:0;width:0;height:0;overflow:hidden;">'
        f"<script>/* {nonce} */(function() {{ {script} }})();</script>"
        f"</div>",
        unsafe_allow_javascript=True,
    )


# チャートの表示切替チェックボックスの既定値。「銘柄検索を開始」直後など、
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
    "chart_pref_show_sma100": True,
    "chart_pref_show_volume": True,
    "chart_pref_show_hover_info": True,
}


def _persistent_checkbox(label, base_key, key_prefix):

    """
    「銘柄検索を開始」やフォーカス対象の切り替えを挟んでも状態が消えない
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

    見出しの直後はステータスメッセージ（st.success/st.warning/st.info）のみに
    とどめ、詳細テーブルは挟まずすぐ株価チャートを表示する（2026-08-29改訂。
    以前はエントリー候補の場合のみコード・銘柄名・スコア等の詳細テーブルを
    挟んでいたが、売買銘柄・監視銘柄タブ（銘柄名の見出し→すぐチャート）と
    見え方が揃わず、自動スクロール先の直後に見慣れない画面が挟まる形に
    なっていたため削除した。詳細情報は候補一覧の表に既に出ている）
    """

    st.subheader(f"銘柄詳細: {label}")

    if "error" in result:
        st.error(result["error"])
        return

    if result.get("no_modules_selected"):
        price = result.get("price")
        price_note = f"　現在の株価: {price}円" if price is not None else ""
        st.info(f"サイドバーの「判断基準」が未選択のため、判定は行っていません{price_note}")
        _render_chart_block(code, chart_timeframe, key_prefix="scan")
        return

    if result["is_entry_candidate"]:
        st.success("本日のエントリー候補です")
    else:
        price = result.get("price")
        price_note = f"　現在の株価: {price}円" if price is not None else ""

        # 反発・MA60/100接近ウォッチ・並び順ウォッチは判定ロジックが別物のため、
        # 同じ銘柄が複数の監視条件に該当することがある。該当する基準をすべて
        # 1つのメッセージにまとめて表示する（_watch_status_text参照）
        if (
            result.get("is_watch_candidate")
            or result.get("is_cross_watch_candidate")
            or result.get("is_order_watch_candidate")
        ):
            st.warning(f"監視銘柄です（{_watch_status_text(result)}）{price_note}")
        else:
            reason_label = SKIP_REASON_LABELS.get(result["reason"], result["reason"])
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

    chart_timeframe
        表示する時間足。サイドバーの「時間足」ラジオボタン（1つだけ）に
        一本化しており、スキャン・売買銘柄・監視銘柄のどのタブのチャートも
        常にこの値を使う（売買銘柄/監視銘柄タブの表内「時間足」列は
        登録データそのものの日足/週足修正用で、これとは別物）
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
    # 挟んでも維持する。表示期間はkey・session_stateとも時間足を含めない
    # （日足/週足/月足を切り替えても値を変えないため）
    period_pref_key = f"chart_period_pref_{key_prefix}"
    with period_col:
        period_label = st.selectbox(
            "表示期間",
            options=CHART_PERIOD_OPTIONS,
            index=CHART_PERIOD_OPTIONS.index(
                st.session_state.get(period_pref_key, CHART_PERIOD_DEFAULT)
            ),
            key=f"chart_period_select_{key_prefix}",
        )
    st.session_state[period_pref_key] = period_label

    # 表示幅は「ローソク足の本数」を時間足に依存しない基準として保持する
    # （key・session_stateとも時間足を含めない）。表示するラベル自体は
    # 時間足ごとに、その本数に最も近いものを選び直す（2026-08-30改訂。
    # 以前はラベル文字列をそのまま共有していたため、同じ「6ヶ月」でも
    # 日足は約130本・週足は約26本・月足は約6本と表示本数が大きく異なり、
    # ローソク足の見た目の太さが時間足を切り替えるたびに揃わなかった。
    # 本数を基準にすることで太さの見た目を揃え、表示上のラベルは実際に
    # その時間足で表示されている期間に合わせる。以前あった「表示期間・
    # 表示幅は時間足を切り替えても値を変えない」という制約は、値の実体を
    # 文字列ラベルから本数に変えたことで、ラベル表示のほうが時間足ごとに
    # 変わる形に変更した）
    width_pref_key = f"chart_display_width_bar_target_{key_prefix}"
    default_bar_target = _width_label_to_bar_count(
        CHART_DISPLAY_WIDTH_DEFAULT, "daily"
    )
    bar_target = st.session_state.get(width_pref_key, default_bar_target)
    suggested_width_label = _closest_width_label_for_bar_count(
        bar_target, chart_timeframe
    )
    with width_col:
        display_width_label = st.selectbox(
            "チャート表示幅",
            options=CHART_DISPLAY_WIDTH_OPTIONS,
            index=CHART_DISPLAY_WIDTH_OPTIONS.index(suggested_width_label),
            key=f"chart_display_width_select_{key_prefix}_{chart_timeframe}",
        )
    st.session_state[width_pref_key] = _width_label_to_bar_count(
        display_width_label, chart_timeframe
    )

    # vertical_alignment="bottom"で、ラベル行が無いチェックボックスを
    # チェックボックス自体の高さに揃える。列幅比率は各チェックボックスの
    # ラベル文字数に応じて調整する。"10日線"・"20日線"・"60日線"（数字2桁）・
    # "出来高"（漢字3文字）は"3日線"等（数字1桁）より横幅が必要で、
    # 同じ比率のままだと折り返してラベルが2行になってしまうため、
    # 他より広めの比率を割り当てる。"100日線"（数字3桁）はさらに幅が必要
    (
        cb_candle, cb_sma3, cb_sma5, cb_sma7, cb_sma10,
        cb_sma20, cb_sma60, cb_sma100, cb_volume, cb_hover, _cb_spacer,
    ) = (
        st.columns(
            [1.4, 0.9, 0.9, 0.9, 1.2, 1.2, 1.2, 1.4, 1.1, 1.3, 2.5],
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
    with cb_sma100:
        show_sma100 = _persistent_checkbox("100日線", "chart_pref_show_sma100", key_prefix)
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
            ("sma100", show_sma100),
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
    # y_range/volume_rangeは実際の表示対象バー（window_start_date〜
    # window_end_date）だけから算出したいのでcompute_visible_window()には
    # 渡さず、表示用のx_rangeにのみ余白を足す（_compute_bar_edge_padding参照）
    bar_edge_padding = _compute_bar_edge_padding(chart_df_in_period["date"])
    x_range = [
        x_range[0] - bar_edge_padding,
        x_range[1] + bar_edge_padding,
    ]

    # スマホでは画面幅に対してデフォルトの高さ（680px/500px）だと縦長すぎて
    # 見づらいため、6割程度に縮める（_is_mobile_viewport参照）
    chart_height = None
    if _is_mobile_viewport():
        chart_height = round((680 if show_volume else 500) * 0.6)

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
            height=chart_height,
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
        width="stretch",
        config=PLOTLY_CONFIG,
        key=f"price_chart_{key_prefix}_{code}",
    )
    st.iframe(
        build_scroll_sync_script(
            chart_df_in_period["date"],
            chart_df_in_period["high"],
            chart_df_in_period["low"],
            chart_df_in_period["volume"],
            visible_bar_count,
            start_offset,
            storage_key=f"{key_prefix}:{code}",
            # 表示位置の復元は「表示期間・表示幅を自分では変えていない
            # 再描画」（MAチェックボックス切替・日足/週足/月足の変更など）
            # だけに適用したい。view_signatureが前回保存時と違えば、
            # ユーザーが表示期間/表示幅を明示的に変更したとみなし、
            # 復元をスキップしてPython側の新しい既定表示をそのまま使う
            view_signature=f"{period_label}:{display_width_label}",
        ),
        # トラック自体は細い（14px）が、ドラッグ中に多少上下にぶれても
        # このiframe自身の高さの範囲内であればmousemoveを取りこぼさない
        # ため、少し余裕を持たせた高さにする（2026-08-30改訂:
        # st.components.v1.html()は非推奨のためst.iframe()に変更）
        height=32,
    )


# CREATE TABLE IF NOT EXISTS・列追加マイグレーションとも冪等なため、
# 起動のたびに呼んでも問題ない
create_trades_table()
create_watchlist_table()

st.set_page_config(
    page_title="株探し",
    page_icon=str(Path(__file__).resolve().parent / "static" / "favicon-32.png"),
    layout="wide",
)
st.markdown(PLOTLY_CURSOR_OVERRIDE_CSS, unsafe_allow_html=True)

# スマホでブラウザの「ホーム画面に追加」をしたときのアイコンを独自の画像に
# するための設定。Streamlitはページの<head>を直接編集する手段を提供して
# いないため、st.iframe（同一オリジンアクセス可能なiframeとして埋め込む）
# 経由でwindow.parent.document.head（アプリ本体のhead）へlink/metaタグを
# 追加する。iOS Safariはapple-touch-icon、Android
# Chromeはmanifest.jsonのiconsをそれぞれ参照する。再実行のたびにこの
# st.iframe呼び出し自体は再実行されるため、二重追加を防ぐガード
# （querySelectorで既存チェック）を入れている
st.iframe(
    """
    <script>
    (function() {
        const doc = window.parent.document;
        const head = doc.head;

        function ensureLink(rel, href, attrs) {
            if (doc.querySelector(`link[rel="${rel}"]`)) return;
            const link = doc.createElement("link");
            link.rel = rel;
            link.href = href;
            if (attrs) {
                Object.keys(attrs).forEach(function(key) {
                    link.setAttribute(key, attrs[key]);
                });
            }
            head.appendChild(link);
        }

        ensureLink("apple-touch-icon", "/app/static/apple-touch-icon.png");
        ensureLink("manifest", "/app/static/manifest.json");
        ensureLink(
            "icon", "/app/static/favicon-32.png",
            {type: "image/png", sizes: "32x32"}
        );

        if (!doc.querySelector('meta[name="theme-color"]')) {
            const meta = doc.createElement("meta");
            meta.name = "theme-color";
            meta.content = "#0e1117";
            head.appendChild(meta);
        }
    })();
    </script>
    """,
    height=1,
)

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
        options=["daily", "weekly", "monthly"],
        format_func=lambda t: TIMEFRAME_LABELS[t],
    )

    universe_labels = st.multiselect(
        "採用指数（対象銘柄の絞り込み、複数選択可）",
        options=list(UNIVERSE_OPTIONS.keys()),
        default=["日経225", "JPX日経400"],
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

    ma_mode = "full_100"
    if "ma_order" in modules:
        ma_mode_label = st.radio(
            "並び順のバリエーション",
            options=list(MA_MODE_LABELS.values()),
            index=list(MA_MODE_LABELS.keys()).index("full_100"),
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

    run_button = st.button("銘柄検索を開始", type="primary", width="stretch")

# 個別銘柄検索の判定は、どのタブが表示中でも使えるようタブの外で評価しておく。
# 判断基準（modules）が未選択でも検索・チャート確認自体はできるようにする
# （evaluate_single_stockが空リストならno_modules_selected扱いで返す）
lookup_result = None

if selected_code:
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
elif run_button:
    universe_display = "・".join(universe_labels)

    with st.spinner(f"{universe_display}をスキャン中..."):
        scan_stocks = _combine_universes(universe_labels)

        # 候補一覧・監視銘柄候補（entry_signal_spec.md 6章「反発の手前」・
        # 14章「MA60/100接近」をまとめた1つのリスト）を1回の全銘柄スキャンで
        # まとめて取得する（個別に呼ぶと全銘柄スキャンが2回走ってしまうため）。
        # 監視銘柄候補は"bounce"（反発）・"ma_cross_watch"（MA60/100接近）の
        # どちらも選択していない限り常に空リストになる
        scan_results = get_today_scan_results(
            direction=direction,
            timeframe=timeframe,
            stocks=scan_stocks,
            modules=modules,
            ma_mode=ma_mode,
            min_volume=min_volume,
            min_price=min_price,
            max_price=max_price,
            min_market_cap=min_market_cap,
        )
        st.session_state["candidates"] = scan_results["candidates"]
        st.session_state["watch_candidates"] = scan_results["watchlist"]
        st.session_state["scan_used_modules"] = bool(modules)

        st.session_state["direction"] = direction
        st.session_state["timeframe"] = timeframe
        st.session_state["universe_label"] = universe_display

        # 新しいスキャン結果が出たら、検索/前回選択していた銘柄のチャートは消し、
        # 候補一覧を表示する（候補一覧のkeyも変えて選択状態をリセットする）
        st.session_state["focus_mode"] = None
        st.session_state["focus_candidate"] = None
        st.session_state["scan_version"] = st.session_state.get("scan_version", 0) + 1
        st.session_state["scroll_to_page_top"] = True

        # 売買銘柄・監視銘柄タブを見ている状態で「銘柄検索を開始」を押した場合も、
        # 結果を確認できるようスキャンタブに戻す（active_tabはst.tabs()の
        # key。on_change="rerun"を指定しているため、ここで書き換えた値が
        # 次の描画に反映される）
        st.session_state["active_tab"] = "スキャン"

candidates = st.session_state.get("candidates")
watch_candidates = st.session_state.get("watch_candidates")

# scroll_to_page_topは直前の「銘柄検索を開始」処理（同じスクリプト実行の中、
# st.rerun()を挟まずここまで来ている）で立てられる。st.tabs()より前だが
# scroll_to_page_topが立ってから呼ぶ必要があるため、この位置で呼ぶ
# （呼び出し自体はスクロール不要な場合も含め毎回同じ形で行う。理由は
# _render_scroll_trigger()のdocstring参照。フラグの消費はここで1回だけ行い、
# 以降は同じ値をタブごとの表の直後にも渡して重ねて呼ぶ）
SCROLL_TO_CHART, SCROLL_TO_PAGE_TOP = _consume_scroll_flags()
_render_scroll_trigger(SCROLL_TO_CHART, SCROLL_TO_PAGE_TOP)

tab_scan, tab_trades, tab_watchlist = st.tabs(
    ["スキャン", "売買銘柄", "監視銘柄"],
    # key・on_change="rerun"を指定することで、st.session_state["active_tab"]を
    # 読み書きできるようにする（「銘柄検索を開始」クリック時にスキャンタブへ戻す用途）。
    # 以前はこれが原因でタブ・見出しの二重表示を起こしたが、原因は
    # このスクロールトリガーの呼び出しがst.tabs()より前で不安定に
    # 出現/消失していたこと（st.tabs自体の問題ではなかった）と判明したため、
    # そちらを安定化したうえで再度有効にしている
    key="active_tab",
    on_change="rerun",
)

with tab_scan:
    scan_used_modules = st.session_state.get("scan_used_modules", True)

    if scan_used_modules:
        st.caption("今日の買い候補一覧")
    else:
        st.caption("銘柄一覧（判断基準が未選択のため、出来高・株価フィルタのみ適用）")

    # チャート・判定結果の表示位置は候補一覧より上のまま固定する。
    # 検索 or 候補一覧からの選択、どちらで内容を決めるかは候補一覧を
    # 描画した後（選択イベントを受け取った後）に確定するため、
    # 表示位置だけ先に確保しておいて後から中身を描画する
    focus_slot = st.container()

    if candidates is None:
        st.info("サイドバーの「銘柄検索を開始」を押してください。")
    elif not candidates:
        if scan_used_modules:
            st.warning("本日の候補はありません。")
        else:
            st.warning("条件に合う銘柄がありません。")
    else:
        st.markdown(
            '<span style="color: #FFC107; font-size: 0.9rem;">エントリー候補</span>',
            unsafe_allow_html=True,
        )

        rows = [
            {"順位": rank, **_candidate_row(candidate)}
            for rank, candidate in enumerate(candidates, start=1)
        ]

        # scan_versionをkeyに含めることで、新しいスキャンのたびに
        # 選択状態がリセットされた新しい表として扱われる。selection_versionも
        # 含めることで、もう一方の表（監視銘柄候補）で行を選択した際に、
        # こちらの表だけ新しいwidgetとして選択状態をリセットできるようにする
        # （_on_watch_candidate_table_select参照。2つの表を跨いで同時に
        # チェックが入ったままにならないようにするため）
        table_key = (
            f"candidates_table_{st.session_state.get('scan_version', 0)}"
            f"_{st.session_state.get('candidates_selection_version', 0)}"
        )

        # 既に監視銘柄として登録済みの行はグレー表示・選択不可にする
        # （_style_already_watchlisted_rows・_on_candidate_table_select参照）
        st.dataframe(
            _style_already_watchlisted_rows(pd.DataFrame(rows), candidates),
            width="stretch",
            hide_index=True,
            on_select=lambda: _on_candidate_table_select(table_key, candidates),
            selection_mode="single-row",
            key=table_key,
        )

        timeframe_label = TIMEFRAME_LABELS[st.session_state["timeframe"]]
        st.caption(
            f"{len(candidates)}件の候補"
            f"（{st.session_state['direction']} / {timeframe_label} / "
            f"{st.session_state['universe_label']}） "
            "行をクリックするとチャートを表示します。"
            "グレー表示の行は既に監視銘柄に登録済みです（選択してチャートは確認できます）。"
        )

    # 反発（entry_signal_spec.md 6章）・MA60/100接近ウォッチ（14章）・並び順
    # ウォッチ（15章）は判定ロジックこそ別物だが、どれも「エントリー候補には
    # まだ届かないが監視する価値がある状態」という位置づけは同じなため、
    # 1つの表にまとめて表示する（2026-08-22改訂で反発・MA60/100接近を統合、
    # 2026-08-23改訂で並び順を追加）。watch_candidates自体は
    # service.screening_service._is_merged_watch_candidate()で、選択中の
    # 監視系モジュールをすべて満たす銘柄だけに絞り込み済み（AND結合）
    if watch_candidates:
        st.divider()
        st.caption("監視銘柄候補")

        watch_rows = [
            {"順位": rank, **_watch_candidate_row(candidate)}
            for rank, candidate in enumerate(watch_candidates, start=1)
        ]

        # candidates_tableと同様、scan_version・selection_versionをkeyに含めて
        # 選択状態をリセットする（selection_versionは候補一覧側で行を選択した際に
        # インクリメントされ、こちらの表の選択状態だけをクリアする）
        watch_table_key = (
            f"watch_candidates_table_{st.session_state.get('scan_version', 0)}"
            f"_{st.session_state.get('watch_selection_version', 0)}"
        )

        # 既に監視銘柄として登録済みの行はグレー表示・選択不可にする
        # （_style_already_watchlisted_rows・_on_watch_candidate_table_select参照）
        st.dataframe(
            _style_already_watchlisted_rows(pd.DataFrame(watch_rows), watch_candidates),
            width="stretch",
            hide_index=True,
            on_select=lambda: _on_watch_candidate_table_select(watch_table_key, watch_candidates),
            selection_mode="single-row",
            key=watch_table_key,
        )

        st.caption(
            f"{len(watch_candidates)}件の監視銘柄候補。行をクリックするとチャートを表示します。"
            "グレー表示の行は既に監視銘柄に登録済みです（選択してチャートは確認できます）。"
        )
    elif candidates is not None and (
        "bounce" in modules or "ma_cross_watch" in modules or "ma_order" in modules
    ):
        st.divider()
        st.caption("監視銘柄候補: 該当銘柄はありません。")

    # 候補一覧・監視銘柄候補一覧の表のすぐ下でも同じスクロール処理を重ねて
    # 呼ぶ（_render_scroll_trigger()のdocstring参照。表の下の方の行を選択した
    # 場合、この位置はユーザーの現在のスクロール位置に近く、ページ最上部の
    # 呼び出しだけでは実行されないことがあるため）
    _render_scroll_trigger(SCROLL_TO_CHART, SCROLL_TO_PAGE_TOP)

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
                # チャート表示の時間足はサイドバーの「時間足」に一本化する
                # （スキャン実行時点の時間足に固定していた従来の挙動をやめる）
                chart_timeframe=timeframe,
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
        # 2026-08-30改訂: 「監視銘柄として追加」を「売買銘柄として追加」より
        # 上に表示する順に変更したため、見出しの表記順もそれに合わせた
        # （以前は「売買銘柄・監視銘柄に追加」）
        st.subheader("監視銘柄・売買銘柄")

        add_label = f"{add_candidate['code']} {add_candidate['company_name']}"
        st.caption(f"追加対象: {add_label}（上に表示中のチャートと同じ銘柄）")

        add_timeframe_label = TIMEFRAME_LABELS[add_candidate["timeframe"]]

        st.write("監視銘柄として追加")
        st.caption(
            f"方向: {DIRECTION_LABELS[add_candidate['direction']]}　"
            f"時間足: {add_timeframe_label}"
        )

        # st.columns(2)だと半分幅ずつ確保されボタン間に大きな隙間ができる
        # ため、内容幅のアイテムを詰めて並べられるst.container(horizontal=True)
        # を使う（2026-08-30改訂）
        with st.container(horizontal=True, gap="small"):
            add_to_priority_watchlist_clicked = st.button("優先監視銘柄に追加")
            add_to_watchlist_clicked = st.button("監視銘柄に追加")

        if add_to_watchlist_clicked or add_to_priority_watchlist_clicked:
            is_priority = add_to_priority_watchlist_clicked
            watchlist_kind_label = "優先監視銘柄" if is_priority else "監視銘柄"

            # 既に保有中（未決済）の銘柄は、売買銘柄と監視銘柄の二重登録に
            # なるため追加しない
            if has_open_trade(add_candidate["code"]):
                st.error(
                    f"{add_label} は既に保有中（未決済）の売買銘柄として"
                    f"登録されているため、{watchlist_kind_label}には追加できません"
                )
            elif not add_watchlist_stock(
                code=add_candidate["code"],
                company_name=add_candidate["company_name"],
                direction=add_candidate["direction"],
                timeframe=add_candidate["timeframe"],
                added_date=str(date.today()),
                priority=is_priority,
            ):
                st.warning(
                    f"{add_label} は既に監視銘柄（{add_timeframe_label}）に"
                    "登録済みです"
                )
            else:
                st.success(
                    f"{add_label} を{watchlist_kind_label}"
                    f"（{add_timeframe_label}）に追加しました"
                )

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
                "決算株価（利確/損切。未決済なら0のまま）",
                min_value=0.0,
                value=0.0,
            )
            exit_date_input = st.date_input(
                "決済日（決算株価を入力した場合のみ）", value=date.today()
            )
            is_nisa_input = st.checkbox("NISA枠（非課税）")

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
                    is_nisa=is_nisa_input,
                    exit_date=(
                        str(exit_date_input) if exit_price_input > 0 else None
                    ),
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
    elif candidates or (lookup_result is not None and "error" not in lookup_result):
        st.divider()
        st.info(
            "候補一覧の行を選択するか、個別銘柄検索で銘柄を選ぶと、"
            "チャートを確認したうえで売買銘柄・監視銘柄に追加できます。"
        )


def _style_negative_pnl_red(df):

    """
    「損益」列がマイナスの行を、行全体を赤字にして表示する

    st.data_editor()にpandas Styler経由で渡すと、Styler由来の見た目は
    編集不可（disabled）の列にのみ適用される（st.data_editorの仕様）。
    行全体を漏れなく赤字にするため、_render_trade_table側で決算済みの
    行は全列disabled指定にしている（read_only=True。2026-08-26改訂。
    以前は一部列のみ赤字になっていた）

    Styler経由だと、column_configで書式を指定していない数値列
    （購入株価・株数・損益等）がst.data_editorの既定フォーマットを
    通らず末尾に「.000000」等が付いてしまうため、明示的にフォーマットし
    直す（末尾の0を落としつつ、実用上十分な精度は保つ。決算株価は
    column_config.NumberColumnが優先されるためここでの指定と競合しない）
    """

    def _style_row(row):
        if pd.notna(row["損益"]) and row["損益"] < 0:
            return ["color: #d32f2f"] * len(row)
        return [""] * len(row)

    numeric_columns = df.select_dtypes(include="number").columns

    return (
        df.style
        .apply(_style_row, axis=1)
        .format({column: "{:.10g}" for column in numeric_columns})
    )


def _render_trade_table(trades_subset, key_suffix, read_only=False):

    """
    トレード一覧を1つのdata_editorで描画する（保有中セクション・決算済み
    セクションの年月ごとの表、両方から呼ぶ共通処理）

    「表示」チェックボックスによるチャート選択、行内編集（決算株価を
    含む）の保存とその後のst.rerun()をここで行う。決算株価を空欄から
    値ありへ（またはその逆へ）編集すると、次の再実行時にexit_priceの
    有無で保有中/決算済みのどちらに振り分けるかが変わり、結果的に
    そちらのセクションへ表示が移動する

    read_only=True（決算済みセクションで使用、2026-08-26追加）の場合、
    「表示」「NISA」「決済日」以外の列を編集不可にする。損益がマイナスの
    行を行全体赤字にするための制約（st.data_editorはStyler由来の見た目を
    編集不可の列にのみ適用する）で、プラスの決算済み取引も含め対象にする。
    決算済みの取引の取引日・価格・株数・時間足を修正したい場合は、いったん
    「保有中に移動」してから保有中セクション（read_only=False）で編集する。
    NISA区分・決済日だけは決算済みでも直接編集できる（税区分の後からの
    修正や、決済日が未記録の既存トレードへの後入力がよくあるため）
    """

    current_focus_id = st.session_state.get("trades_chart_focus_id")

    display_df = pd.DataFrame(
        [
            {
                "表示": trade["id"] == current_focus_id,
                "コード": trade["code"],
                "銘柄名": trade["company_name"],
                "方向": DIRECTION_LABELS[trade["direction"]],
                "NISA": bool(trade.get("is_nisa", False)),
                "時間足": TIMEFRAME_LABELS[trade["timeframe"]],
                "取引日": date.fromisoformat(trade["trade_date"]),
                "決済日": (
                    date.fromisoformat(trade["exit_date"])
                    if trade.get("exit_date") else None
                ),
                "購入株価": trade["entry_price"],
                "決算株価": trade["exit_price"],
                "株数": trade["quantity"],
                "損益": calculate_pnl(trade),
            }
            for trade in trades_subset
        ],
        index=[trade["id"] for trade in trades_subset],
    )

    # DateColumnの入力UI（カレンダーピッカー）を確実に出すため、object dtype
    # （date/Noneの混在）ではなくdatetime64に明示変換する。変換しないと
    # 一部環境でテキスト直接入力扱いになりカレンダーが出ないことがある
    display_df["取引日"] = pd.to_datetime(display_df["取引日"])
    display_df["決済日"] = pd.to_datetime(display_df["決済日"])

    disabled_columns = ["コード", "銘柄名", "方向", "損益"]
    if read_only:
        # 決算済みの取引は（NISA区分・決済日を除き）編集不可にする。損益が
        # マイナスの行を行全体赤字にするための制約（st.data_editorはStyler
        # 由来の見た目を編集不可の列にのみ適用する）で、勝ちトレードも含め
        # 決算済み全体を対象にする。修正が必要な場合は「保有中に移動」してから
        # 編集する
        disabled_columns += ["時間足", "取引日", "購入株価", "決算株価", "株数"]

    edited_df = st.data_editor(
        _style_negative_pnl_red(display_df),
        # keyにcurrent_focus_idを含める: 選択が変わるたびにウィジェットを
        # 新規生成させ、st.data_editorが「表示」列の過去の編集状態を
        # 引きずって選択が正しく切り替わらない（チェックが更新されず
        # 再実行が終わらない）事象を避ける
        key=f"trade_editor_{key_suffix}_{current_focus_id}",
        width="stretch",
        disabled=disabled_columns,
        column_config={
            "表示": st.column_config.CheckboxColumn(
                help="チェックした銘柄のチャートを上に表示します", pinned=True
            ),
            "コード": st.column_config.Column(pinned=True),
            "銘柄名": st.column_config.Column(pinned=True),
            "NISA": st.column_config.CheckboxColumn(
                help="NISA口座での取引はチェック。個別の「損益」表示には"
                "影響しませんが、年間損益の合計課税でこのトレードを"
                "非課税として扱います"
            ),
            "取引日": st.column_config.DateColumn(
                format="YYYY-MM-DD",
                help="登録間違いの修正用。エントリーした日付を修正できます",
            ),
            "決算株価": st.column_config.NumberColumn(
                help="値を入れると決算済みとして扱われ、決算済みセクションへ移動します"
            ),
            "決済日": st.column_config.DateColumn(
                format="YYYY-MM-DD",
                help="決算株価を入力したときの決済日（受け渡し日）を入力できます",
            ),
            "時間足": st.column_config.SelectboxColumn(
                options=list(TIMEFRAME_LABELS.values()),
                help="日足/週足を間違えて登録した場合はここで修正できます",
            ),
            "損益": st.column_config.NumberColumn(
                help="税引前の金額です。譲渡益課税は個別のトレードではなく、"
                "年間損益・全期間の損益合計に対して年単位でまとめて"
                "計算しています"
            ),
        },
    )

    trade_ids = [trade["id"] for trade in trades_subset]
    newly_checked_ids = [
        trade_id for trade_id in trade_ids
        if bool(edited_df.loc[trade_id, "表示"]) and trade_id != current_focus_id
    ]

    if newly_checked_ids:
        st.session_state["trades_chart_focus_id"] = newly_checked_ids[0]
        st.session_state["scroll_to_chart"] = True
        st.rerun()
    elif (
        current_focus_id in trade_ids
        and not bool(edited_df.loc[current_focus_id, "表示"])
    ):
        st.session_state["trades_chart_focus_id"] = None
        st.rerun()

    for trade in trades_subset:
        row = edited_df.loc[trade["id"]]
        new_exit_price = (
            None if pd.isna(row["決算株価"]) else float(row["決算株価"])
        )
        new_timeframe = TIMEFRAME_LABELS_INVERSE[row["時間足"]]
        # 取引日は必須項目のため、空欄にされた場合は元の値を保持する
        new_trade_date = (
            trade["trade_date"] if pd.isna(row["取引日"])
            else pd.Timestamp(row["取引日"]).strftime("%Y-%m-%d")
        )
        new_exit_date = (
            None if pd.isna(row["決済日"])
            else pd.Timestamp(row["決済日"]).strftime("%Y-%m-%d")
        )
        new_is_nisa = bool(row["NISA"])

        if (
            row["購入株価"] != trade["entry_price"]
            or new_exit_price != trade["exit_price"]
            or row["株数"] != trade["quantity"]
            or new_timeframe != trade["timeframe"]
            or new_trade_date != trade["trade_date"]
            or new_exit_date != trade.get("exit_date")
            or new_is_nisa != trade.get("is_nisa", False)
        ):
            update_trade(
                trade["id"],
                entry_price=float(row["購入株価"]),
                exit_price=new_exit_price,
                quantity=int(row["株数"]),
                timeframe=new_timeframe,
                trade_date=new_trade_date,
                is_nisa=new_is_nisa,
                exit_date=new_exit_date,
            )
            st.rerun()


def _render_trades_section():

    """
    売買銘柄タブを描画する

    保有中（決算株価が未入力）・決算済み（決算株価入力済み）を別セクション
    に分ける。決算済みセクションはこれまで通り年→月でグルーピングし、
    月間・年間損益を表示する（未決済トレードは損益集計に含まれないため、
    保有中セクションには損益の合計表示は無い）。日足・週足は分けず
    1つの表にまとめ、「時間足」列で見分ける

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

    open_trades = [trade for trade in trades if trade["exit_price"] is None]
    closed_trades = [trade for trade in trades if trade["exit_price"] is not None]

    st.markdown("#### 保有中")
    # ロングとショートを同じ表に混在させず、別々の表に分けて表示する
    # （2026-08-30改訂）
    open_long_trades = [t for t in open_trades if t["direction"] == "long"]
    open_short_trades = [t for t in open_trades if t["direction"] == "short"]

    st.markdown("##### ロング")
    if open_long_trades:
        _render_trade_table(open_long_trades, key_suffix="open_long")
        st.caption(f"{len(open_long_trades)}件の保有銘柄（ロング）")
    else:
        st.caption("現在保有中のロング銘柄はありません。")

    st.markdown("##### ショート")
    if open_short_trades:
        _render_trade_table(open_short_trades, key_suffix="open_short")
        st.caption(f"{len(open_short_trades)}件の保有銘柄（ショート）")
    else:
        st.caption("現在保有中のショート銘柄はありません。")

    st.markdown("#### 決算済み")
    if closed_trades:
        groups = group_by_year_and_month(closed_trades)

        for year_index, (year, year_pnl, month_groups) in enumerate(groups):
            with st.expander(
                f"{year}年（年間損益（税引後）: {year_pnl:+,.0f}円）",
                expanded=(year_index == 0),
            ):
                for month, month_pnl, month_trades in month_groups:
                    st.markdown(
                        f"**{month}月　月間損益（税引前）: {month_pnl:+,.0f}円**"
                    )
                    _render_trade_table(
                        month_trades, key_suffix=f"{year}_{month}", read_only=True
                    )
        st.caption(f"{len(closed_trades)}件の決算済み銘柄")
    else:
        st.caption("決算済みの銘柄はまだありません。")

    # 表のすぐ下でも同じスクロール処理を重ねて呼ぶ（_render_scroll_trigger()の
    # docstring参照。決算済みの月が多く表が長い場合、下の方の行を選択すると
    # ページ最上部の呼び出しだけでは実行されないことがあるため）
    _render_scroll_trigger(SCROLL_TO_CHART, SCROLL_TO_PAGE_TOP)

    focus_id = st.session_state.get("trades_chart_focus_id")
    focus_trade = next((t for t in trades if t["id"] == focus_id), None)

    with focus_slot:
        if focus_trade is not None:
            st.markdown(f"##### {focus_trade['code']} {focus_trade['company_name']}")
            # チャート表示の時間足はサイドバーの「時間足」に一本化する
            # （表内の「時間足」列は登録データそのものの修正用で別物）
            _render_chart_block(focus_trade["code"], timeframe, key_prefix="trades")
            st.divider()
        else:
            st.info(
                "表の「表示」列にチェックを入れると、その銘柄のチャートを"
                "ここに表示します。"
            )
            st.divider()

    st.metric("全期間の損益合計（税引後）", f"{total_pnl(trades):+,.0f}円")

    st.divider()

    if focus_trade is None:
        st.info(
            "削除・監視銘柄への移動を行うには、表の「表示」列で対象の"
            "銘柄にチェックを入れてください。"
        )
        return

    is_closed = focus_trade["exit_price"] is not None

    # 決算済みの取引は、確定した損益の記録を誤って消してしまわないよう
    # 削除ボタンを出さない。「保有中に移動」（決算株価をクリアするだけ）で
    # 誤って決算済みにしてしまった場合の修正ができるため、削除しか手段が
    # ないわけではない
    if is_closed:
        if st.button(
            "選択した取引を保有中に移動",
            key="move_to_open_trade_button",
            help="決算株価の入力を誤った場合の修正用。決算株価と決済日を"
            "クリアし、保有中に戻します",
        ):
            update_trade(
                focus_trade["id"],
                entry_price=focus_trade["entry_price"],
                exit_price=None,
                quantity=focus_trade["quantity"],
                timeframe=focus_trade["timeframe"],
                trade_date=focus_trade["trade_date"],
                is_nisa=focus_trade.get("is_nisa", False),
                exit_date=None,
            )
            st.session_state["trades_chart_focus_id"] = None
            st.rerun()
        return

    col_delete, col_move = st.columns(2)

    with col_delete:
        # 削除は取り消せない操作のため、他のボタンと区別しやすいよう
        # 文字色を赤くする（_style_delete_buttons_red()参照。
        # 2026-08-30追加）
        if st.button(
            "選択した取引を削除",
            key="delete_trade_button",
        ):
            delete_trade(focus_trade["id"])
            st.session_state["trades_chart_focus_id"] = None
            st.rerun()
        _style_delete_buttons_red()

    with col_move:
        if st.button(
            "選択した取引を監視銘柄に移動",
            key="move_trade_button",
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
            # 移動元の売買銘柄は、既に同じ監視銘柄が登録済みでスキップされた
            # 場合でも常に削除する（「監視銘柄に戻す」操作の意図を優先する）
            delete_trade(focus_trade["id"])
            st.session_state["trades_chart_focus_id"] = None
            st.rerun()


def _render_watchlist_table(stocks_subset, key_suffix):

    """
    監視銘柄一覧を1つのdata_editorで描画する（優先監視銘柄セクション・
    監視銘柄セクション、両方から呼ぶ共通処理）

    「表示」チェックボックスによるチャート選択、時間足の編集をここで行う。
    session_state["watchlist_chart_focus_id"]はタブ全体で1つだけなので、
    どちらのセクションで選択してもチャートは1箇所（focus_slot）に表示される
    """

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
            for w in stocks_subset
        ],
        index=[w["id"] for w in stocks_subset],
    )

    edited_watchlist_df = st.data_editor(
        watchlist_display_df,
        # keyにcurrent_focus_idを含める理由は_render_trade_tableのコメント参照
        key=f"watchlist_editor_{key_suffix}_{current_focus_id}",
        width="stretch",
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

    subset_ids = [w["id"] for w in stocks_subset]
    newly_checked_ids = [
        wid for wid in subset_ids
        if bool(edited_watchlist_df.loc[wid, "表示"]) and wid != current_focus_id
    ]

    if newly_checked_ids:
        st.session_state["watchlist_chart_focus_id"] = newly_checked_ids[0]
        st.session_state["scroll_to_chart"] = True
        st.rerun()
    elif (
        current_focus_id in subset_ids
        and not bool(edited_watchlist_df.loc[current_focus_id, "表示"])
    ):
        st.session_state["watchlist_chart_focus_id"] = None
        st.rerun()

    for stock in stocks_subset:
        new_timeframe = TIMEFRAME_LABELS_INVERSE[
            edited_watchlist_df.loc[stock["id"], "時間足"]
        ]

        if new_timeframe != stock["timeframe"]:
            update_watchlist_timeframe(stock["id"], new_timeframe)
            st.rerun()


def _render_watchlist_section():

    """
    監視銘柄タブを描画する（_render_trades_sectionと同様、日足/週足は
    「時間足」列で見分けるだけで表・削除・移動は一括で扱う）。

    優先監視銘柄・監視銘柄の2セクションに分けて表示する（優先監視銘柄が
    上）。振り分けは監視銘柄タブに追加した後、選択した銘柄を対象に
    ボタンで行う（どちらからどちらへも移動可能）

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

    priority_stocks = [w for w in watchlist_stocks if w["priority"]]
    normal_stocks = [w for w in watchlist_stocks if not w["priority"]]

    # ロングとショートを同じ表に混在させず、別々の表に分けて表示する
    # （2026-08-30改訂）
    priority_long_stocks = [w for w in priority_stocks if w["direction"] == "long"]
    priority_short_stocks = [w for w in priority_stocks if w["direction"] == "short"]
    normal_long_stocks = [w for w in normal_stocks if w["direction"] == "long"]
    normal_short_stocks = [w for w in normal_stocks if w["direction"] == "short"]

    st.markdown("#### 優先監視銘柄")

    st.markdown("##### ロング")
    if priority_long_stocks:
        _render_watchlist_table(priority_long_stocks, key_suffix="priority_long")
        st.caption(f"{len(priority_long_stocks)}件の優先監視銘柄（ロング）")
    else:
        st.caption("優先監視銘柄（ロング）はまだありません。")

    st.markdown("##### ショート")
    if priority_short_stocks:
        _render_watchlist_table(priority_short_stocks, key_suffix="priority_short")
        st.caption(f"{len(priority_short_stocks)}件の優先監視銘柄（ショート）")
    else:
        st.caption("優先監視銘柄（ショート）はまだありません。")

    st.markdown("#### 監視銘柄")

    st.markdown("##### ロング")
    if normal_long_stocks:
        _render_watchlist_table(normal_long_stocks, key_suffix="normal_long")
        st.caption(f"{len(normal_long_stocks)}件の監視銘柄（ロング）")
    else:
        st.caption("監視銘柄（ロング）はまだありません。")

    st.markdown("##### ショート")
    if normal_short_stocks:
        _render_watchlist_table(normal_short_stocks, key_suffix="normal_short")
        st.caption(f"{len(normal_short_stocks)}件の監視銘柄（ショート）")
    else:
        st.caption("監視銘柄（ショート）はまだありません。")

    # 表のすぐ下でも同じスクロール処理を重ねて呼ぶ（_render_scroll_trigger()の
    # docstring参照。銘柄数が多く表が長い場合、下の方の行を選択すると
    # ページ最上部の呼び出しだけでは実行されないことがあるため）
    _render_scroll_trigger(SCROLL_TO_CHART, SCROLL_TO_PAGE_TOP)

    focus_id = st.session_state.get("watchlist_chart_focus_id")
    focus_stock = next((w for w in watchlist_stocks if w["id"] == focus_id), None)

    with focus_slot:
        if focus_stock is not None:
            st.markdown(f"##### {focus_stock['code']} {focus_stock['company_name']}")
            # チャート表示の時間足はサイドバーの「時間足」に一本化する
            # （表内の「時間足」列は登録データそのものの修正用で別物）
            _render_chart_block(focus_stock["code"], timeframe, key_prefix="watchlist")
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

    # 優先振り分けボタンと削除ボタンは横に並べる（st.columns(2)だと
    # 半分幅ずつ確保されボタン間に大きな隙間ができるため、内容幅の
    # アイテムを詰めて並べられるst.container(horizontal=True)を使う。
    # 2026-08-30改訂: 以前は縦に並べていた）
    with st.container(horizontal=True, gap="small"):
        if focus_stock["priority"]:
            if st.button(
                "監視銘柄を優先から外す",
                key="toggle_watchlist_priority_button",
                help="優先監視銘柄から通常の監視銘柄に戻します",
            ):
                update_watchlist_priority(focus_stock["id"], False)
                st.rerun()
        else:
            if st.button(
                "監視銘柄を優先監視銘柄に追加",
                key="toggle_watchlist_priority_button",
                help="優先監視銘柄セクションに移動します",
            ):
                update_watchlist_priority(focus_stock["id"], True)
                st.rerun()

        # 削除は取り消せない操作のため、他のボタンと区別しやすいよう
        # 文字色を赤くする（_style_delete_buttons_red()参照。2026-08-30追加）
        if st.button("監視銘柄を削除", key="delete_watchlist_button"):
            delete_watchlist_stock(focus_stock["id"])
            st.session_state["watchlist_chart_focus_id"] = None
            st.rerun()
    _style_delete_buttons_red()

    st.markdown("##### 監視銘柄を売買銘柄に移動")

    with st.form("move_watchlist_to_trade_form"):
        move_trade_date_input = st.date_input("取引日", value=date.today())
        move_entry_price_input = st.number_input(
            "購入株価", min_value=0.0, value=0.0
        )
        move_quantity_input = st.number_input(
            "株数", min_value=1, value=100, step=100
        )
        move_exit_price_input = st.number_input(
            "決算株価（利確/損切。未決済なら0のまま）",
            min_value=0.0,
            value=0.0,
        )
        move_exit_date_input = st.date_input(
            "決済日（決算株価を入力した場合のみ）", value=date.today()
        )
        move_is_nisa_input = st.checkbox("NISA枠（非課税）")

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
                is_nisa=move_is_nisa_input,
                exit_date=(
                    str(move_exit_date_input) if move_exit_price_input > 0 else None
                ),
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
