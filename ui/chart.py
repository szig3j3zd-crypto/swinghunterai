import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 陽線（上昇）=赤、陰線（下落）=青。日本の株価チャートの慣例に合わせる
CANDLE_UP_COLOR = "#d1495b"
CANDLE_DOWN_COLOR = "#2e6f95"

# 出来高は陽線/陰線で色分けせず、全て同じ色にする
VOLUME_COLOR = "#e6b800"

# 短期・中期・長期の順で色を固定する（周期的に割り当てない）
MA_COLORS = {
    "sma3": "#8fd14f",
    "sma5": "#e6b800",
    "sma7": "#ff69b4",
    "sma10": "#9467bd",
    "sma20": "#d62728",
    "sma60": "#1f5fa8",
}
MA_LABELS = {
    "sma3": "3日線",
    "sma5": "5日線",
    "sma7": "7日線",
    "sma10": "10日線",
    "sma20": "20日線",
    "sma60": "60日線",
}
GRID_COLOR = "rgba(128, 128, 128, 0.18)"
Y_AXIS_PADDING_RATIO = 0.04

# モードバーのアイコン説明（ツールチップ）を日本語化する。
# 公式の日本語ロケールファイルを読み込む手段が無いため、
# 英語表記→日本語表記の対訳辞書をそのまま渡す
PLOTLY_JA_LOCALE = {
    "ja": {
        "dictionary": {
            "Download plot as a png": "PNG画像として保存",
            "Download plot as a PNG": "PNG画像として保存",
            "Download plot": "画像として保存",
            "Fullscreen": "全画面表示",
            "Zoom": "ズーム",
            "Pan": "パン（移動）",
            "Box Select": "矩形選択",
            "Lasso Select": "自由選択（投げ縄）",
            "Zoom in": "拡大",
            "Zoom out": "縮小",
            "Autoscale": "自動スケール",
            "Reset axes": "軸をリセット",
            "Toggle Spike Lines": "十字ラインの表示切替",
            "Show closest data on hover": "最も近いデータのみ表示",
            "Compare data on hover": "同じ位置のデータを比較表示",
            "Draw line": "直線を描画",
            "Draw open freeform": "フリーハンド線を描画",
            "Draw closed freeform": "フリーハンド図形を描画",
            "Draw circle": "円を描画",
            "Draw rectangle": "四角形を描画",
            "Erase active shape": "選択した図形を削除",
            "Reset": "リセット",
        },
        "format": {},
    },
}

# st.plotly_chart(..., config=PLOTLY_CONFIG) にそのまま渡す共通設定
PLOTLY_CONFIG = {
    "modeBarButtonsToAdd": ["drawline", "eraseshape"],
    "displaylogo": False,
    "locale": "ja",
    "locales": PLOTLY_JA_LOCALE,
}

# dragmode="zoom"のとき、Plotlyはチャート上のマウスカーソルを標準で十字（crosshair）
# に変える。矢印のままにしたいという要望のため、CSSでカーソル形状を上書きする。
# ドラッグでのズーム機能自体はdragmodeの設定のままなので変わらない。
# st.markdown(PLOTLY_CURSOR_OVERRIDE_CSS, unsafe_allow_html=True) をアプリ起動時に
# 一度呼び出せば、ページ内の全Plotlyチャートに適用される
PLOTLY_CURSOR_OVERRIDE_CSS = """
<style>
.js-plotly-plot .nsewdrag,
.js-plotly-plot .cursor-crosshair {
    cursor: default !important;
}
</style>
"""


