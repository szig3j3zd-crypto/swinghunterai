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
    "sma100": "#8c564b",
}
MA_LABELS = {
    "sma3": "3日線",
    "sma5": "5日線",
    "sma7": "7日線",
    "sma10": "10日線",
    "sma20": "20日線",
    "sma60": "60日線",
    "sma100": "100日線",
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
        sma60, sma100 列を持つDataFrame

    show_candlestick
        ローソク足を表示するか

    visible_ma
        表示する移動平均線のキー（"sma3", "sma5", "sma7", "sma10", "sma20",
        "sma60", "sma100"）のタプル/リスト

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
        # x軸にはデータが存在しない日（土日・祝日、週足/月足なら期間内の
        # ほとんどの日）を圧縮するrangebreaksを適用している（下のfig.update_xaxes
        # 参照）ため、隣り合う実データ点同士の実質的な間隔は日足/週足/月足を
        # 問わずどれも「（圧縮されずに残る）1日分」相当になる。棒の幅を
        # 明示しないとPlotlyが表示期間全体分のx値から自動で幅を決めようと
        # して、この圧縮を考慮せず暦日ベースで計算してしまい、週足・月足で
        # 隣の棒とくっついて見えてしまう。1日分を基準に幅を明示することで
        # 日足・週足・月足で見た目の隙間の比率を揃える
        one_day_ms = 24 * 60 * 60 * 1000
        fig.add_trace(
            go.Bar(
                x=df["date"],
                y=df["volume"],
                width=one_day_ms * 0.6,
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
        height=680 if show_volume else 500,
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

    return fig


def build_scroll_sync_script(bar_dates, highs, lows, volumes,
                              visible_bar_count, initial_start_index, storage_key,
                              view_signature):

    """
    チャートの下に表示する、一般的なスクロールバー（トラック＋つまみの
    シンプルな見た目。Plotly標準のレンジスライダーはトラック内に全期間の
    ミニチャートを描画してしまい見た目が煩雑になるため採用しなかった）と、
    左右矢印キーでのスクロール、表示範囲変更時の価格軸・出来高軸の自動
    フィットを行うJavaScriptを組み立てる

    st.components.v1.html(...)でst.plotly_chartの直後に埋め込む想定。
    このscriptが行うのは次の4点

    - チャート下にスクロールバー（トラック＋つまみ）を描画する。つまみの
      位置・幅は現在の表示範囲（Plotlyのxaxis.range）が表示期間全体の
      どこに当たるかで決まる。つまみをドラッグする、またはトラックの
      余白をクリックするとその位置へスクロールする
    - 左右矢印キーでのローソク足1本分ずつのスクロール
    - 表示範囲が変わるたびに（スクロールバー・チャート上のドラッグ
      （Plotly標準のdragmode="pan"）・矢印キーのいずれが原因でも）、
      その範囲内の高値・安値・出来高から価格軸・出来高軸のレンジを自動で
      再フィットし、あわせてスクロールバーのつまみの位置・幅も更新する
    - 表示範囲が変わるたびにsessionStorageへ現在の表示範囲（カレンダー日付）
      を保存し、次にこのチャート（storage_key単位）が再描画されたとき
      （MAチェックボックスの切替、日足/週足/月足の変更など、Streamlitの
      再実行を伴う操作すべて）に自動で復元する。Python側は表示期間・
      表示幅から計算した「最新側」の範囲を常に初期値として渡すため、
      これが無いと操作のたびに表示位置が最新側へ戻ってしまう
      （Streamlit側の制限。詳細はdashboard.pyのst.plotly_chart呼び出し
      付近のコメント参照）

    いずれの操作もStreamlitの再実行を伴わず、ブラウザ側でPlotly.relayoutを
    直接呼ぶことで完結する

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

    storage_key
        表示位置の記憶に使うsessionStorageのキー。銘柄・タブ単位で
        一意にする（例: f"{key_prefix}:{code}"）。日足/週足/月足を
        変えても引き継ぎたいため、意図的に時間足は含めない
        （銘柄・タブが変われば別の記憶として扱う）

    view_signature
        表示期間・表示幅の現在値を表す文字列（例: f"{period_label}:
        {display_width_label}"）。保存済みの表示位置は、これが前回
        保存時と一致する場合のみ復元する。表示期間・表示幅を
        ユーザーが明示的に変更した場合は、その変更を優先し復元は
        スキップする（スキップしないと、変更してもPython側の新しい
        既定表示ではなく古い保存位置が復元され続けてしまう）

    Returns
    -------
    html
        st.components.v1.html()にそのまま渡せるHTML文字列
    """

    dates_json = json.dumps([str(d) for d in bar_dates])
    highs_json = json.dumps([float(v) for v in highs])
    lows_json = json.dumps([float(v) for v in lows])
    volumes_json = json.dumps([float(v) for v in volumes])
    storage_key_json = json.dumps(f"swingHunterChartWindow:{storage_key}")
    view_signature_json = json.dumps(view_signature)

    return f"""
    <style>
        body {{ margin: 0; }}
        #sh-scrollbar-track {{
            position: relative;
            width: 100%;
            height: 14px;
            margin-top: 4px;
            background: rgba(120, 120, 120, 0.18);
            border-radius: 7px;
            box-sizing: border-box;
            cursor: pointer;
        }}
        #sh-scrollbar-thumb {{
            position: absolute;
            top: 0;
            height: 100%;
            min-width: 20px;
            background: rgba(120, 120, 120, 0.6);
            border-radius: 7px;
            cursor: grab;
            box-sizing: border-box;
        }}
        #sh-scrollbar-thumb:hover {{ background: rgba(100, 100, 100, 0.75); }}
        #sh-scrollbar-thumb:active {{ cursor: grabbing; background: rgba(90, 90, 90, 0.8); }}
    </style>
    <div id="sh-scrollbar-track">
        <div id="sh-scrollbar-thumb"></div>
    </div>
    <script>
    (function() {{
        const track = document.getElementById("sh-scrollbar-track");
        const thumb = document.getElementById("sh-scrollbar-thumb");
        const storageKey = {storage_key_json};
        const viewSignature = {view_signature_json};

        // 現在の表示範囲（カレンダー日付）をsessionStorageへ保存する。
        // 保存先はwindow.parent（メインページ）側にする。このiframe自身は
        // Streamlitの再描画のたびに作り直されるため、iframe自身の
        // sessionStorageに保存すると次の再描画までに失われることがある
        function saveWindow(range) {{
            try {{
                window.parent.sessionStorage.setItem(
                    storageKey,
                    JSON.stringify({{
                        start: range[0], end: range[1], viewSignature: viewSignature,
                    }})
                );
            }} catch (err) {{
                // プライベートブラウジング等でsessionStorageが使えなくても
                // チャート自体は通常どおり表示できるよう、握りつぶす
            }}
        }}

        // 前回保存されている表示範囲があれば復元する。MAチェックボックスの
        // 切替・日足/週足/月足の変更など、Streamlitの再実行を伴う操作の
        // たびにPythonは「表示期間・表示幅から計算した最新側」の範囲を
        // 初期値として渡してくるため、これが無いと操作のたびに表示位置が
        // 最新側へ戻ってしまう
        function restoreWindow(gd, scrollState) {{
            // 前回のrestoreWindow()呼び出しで仕掛けた再適用タイマーが
            // まだ残っていればキャンセルする（古い（別のgd・別の範囲を
            // 対象とした）再適用が、この後の新しい復元と競合して表示が
            // 安定しなくなるのを防ぐ）
            pendingRestoreTimers.forEach(function(timerId) {{ clearTimeout(timerId); }});
            pendingRestoreTimers = [];

            let saved;
            try {{
                const raw = window.parent.sessionStorage.getItem(storageKey);
                if (!raw) return;
                saved = JSON.parse(raw);
            }} catch (err) {{
                return;
            }}
            if (!saved || !saved.start || !saved.end) return;
            // 表示期間・表示幅をユーザーが明示的に変更した場合は、その
            // 変更を優先する（保存済みの位置を復元しない）。復元しないと
            // 次に実際に表示範囲が変わった時点（ドラッグ等）でsaveWindow()
            // が新しいviewSignatureで上書き保存する
            if (saved.viewSignature !== viewSignature) return;

            const minMs = scrollState.barTimestamps[0];
            const maxMs = scrollState.barTimestamps[scrollState.barTimestamps.length - 1];
            let startMs = new Date(saved.start).getTime();
            let endMs = new Date(saved.end).getTime();
            if (!(startMs < endMs)) return;

            // 表示期間の変更・日足/週足/月足の切替で、保存済みの範囲が
            // 現在のデータ範囲からはみ出すことがあるためクランプする
            const width = endMs - startMs;
            if (startMs < minMs) {{
                startMs = minMs;
                endMs = startMs + width;
            }}
            if (endMs > maxMs) {{
                endMs = maxMs;
                startMs = endMs - width;
            }}
            startMs = Math.max(startMs, minMs);
            endMs = Math.min(endMs, maxMs);
            if (!(startMs < endMs)) return;

            const targetRange = [
                new Date(startMs).toISOString(),
                new Date(endMs).toISOString(),
            ];

            function applyTargetRange() {{
                const nowRange = gd._fullLayout && gd._fullLayout.xaxis
                    ? gd._fullLayout.xaxis.range : null;
                const alreadyThere = nowRange
                    && Math.abs(new Date(nowRange[0]).getTime() - startMs) < 1000
                    && Math.abs(new Date(nowRange[1]).getTime() - endMs) < 1000;
                if (alreadyThere) return;
                window.parent.Plotly.relayout(gd, {{"xaxis.range": targetRange}});
            }}

            applyTargetRange();
            // st.plotly_chart側は、このscrollStateとは別のStreamlitコンポーネント
            // として少し遅れて（または2段階に分けて）Python側の既定レンジで
            // 再描画されることがあり、その場合ここでの復元が後から上書きされて
            // しまう。同じgdに対して少し時間を置いて複数回再適用することで
            // 上書きに対抗する（既に正しい範囲ならrelayoutを呼ばないため、
            // 定常状態になった後は無駄なPlotly呼び出しは発生しない）。
            // タイマーIDをpendingRestoreTimersに残し、次のrestoreWindow()
            // 呼び出し時にキャンセルできるようにする
            [200, 500, 900, 1500, 2500, 4000].forEach(function(delay) {{
                pendingRestoreTimers.push(setTimeout(applyTargetRange, delay));
            }});
        }}

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

        // スクロールバーのつまみの位置・幅を、現在のxaxis.rangeが表示期間
        // 全体（barTimestampsの最小〜最大）のどこに当たるかから計算する
        function updateThumb(gd, scrollState) {{
            if (!scrollState) return;
            const range = gd && gd._fullLayout && gd._fullLayout.xaxis
                ? gd._fullLayout.xaxis.range : null;
            if (!range) return;

            const minMs = scrollState.barTimestamps[0];
            const maxMs = scrollState.barTimestamps[scrollState.barTimestamps.length - 1];
            const totalMs = Math.max(maxMs - minMs, 1);
            const curStartMs = new Date(range[0]).getTime();
            const curEndMs = new Date(range[1]).getTime();

            let leftPct = ((curStartMs - minMs) / totalMs) * 100;
            let widthPct = ((curEndMs - curStartMs) / totalMs) * 100;
            leftPct = Math.max(0, Math.min(leftPct, 100));
            widthPct = Math.max(2, Math.min(widthPct, 100 - leftPct));
            thumb.style.left = leftPct + "%";
            thumb.style.width = widthPct + "%";
        }}

        // 現在把握している「生きている」チャートdiv・その付随状態。
        // setup()を呼ぶたびに更新する。gd自体をこれらの状態の保管場所に
        // しない（後述）ため、クロージャ内のこの2変数が単一の真実の情報源になる
        let currentGd = null;
        let currentScrollState = null;
        // restoreWindow()が仕掛ける再適用タイマー（下記参照）。新しい
        // restoreWindow()呼び出しのたびに、前回分がまだ残っていればキャンセル
        // する（キャンセルしないと、日足/週足/月足の切替やMAチェックボックスの
        // 連続操作で新旧の復元先が競合し、表示が安定しない）
        let pendingRestoreTimers = [];

        // currentGdがまだDOM上に存在するか確認し、破棄されていれば
        // 現在のチャートdivを探し直してsetup()をやり直す（currentGd・
        // currentScrollStateの更新、plotly_relayoutリスナーの張り替えを含む）。
        // スクロールバーのつまみ・トラックをクリックした瞬間に毎回呼ぶことで、
        // その間にStreamlitの再描画でチャートdivが差し替わっていても
        // 自己修復する
        function ensureLiveGd() {{
            if (currentGd && window.parent.document.contains(currentGd)) {{
                return currentGd;
            }}
            const found = findPlotDiv();
            if (found) {{
                setup(found);
            }}
            return currentGd;
        }}

        function attachRelayoutListener(gd, scrollState) {{
            // マウスドラッグ（Plotly標準のdragmode="pan"）・スクロールバー・
            // 矢印キーのいずれでx軸レンジが変わった場合も、Plotlyが発火する
            // plotly_relayoutイベントを起点に価格軸・出来高軸を再フィット
            // し、スクロールバーのつまみも合わせて更新する。このハンドラは
            // 今回のgd・scrollStateを直接参照するクロージャなので、再描画の
            // たびに張り替える（古いハンドラをそのまま使い回すと、前回の
            // gdが破棄された後は無反応になるため）。同じ関数から呼ぶ
            // 自分自身のy軸更新（Plotly.relayout）が再度plotly_relayoutを
            // 発火させても、そちらはxaxis側のキーを含まないため無限ループには
            // ならない
            if (gd.__swingHunterRelayoutHandler
                    && typeof gd.removeListener === "function") {{
                gd.removeListener("plotly_relayout", gd.__swingHunterRelayoutHandler);
            }}
            const relayoutHandler = function(eventdata) {{
                const xChanged = Object.keys(eventdata).some(function(k) {{
                    return k.indexOf("xaxis.range") === 0;
                }});
                if (!xChanged) return;

                const curRange = gd._fullLayout && gd._fullLayout.xaxis
                    ? gd._fullLayout.xaxis.range : null;
                if (!curRange) return;

                saveWindow(curRange);

                const startMs = new Date(curRange[0]).getTime();
                let startIndex = lowerBound(scrollState.barTimestamps, startMs);
                startIndex = Math.max(0, Math.min(startIndex, scrollState.maxStartIndex));
                scrollState.startIndex = startIndex;

                const ranges = computeYRanges(scrollState, startIndex);
                window.parent.Plotly.relayout(gd, {{
                    "yaxis.range": ranges.yRange,
                    "yaxis2.range": ranges.volRange,
                }});
                updateThumb(gd, scrollState);
            }};
            gd.__swingHunterRelayoutHandler = relayoutHandler;
            gd.on("plotly_relayout", relayoutHandler);
        }}

        function setup(gd) {{
            // scrollStateはこの関数の外（currentScrollState）に持たせ、gd
            // （Plotlyのチャートdiv）には保存しない。gdはStreamlitの再描画の
            // たびに破棄・差し替えされることがあり（Plotly.purge()されると
            // gdの_fullLayout等の内部状態も失われる）、gdに直接ぶら下げると
            // 後から参照したときに既に無効なdivを見てしまうため
            const barDates = {dates_json};
            currentGd = gd;
            currentScrollState = {{
                barDates: barDates,
                barTimestamps: barDates.map(function(d) {{ return new Date(d).getTime(); }}),
                highs: {highs_json},
                lows: {lows_json},
                volumes: {volumes_json},
                visibleBarCount: {int(visible_bar_count)},
                startIndex: {int(initial_start_index)},
                maxStartIndex: Math.max(barDates.length - {int(visible_bar_count)}, 0),
            }};
            updateThumb(gd, currentScrollState);

            // マウスが乗っているチャートを「矢印キーの対象」として覚えておく
            function markActive() {{
                window.parent.__swingHunterActiveChart = gd;
                window.parent.__swingHunterActiveScrollState = currentScrollState;
            }}
            gd.addEventListener("mouseenter", markActive);
            if (gd.matches(":hover")) {{
                markActive();
            }}

            attachRelayoutListener(gd, currentScrollState);

            // 保存済みの表示範囲があれば、Python側が渡した「最新側」の
            // 初期範囲を上書きして復元する（上のattachRelayoutListener
            // の後で呼ぶことで、復元時のrelayoutもY軸再フィット・
            // つまみ更新・再保存の対象になる）
            restoreWindow(gd, currentScrollState);

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
                const scrollState = window.parent.__swingHunterActiveScrollState;
                if (!target || !scrollState || !window.parent.Plotly) {{
                    return;
                }}

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

            // つまみ・トラックへの実際のクリックは、このscriptを埋め込んだ
            // iframe自身のdocumentで発生するイベントであり、親ページの
            // documentへは伝播しない（iframeは別ドキュメントであり、
            // 中で起きたmousedown等が親にbubbleすることはない）。そのため
            // mousedown/mousemove/mouseupはすべてこのiframe自身の要素・
            // documentで受け取る。iframe（＝チャート幅いっぱいの横長・
            // 低いdiv）の高さの範囲内でカーソルが動いている限りは、
            // 横方向にどれだけ動いてもこのdocumentのmousemoveが発火し
            // 続ける。iframeは再描画のたびに作り直されるため、ここで
            // 登録するリスナーも（前回分ごと）毎回新しく作られる形になり、
            // 明示的な後始末は不要
            let dragState = null;

            thumb.addEventListener("mousedown", function(e) {{
                // ドラッグ開始時点でensureLiveGd()を呼び、チャートdivが
                // Streamlitの再描画で破棄・差し替えされていないか確認する
                // （破棄されていた場合は自動的にsetup()をやり直し、
                // currentGd/currentScrollStateとplotly_relayoutリスナーを
                // 新しいdivへ張り替える）。これをしないと、setup()実行時に
                // 見つけたdivがその後無効になった場合にドラッグが反応しなく
                // なる
                const liveGd = ensureLiveGd();
                const range = liveGd && liveGd._fullLayout && liveGd._fullLayout.xaxis
                    ? liveGd._fullLayout.xaxis.range : null;
                if (!currentScrollState || !range) return;
                dragState = {{
                    gd: liveGd,
                    startClientX: e.clientX,
                    startRangeMs: [
                        new Date(range[0]).getTime(),
                        new Date(range[1]).getTime(),
                    ],
                    trackWidthPx: track.getBoundingClientRect().width,
                    minMs: currentScrollState.barTimestamps[0],
                    maxMs: currentScrollState.barTimestamps[currentScrollState.barTimestamps.length - 1],
                }};
                e.preventDefault();
            }});

            document.addEventListener("mousemove", function(e) {{
                if (!dragState || !window.parent.Plotly) {{
                    return;
                }}
                const deltaPx = e.clientX - dragState.startClientX;
                const deltaMs = (deltaPx / dragState.trackWidthPx)
                    * (dragState.maxMs - dragState.minMs);
                const width = dragState.startRangeMs[1] - dragState.startRangeMs[0];
                let newStart = dragState.startRangeMs[0] + deltaMs;
                let newEnd = dragState.startRangeMs[1] + deltaMs;
                if (newStart < dragState.minMs) {{
                    newStart = dragState.minMs;
                    newEnd = newStart + width;
                }}
                if (newEnd > dragState.maxMs) {{
                    newEnd = dragState.maxMs;
                    newStart = newEnd - width;
                }}
                window.parent.Plotly.relayout(dragState.gd, {{
                    "xaxis.range": [
                        new Date(newStart).toISOString(),
                        new Date(newEnd).toISOString(),
                    ],
                }});
            }});

            document.addEventListener("mouseup", function() {{
                dragState = null;
                // このiframe内をクリックするとブラウザのフォーカスがiframe側に
                // 移り、以後の矢印キー等のキー入力が親ページ（window.parent.
                // document）へ届かなくなる（キーイベントはフォーカスのある
                // ドキュメントへ配送されるため）。ドラッグ操作が終わったら
                // フォーカスを親ページへ戻し、矢印キーでのスクロールを
                // 引き続き使えるようにする
                window.parent.focus();
            }});

            // トラックの余白（つまみ以外の部分）をクリックすると、
            // そのクリック位置を中心に表示幅を保ったままジャンプする
            track.addEventListener("mousedown", function(e) {{
                if (e.target === thumb || !window.parent.Plotly) return;
                // つまみのmousedownと同様、クリック時点でensureLiveGd()を呼ぶ
                const liveGd = ensureLiveGd();
                const range = liveGd && liveGd._fullLayout && liveGd._fullLayout.xaxis
                    ? liveGd._fullLayout.xaxis.range : null;
                if (!currentScrollState || !range) return;

                const rect = track.getBoundingClientRect();
                const minMs = currentScrollState.barTimestamps[0];
                const maxMs = currentScrollState.barTimestamps[currentScrollState.barTimestamps.length - 1];
                const clickMs = minMs + ((e.clientX - rect.left) / rect.width) * (maxMs - minMs);
                const width = new Date(range[1]).getTime() - new Date(range[0]).getTime();
                let newStart = clickMs - width / 2;
                let newEnd = clickMs + width / 2;
                if (newStart < minMs) {{
                    newStart = minMs;
                    newEnd = newStart + width;
                }}
                if (newEnd > maxMs) {{
                    newEnd = maxMs;
                    newStart = newEnd - width;
                }}
                window.parent.Plotly.relayout(liveGd, {{
                    "xaxis.range": [
                        new Date(newStart).toISOString(),
                        new Date(newEnd).toISOString(),
                    ],
                }});
                // つまみのドラッグ後と同様、クリックでiframe側に移った
                // フォーカスを親ページへ戻す
                window.parent.focus();
            }});
        }}

        // st.plotly_chart側の描画は非同期のため、このscriptが先に動いて
        // チャートdivがまだ存在しないことがある。見つかるまで短い間隔で
        // 探し直す。さらに、st.plotly_chartはチェックボックス操作等の
        // 再描画のたびにチャートdivを裏で作り直すことがあり（このscroll-sync
        // 用iframe自体はbar_dates等の内容が変わらない限り再読み込みされない
        // ため、その再描画に気づけない）、そのままだと表示位置の復元
        // （restoreWindow）が古いdivにしか適用されず反映されない。そのため
        // 「見つけたら終わり」にせず、iframeが存在する間ずっと定期的に
        // 探し直し、currentGdと異なるdivが見つかるたびにsetup()をやり直す
        setInterval(function() {{
            const gd = findPlotDiv();
            if (gd && gd !== currentGd) {{
                setup(gd);
            }}
        }}, 200);
    }})();
    </script>
    """
