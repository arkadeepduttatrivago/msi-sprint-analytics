"""trivago brand tokens, Plotly chart template, and reusable UI components."""

import plotly.graph_objects as go
import streamlit as st

# ── Color tokens ──────────────────────────────────────────────────────
RED = "#E32851"
BLUE = "#0088D9"
ORANGE = "#FF932C"
PINK = "#FF9DDE"
LIGHTBLUE = "#78DAFF"
YELLOW = "#FFCC31"
GREEN = "#008513"

WHITE = "#FFFFFF"
WARM_WHITE = "#F8F8F6"
GRAY_100 = "#F7F7F7"
GRAY_200 = "#F0F0F0"
GRAY_300 = "#E0E0E0"
GRAY_500 = "#808080"
GRAY_700 = "#515151"
GRAY_900 = "#1A1A1A"

SERIES_ORDER = [RED, ORANGE, BLUE, PINK, LIGHTBLUE, YELLOW]
FONT_STACK = "Arial, Helvetica Neue, sans-serif"

TEAM_COLORS = {
    "MSI_OPS": BLUE,
    "MSI_EXP": ORANGE,
    "MSI_BRAND_CIM": RED,
}

# ── Plotly template ───────────────────────────────────────────────────
PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FONT_STACK, color=GRAY_900, size=13),
        plot_bgcolor=WHITE,
        paper_bgcolor=WHITE,
        xaxis=dict(gridcolor=GRAY_300, showgrid=False, zeroline=False),
        yaxis=dict(gridcolor=GRAY_300, showgrid=True, zeroline=False),
        colorway=SERIES_ORDER,
        margin=dict(l=60, r=30, t=50, b=50),
        hoverlabel=dict(font_size=12, font_family=FONT_STACK),
    )
)


def apply_chart_defaults(fig: go.Figure, height: int = 420) -> go.Figure:
    """Apply brand styling to any Plotly figure."""
    fig.update_layout(template=PLOTLY_TEMPLATE, height=height)
    return fig


# ── Reusable UI components ────────────────────────────────────────────
def kpi_row(metrics: list[dict]):
    """Render a row of KPI cards.

    Each dict: {"label": str, "value": str|int, "delta": str|None, "color": str}
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        color = m.get("color", BLUE)
        delta_html = ""
        if m.get("delta") is not None:
            delta_html = (
                f'<div style="font-size:13px;color:{color};'
                f'margin-top:2px;">{m["delta"]}</div>'
            )
        col.markdown(
            f"""<div style="background:{GRAY_100};border-radius:12px;
            padding:18px 14px;text-align:center;
            border-top:4px solid {color};">
            <div style="font-size:11px;color:{GRAY_500};
            text-transform:uppercase;letter-spacing:.5px;">{m["label"]}</div>
            <div style="font-size:30px;font-weight:700;
            color:{GRAY_900};margin-top:4px;">{m["value"]}</div>
            {delta_html}</div>""",
            unsafe_allow_html=True,
        )


def section_header(title: str, subtitle: str = ""):
    """Render a styled section header."""
    sub = f'<div style="font-size:12px;color:{GRAY_500};">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""<div style="margin:24px 0 12px;">
        <div style="font-size:18px;font-weight:700;color:{GRAY_900};">{title}</div>
        {sub}</div>""",
        unsafe_allow_html=True,
    )


def trv_logo_html() -> str:
    return (
        '<span style="font-weight:700;font-size:20px;">'
        '<span style="color:#E32851">t</span>'
        '<span style="color:#E32851">r</span>'
        '<span style="color:#E32851">i</span>'
        '<span style="color:#FF932C">v</span>'
        '<span style="color:#FF932C">a</span>'
        '<span style="color:#0088D9">g</span>'
        '<span style="color:#0088D9">o</span></span>'
    )