def compute_visible_window(df, start_date, end_date):

    """
    指定期間内のデータから、価格・出来高の表示レンジ（余白付き）を計算する

    build_price_chart()のx_range/y_range/volume_rangeにそのまま渡す用

    Parameters
    ----------
    df
        date, high, low, volume 列を持つDataFrame

    start_date, end_date
        表示したい期間（この範囲外のデータでレンジを計算しない）

    Returns
    -------
    x_range, y_range, volume_range
        x_range: [start_date, end_date]
        y_range: [安値の最小*(1-余白), 高値の最大*(1+余白)]（対象データが無ければNone）
        volume_range: [0, 出来高の最大*(1+余白)]（対象データが無ければNone）
    """

    window = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

    if window.empty:
        return [start_date, end_date], None, None

    low_min = window["low"].min()
    high_max = window["high"].max()
    padding = (high_max - low_min) * Y_AXIS_PADDING_RATIO or high_max * 0.01

    y_range = [low_min - padding, high_max + padding]
    volume_range = [0, window["volume"].max() * (1 + Y_AXIS_PADDING_RATIO)]

    return [start_date, end_date], y_range, volume_range


def _compute_date_rangebreaks(df):

    """
    土日・祝日など、データが存在しない日をチャートのx軸から除外するための
    rangebreaksを計算する。株式市場の休業日カレンダーを別途持たなくても、
    df内の実際のデータ日を基準に「その間に存在するはずなのに無い日」を
    差分で求めれば同じ結果になる（週足の場合も同様に、実データの無い日が
    まとめて詰められるため、週足の点同士が均等な間隔で並ぶ）
    """

    existing_dates = pd.to_datetime(df["date"]).dt.normalize()
    all_days = pd.date_range(existing_dates.min(), existing_dates.max(), freq="D")
    missing_days = all_days.difference(existing_dates)

    return [dict(values=missing_days)]


def _format_or_dash(value, fmt):

    return format(value, fmt) if pd.notna(value) else "-"


def _build_hover_text(df, visible_ma, show_volume):

    """
    ローソク足トレース1本にまとめるホバー表示用テキストを行ごとに作る。
    高値・安値・始値・終値・（表示中の）移動平均線・出来高の順で日本語ラベルを付ける。
    移動平均線はチェックボックスで非表示にしているものはホバーにも出さない
    （画面に無い情報が出てくると混乱するため、表示状態と揃える）
    """

    lines = []
    for _, row in df.iterrows():
        parts = [
            row["date"].strftime("%Y/%m/%d"),
            f"高値: {row['high']:,.1f}",
            f"安値: {row['low']:,.1f}",
            f"始値: {row['open']:,.1f}",
            f"終値: {row['close']:,.1f}",
        ]
        for key in visible_ma:
            parts.append(f"{MA_LABELS[key]}: {_format_or_dash(row[key], ',.2f')}")
        if show_volume:
            parts.append(f"出来高: {row['volume']:,.0f}")
        lines.append("<br>".join(parts))

    return lines


