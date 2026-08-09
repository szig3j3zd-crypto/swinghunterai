import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 陽線（上昇）=赤、陰線（下落）=青。日本の株価チャートの慣例に合わせる
CANDLE_UP_COLOR = "#d1495b"
CANDLE_DOWN_COLOR = "#2e6f95"

# 出来高は陽線/陰線で色分けせず、全て同じ色にする
VOLUME_COLOR = "#e6b800"

# 短期・中期・長期の順で色を固定する（周期的に割り当てない）
MA_COLORS = {
    "sma5": "#e6b800",
    "sma20": "#d62728",
    "sma60": "#1f5fa8",
}
MA_LABELS = {
    "sma5": "5日線",
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


def build_price_chart(df, show_candlestick=True, visible_ma=(), show_volume=True,
                       x_range=None, y_range=None, volume_range=None,
                       ohlc_text=None, uirevision=None):

    """
    ローソク足・移動平均線・出来高のチャートを作る

    Parameters
    ----------
    df
        date, open, high, low, close, volume, sma5, sma20, sma60 列を持つDataFrame

    show_candlestick
        ローソク足を表示するか

    visible_ma
        表示する移動平均線のキー（"sma5", "sma20", "sma60"）のタプル/リスト

    show_volume
        出来高サブプロットを表示するか

    x_range
        初期表示するx軸（日付）の範囲 [開始日, 終了日]。Noneなら全期間

    y_range
        初期表示する株価軸の範囲 [下限, 上限]。Noneなら自動

    volume_range
        初期表示する出来高軸の範囲 [下限, 上限]。Noneなら自動

    ohlc_text
        凡例の右側に表示する高値・安値・始値・終値などのテキスト。Noneなら非表示

    uirevision
        この値が前回描画時と同じなら、ユーザーが手動でズーム/パンした状態を
        維持する（表示期間・銘柄を変えたときだけ値を変えてリセットさせる）

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
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=680 if show_volume else 500,
        margin=dict(l=40, r=20, t=10, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        xaxis_rangeslider_visible=False,
        dragmode="zoom",
        hovermode="x unified",
        uirevision=uirevision,
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)

    # shared_xaxesでも各サブプロットのrangeは個別に指定する必要があるため、
    # 全x軸（row指定なし）に同じrangeを適用する
    if x_range is not None:
        fig.update_xaxes(range=x_range)

    if y_range is not None:
        fig.update_yaxes(range=y_range, row=1, col=1)

    if show_volume and volume_range is not None:
        fig.update_yaxes(range=volume_range, row=2, col=1)

    if ohlc_text:
        # 凡例のすぐ右（モードバーのアイコンとは被らない位置）に表示する
        fig.add_annotation(
            text=ohlc_text,
            xref="paper",
            yref="paper",
            x=0.35,
            y=1.01,
            xanchor="left",
            yanchor="bottom",
            showarrow=False,
            # Streamlitの標準テキストの見た目（濃色・読みやすいサイズ）に合わせる
            font=dict(size=15, color="#31333F"),
        )

    return fig
