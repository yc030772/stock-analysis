from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ══════════════════════════════════════════════════════════════════════════════
# SHARED CHART LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#161b22",
    font=dict(color="#c9d1d9", size=11),
)
_M_DEFAULT = dict(l=4, r=4, t=28, b=4)


# ══════════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_candle_chart(df: pd.DataFrame, ind: dict, patterns: list[dict]) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.58, 0.20, 0.22],
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=("K 線 + 均線 + 布林帶", "成交量", "RSI (14)"),
    )

    # K-line (Taiwan: red=up, green=down)
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color="#f85149"), fillcolor="#f85149"),
        decreasing=dict(line=dict(color="#3fb950"), fillcolor="#3fb950"),
        name="K 線", showlegend=False,
    ), row=1, col=1)

    # MAs
    for key, color, label in [("_s_ma20", "#e3b341", "MA20"),
                               ("_s_ma50", "#58a6ff", "MA50"),
                               ("_s_ma200", "#bc8cff", "MA200")]:
        if ind.get(key) is not None:
            fig.add_trace(go.Scatter(x=df.index, y=ind[key], mode="lines",
                                     line=dict(color=color, width=1.2), name=label), row=1, col=1)

    # Bollinger fill
    idx    = list(df.index)
    bb_up  = ind["_s_bb_up"].tolist()
    bb_lo  = ind["_s_bb_lo"].tolist()
    fig.add_trace(go.Scatter(
        x=idx + list(reversed(idx)), y=bb_up + list(reversed(bb_lo)),
        fill="toself", fillcolor="rgba(88,166,255,0.06)",
        line=dict(color="rgba(0,0,0,0)"), name="布林帶", showlegend=True,
    ), row=1, col=1)
    for y_data, dash, lbl in [(bb_up, "dot", "BB上"), (bb_lo, "dot", "BB下"),
                               (ind["_s_bb_mid"].tolist(), "dash", "BB中")]:
        fig.add_trace(go.Scatter(x=idx, y=y_data, mode="lines",
                                  line=dict(color="#58a6ff", width=0.7, dash=dash),
                                  name=lbl, showlegend=False), row=1, col=1)

    # Pattern annotations
    for pat in patterns:
        if pat["days_ago"] <= 8 and len(df) > pat["days_ago"] + 1:
            pos   = -(pat["days_ago"] + 1)
            x_val = df.index[pos]
            y_val = float(df["High"].iloc[pos]) * 1.013
            color = "#3fb950" if pat["type"] == "bull" else "#f85149"
            short = pat["name"].split("(")[0].strip()
            fig.add_annotation(x=x_val, y=y_val, text=short,
                                showarrow=True, arrowhead=2,
                                arrowcolor=color, arrowsize=0.8,
                                font=dict(size=8, color=color),
                                ax=0, ay=-26, row=1, col=1)

    # Volume
    vol_colors = ["#f85149" if float(c) >= float(o) else "#3fb950"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="成交量",
                          marker_color=vol_colors, showlegend=False), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=ind["_s_rsi"], mode="lines",
                              line=dict(color="#f0883e", width=1.3), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_width=0.8, line_dash="dash",
                  line_color="rgba(248,81,73,0.5)", row=3, col=1)
    fig.add_hline(y=30, line_width=0.8, line_dash="dash",
                  line_color="rgba(63,185,80,0.5)", row=3, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.02)",
                   line_width=0, row=3, col=1)

    fig.update_layout(
        **_DARK_LAYOUT,
        margin=_M_DEFAULT,
        height=600,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=10)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#21262d", zeroline=False)
    return fig


def build_quant_chart(df: pd.DataFrame, ind: dict) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.55, 0.45],
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=("MACD (12/26/9)", "成交量"),
    )

    hist        = ind["_s_macd_hist"]
    bar_colors  = ["#f85149" if v >= 0 else "#3fb950" for v in hist]
    fig.add_trace(go.Bar(x=df.index, y=hist, name="MACD Hist",
                          marker_color=bar_colors, showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ind["_s_macd"], mode="lines",
                              line=dict(color="#58a6ff", width=1.2), name="MACD"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ind["_s_macd_sig"], mode="lines",
                              line=dict(color="#e3b341", width=1.2), name="Signal"), row=1, col=1)
    fig.add_hline(y=0, line_width=0.6, line_color="#30363d", row=1, col=1)

    vol_colors = ["#f85149" if float(c) >= float(o) else "#3fb950"
                  for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="成交量",
                          marker_color=vol_colors, showlegend=False), row=2, col=1)

    fig.update_layout(**_DARK_LAYOUT, margin=_M_DEFAULT, height=340)
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#21262d", zeroline=False)
    return fig