def build_price_chart(df, show_candlestick=True, visible_ma=(), show_volume=True,
                       x_range=None, y_range=None, volume_range=None,
                       uirevision=None, show_hover_info=True,
                       tick_format="%Y/%m/%d"):

    """
    ローソク足・移動平均線・出来高のチャートを作る

    Parameters
    ----------
    df
        date, open, high, low, close, volume, sma3, sma5, sma7, sma10, sma20,
        sma60 列を持つDataFrame

    show_candlestick
        ローソク足を表示するか

    visible_ma
        表示する移動平均線のキー（"sma3", "sma5", "sma7", "sma10", "sma20",
        "sma60"）のタプル/リスト

    show_volume
        出来高サブプロットを表示するか

    x_range
        初期表示するx軸（日付）の範囲 [開始日, 終了日]。Noneなら全期間

    y_range
        初期表示する株価軸の範囲 [下限, 上限]。Noneなら自動

    volume_range
        初期表示する出来高軸の範囲 [下限, 上限]。Noneなら自動

    uirevision
        この値が前回描画時と同じなら、ユーザーが手動でズーム/パンした状態を
        維持する（表示期間・銘柄を変えたときだけ値を変えてリセットさせる）

    show_hover_info
        カーソルを合わせたときの株価・出来高の詳細情報ボックスを表示するか。
        Falseにするとホバー自体を無効化する（縦の点線もホバー起点のため
        同時に非表示になる）

    tick_format
        出来高チャート下の日付軸ラベルのd3-time-format文字列。表示期間が
        短い（日単位で見たい）場合は"%m/%d"、長い場合は"%Y/%m"など、
        呼び出し側（表示期間の選択）に応じて渡す

    Returns
    -------
    fig
        plotly.graph_objects.Figure
    """

    rows = 2 if show_volume else 1
    row_heights = [0.72, 0.28] if show_volume else [1.0]

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.03,
    )

    # ホバー表示は個々のトレースには持たせず、常に存在する透明な補助トレース
    # （下で追加）1本にまとめる。ローソク足の表示・非表示に関わらず
    # 高値・安値・始値・終値・移動平均線・出来高を一つのボックスで、
    # 日本語ラベル・指定した順序で表示するため
    if show_candlestick:
        fig.add_trace(
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color=CANDLE_UP_COLOR,
                decreasing_line_color=CANDLE_DOWN_COLOR,
                increasing_fillcolor=CANDLE_UP_COLOR,
                decreasing_fillcolor=CANDLE_DOWN_COLOR,
                name="株価",
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    for key in visible_ma:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df[key],
                mode="lines",
                line=dict(color=MA_COLORS[key], width=1.5),
                name=MA_LABELS[key],
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    if show_volume:
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                marker_color=VOLUME_COLOR,
                name="出来高",
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2,
            col=1,
        )

    # 高値・安値・始値・終値・（表示中の）移動平均線・出来高をひとつのボックスに
    # まとめてホバー表示するための透明な補助トレース。ローソク足の表示状態に
    # 関わらず常に追加する。row=1・row=2どちらにカーソルを合わせても同じ内容が
    # 出るよう、サブプロットごとに（別軸のため）同じ内容のトレースを重ねて置く
    hover_text = _build_hover_text(df, visible_ma, show_volume)
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["high"],
            mode="lines",
            line=dict(width=0),
            hovertext=hover_text,
            hovertemplate="%{hovertext}<extra></extra>",
            showlegend=False,
            name="",
        ),
        row=1,
        col=1,
    )
    if show_volume:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["volume"],
                mode="lines",
                line=dict(width=0),
                hovertext=hover_text,
                hovertemplate="%{hovertext}<extra></extra>",
                showlegend=False,
                name="",
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=760 if show_volume else 580,
        margin=dict(l=40, r=20, t=10, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        xaxis_rangeslider_visible=False,
        # チャート上のドラッグでも横スクロールできるよう、既定のドラッグ操作を
        # 矩形ズームではなくパン（横移動）にする。表示期間の範囲全体分の
        # データを常にトレースへ渡しているため、パン自体はブラウザ側で完結し
        # （Streamlitの再実行を伴わない）ため滑らかに動く。ズームしたい場合は
        # モードバーの「ズーム」アイコンで切り替えられる
        dragmode="pan",
        # "closest"はカーソルとの2次元（x・y）距離が最も近い点を拾うため、
        # カーソルがトレースの線から縦に離れた位置にあると、縦の点線
        # （spikesnap="cursor"でカーソルのx座標そのものに追従）とは
        # 別のx（たまたま2次元距離が近いだけの点）の情報を表示してしまう。
        # "x"はx座標のみで最も近い点を拾うため、点線の位置と表示内容が
        # 常に一致する
        hovermode="x" if show_hover_info else False,
        # 既定では隣接データ点までの距離（hoverdistance=20px）を超えると
        # 何も拾わなくなる。表示期間によっては点の間隔が20pxを超えることも
        # あるため、距離制限を外して常に最寄りのxのデータを拾えるようにする
        hoverdistance=-1,
        uirevision=uirevision,
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)

    # 土日・祝日など、データの無い日をx軸から除外し、ローソク足の間隔を
    # 詰めて連続して見えるようにする
    fig.update_xaxes(rangebreaks=_compute_date_rangebreaks(df))

    # 出来高チャート下の日付ラベル・ホバー表示の日付を日本式（年/月、月/日）に統一する。
    # 既定は"Mar 2026"のような英語表記になるため変更する。Plotly側の自動目盛間隔
    # （dtickrange）は狙った境界に一致しないことがあり不安定なため、呼び出し側
    # （選択された表示期間）から明示的に受け取ったtick_formatをそのまま使う
    fig.update_xaxes(tickformat=tick_format)
    fig.update_xaxes(hoverformat="%Y/%m/%d")

    # 縦の点線（スパイクライン）を出来高サブプロットまで伸ばす
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikedash="dot",
        spikethickness=1,
        spikecolor="rgba(100, 100, 100, 0.5)",
    )

    # shared_xaxesでも各サブプロットのrangeは個別に指定する必要があるため、
    # 全x軸（row指定なし）に同じrangeを適用する
    if x_range is not None:
        fig.update_xaxes(range=x_range)

    if y_range is not None:
        fig.update_yaxes(range=y_range, row=1, col=1)

    if show_volume and volume_range is not None:
        fig.update_yaxes(range=volume_range, row=2, col=1)

    # Plotly標準のレンジスライダー（一番下のサブプロットに、全期間分の
    # ミニチャート＋現在の表示範囲を示す枠を表示する）を付ける。枠を
    # ドラッグするとチャート本体と自動的に同期してスクロールする
    # （同じx軸を参照しているため、追加のJavaScriptなしでPlotly標準機能
    # だけで完結する）
    rangeslider_row = 2 if show_volume else 1
    fig.update_xaxes(rangeslider_visible=True, row=rangeslider_row, col=1)
    if show_volume:
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

    return fig


def build_scroll_sync_script(bar_dates, highs, lows, volumes,
                              visible_bar_count, initial_start_index):

    """
    左右矢印キーでのチャートスクロールと、表示範囲変更時の価格軸・出来高軸の
    自動フィットを行うJavaScriptを組み立てる

    st.components.v1.html(...)でst.plotly_chartの直後に埋め込む想定。
    横スクロール自体は、チャート上のマウスドラッグ（Plotly標準の
    dragmode="pan"）と、チャート下のPlotly標準レンジスライダー
    （build_price_chartのrangeslider_visible=True）のどちらもPlotly標準
    機能でチャート本体と自動的に同期するため、このscript側で同期を取る
    必要はない。このscriptが追加で行うのは次の2点

    - 左右矢印キーでのローソク足1本分ずつのスクロール（Streamlitの
      再実行を伴わず、ブラウザ側でPlotly.relayoutを直接呼ぶ）
    - 表示範囲が変わるたびに（ドラッグ・レンジスライダー・矢印キーの
      いずれが原因でも）、その範囲内の高値・安値・出来高から価格軸・
      出来高軸のレンジを自動で再フィットする
      （compute_visible_windowと同じ計算をブラウザ側で再現）

    Parameters
    ----------
    bar_dates
        表示期間内の全ローソク足の日付（date列、日付順）。矢印キーで
        何日分移動するかをこの実データから引くため、営業日以外
        （土日等）は自動的に読み飛ばされる

    highs, lows, volumes
        bar_datesと同じ並びの高値・安値・出来高。表示範囲変更時の
        価格軸・出来高軸の自動フィットに使う

    visible_bar_count
        チャート表示幅に相当する本数（表示するローソク足の本数）

    initial_start_index
        現在（Streamlitが最後に描画した時点）の表示窓の左端が、
        bar_dates の何番目か。矢印キーはここを起点に動かす

    Returns
    -------
    html
        st.components.v1.html()にそのまま渡せるHTML文字列
    """

    dates_json = json.dumps([str(d) for d in bar_dates])
    highs_json = json.dumps([float(v) for v in highs])
    lows_json = json.dumps([float(v) for v in lows])
    volumes_json = json.dumps([float(v) for v in volumes])

    return f"""
    <script>
    (function() {{
        // このscriptを埋め込んだiframe（window.frameElement）の直前にある
        // Plotlyチャートdivを探す。IDを直接指定できない（Streamlitが
        // 内部で採番するため）ので、DOM上の前後関係だけで判定する
        function findPlotDiv() {{
            const myFrame = window.frameElement;
            if (!myFrame) return null;
            const doc = window.parent.document;
            const plots = doc.querySelectorAll(".js-plotly-plot");
            let best = null;
            plots.forEach(function(p) {{
                const relToFrame = p.compareDocumentPosition(myFrame);
                const pIsBeforeFrame = (relToFrame & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
                if (!pIsBeforeFrame) return;
                if (!best) {{
                    best = p;
                    return;
                }}
                const relToBest = best.compareDocumentPosition(p);
                const pIsAfterBest = (relToBest & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
                if (pIsAfterBest) {{
                    best = p;
                }}
            }});
            return best;
        }}

        // barDatesの何番目が指定した時刻（ミリ秒）に最も近いかを二分探索で求める
        function lowerBound(sortedMs, targetMs) {{
            let lo = 0, hi = sortedMs.length;
            while (lo < hi) {{
                const mid = (lo + hi) >> 1;
                if (sortedMs[mid] < targetMs) {{
                    lo = mid + 1;
                }} else {{
                    hi = mid;
                }}
            }}
            return lo;
        }}

        function computeYRanges(scrollState, startIndex) {{
            const endIndex = Math.min(
                startIndex + scrollState.visibleBarCount - 1,
                scrollState.barDates.length - 1
            );
            let lowMin = Infinity;
            let highMax = -Infinity;
            let volMax = -Infinity;
            for (let i = startIndex; i <= endIndex; i++) {{
                if (scrollState.lows[i] < lowMin) lowMin = scrollState.lows[i];
                if (scrollState.highs[i] > highMax) highMax = scrollState.highs[i];
                if (scrollState.volumes[i] > volMax) volMax = scrollState.volumes[i];
            }}
            const padding = (highMax - lowMin) * 0.04 || highMax * 0.01;
            return {{
                yRange: [lowMin - padding, highMax + padding],
                volRange: [0, volMax * 1.04],
            }};
        }}

        function setup(gd) {{
            // スキャン/売買銘柄/監視銘柄タブが同時にチャートを表示している
            // ケースがあるため、本数・現在位置などの状態はグローバルではなく
            // 各チャートのdivに直接持たせ、チャート同士が干渉しないようにする
            const barDates = {dates_json};
            gd.__swingHunterScroll = {{
                barDates: barDates,
                barTimestamps: barDates.map(function(d) {{ return new Date(d).getTime(); }}),
                highs: {highs_json},
                lows: {lows_json},
                volumes: {volumes_json},
                visibleBarCount: {int(visible_bar_count)},
                startIndex: {int(initial_start_index)},
                maxStartIndex: Math.max(barDates.length - {int(visible_bar_count)}, 0),
            }};

            // マウスが乗っているチャートを「矢印キーの対象」として覚えておく
            function markActive() {{
                window.parent.__swingHunterActiveChart = gd;
            }}
            gd.addEventListener("mouseenter", markActive);
            if (gd.matches(":hover")) {{
                markActive();
            }}

            // マウスドラッグ（Plotly標準のdragmode="pan"）・レンジスライダー・
            // 矢印キーのいずれでx軸レンジが変わった場合も、Plotlyが発火する
            // plotly_relayoutイベントを起点に価格軸・出来高軸を再フィット
            // する。同じ関数から呼ぶ自分自身のy軸更新（Plotly.relayout）が
            // 再度plotly_relayoutを発火させても、そちらはxaxis側のキーを
            // 含まないため無限ループにはならない
            if (!gd.__swingHunterRelayoutBound) {{
                gd.__swingHunterRelayoutBound = true;
                gd.on("plotly_relayout", function(eventdata) {{
                    const xChanged = Object.keys(eventdata).some(function(k) {{
                        return k.indexOf("xaxis.range") === 0;
                    }});
                    if (!xChanged) return;

                    const scrollState = gd.__swingHunterScroll;
                    if (!scrollState) return;
                    const curRange = gd._fullLayout && gd._fullLayout.xaxis
                        ? gd._fullLayout.xaxis.range : null;
                    if (!curRange) return;

                    const startMs = new Date(curRange[0]).getTime();
                    let startIndex = lowerBound(scrollState.barTimestamps, startMs);
                    startIndex = Math.max(0, Math.min(startIndex, scrollState.maxStartIndex));
                    scrollState.startIndex = startIndex;

                    const ranges = computeYRanges(scrollState, startIndex);
                    window.parent.Plotly.relayout(gd, {{
                        "yaxis.range": ranges.yRange,
                        "yaxis2.range": ranges.volRange,
                    }});
                }});
            }}

            // 矢印キーのリスナーは常にこのチャート（この再描画）の分だけを
            // 残す。「一度だけ登録して使い回す」実装だと、以前のリスナーは
            // その時のcomponents.html用iframe（DOMから削除されると実行
            // コンテキストごと破棄される）内で作られたクロージャのままに
            // なり、次の再描画でそのiframeが消えた後は矢印キーを押しても
            // 無反応になってしまう（前回実装で実際に発生した不具合）。
            // 実際にどのチャートを動かすかは押された瞬間の「マウスが
            // 乗っているチャート」（__swingHunterActiveChart）を都度参照
            // して決める
            if (window.parent.__swingHunterScrollKeyHandler) {{
                window.parent.document.removeEventListener(
                    "keydown", window.parent.__swingHunterScrollKeyHandler, true
                );
            }}

            // capture: trueでバブリング前（キャプチャフェーズ）に取る。
            // フォーカスがテキスト系input（表示期間・表示幅のセレクト
            // ボックス等、選択後もフォーカスが残り続ける）にある状態だと、
            // そのinput自身がカーソル移動のため矢印キーのbubbleを止めて
            // しまい、document（bubbleフェーズ）まで届かないことがある
            const keydownHandler = function(e) {{
                if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;

                const target = window.parent.__swingHunterActiveChart;
                if (!target || !target.__swingHunterScroll || !window.parent.Plotly) {{
                    return;
                }}
                const scrollState = target.__swingHunterScroll;

                let nextIndex;
                if (e.key === "ArrowLeft") {{
                    nextIndex = Math.max(scrollState.startIndex - 1, 0);
                }} else {{
                    nextIndex = Math.min(scrollState.startIndex + 1, scrollState.maxStartIndex);
                }}
                const endIndex = Math.min(
                    nextIndex + scrollState.visibleBarCount - 1,
                    scrollState.barDates.length - 1
                );
                // startIndexの更新自体はplotly_relayoutハンドラ側でも
                // 行われるが、ここで即時に反映しておくことで連続で矢印キーを
                // 押したときにも正しい起点から1本ずつ動かせる
                scrollState.startIndex = nextIndex;
                window.parent.Plotly.relayout(target, {{
                    "xaxis.range": [
                        scrollState.barDates[nextIndex],
                        scrollState.barDates[endIndex],
                    ],
                }});
                e.preventDefault();
            }};
            window.parent.__swingHunterScrollKeyHandler = keydownHandler;
            window.parent.document.addEventListener("keydown", keydownHandler, true);
        }}

        // st.plotly_chart側の描画は非同期のため、このscriptが先に動いて
        // チャートdivがまだ存在しないことがある。見つかるまで短い間隔で
        // 探し直す（最大5秒。それでも見つからなければ諦める）
        let attempts = 0;
        const timer = setInterval(function() {{
            attempts += 1;
            const gd = findPlotDiv();
            if (gd) {{
                clearInterval(timer);
                setup(gd);
            }} else if (attempts > 50) {{
                clearInterval(timer);
            }}
        }}, 100);
    }})();
    </script>
    """
