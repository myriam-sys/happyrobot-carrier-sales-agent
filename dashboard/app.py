"""
HappyRobot — Carrier Sales Operations Dashboard
Visual identity: DM Sans, #FAFAF8 background, muted dark palette.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
from datetime import datetime

import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE_URL: str = os.getenv(
    "API_BASE_URL",
    "https://happyrobot-carrier-sales-agent-production.up.railway.app",
).rstrip("/")
API_KEY: str = os.getenv("API_KEY", "test-key-local")

# Design tokens — HappyRobot visual identity
C = {
    "bg":        "#FAFAF8",
    "white":     "#FFFFFF",
    "text":      "#0D0D0D",
    "muted":     "#6B6B6B",
    "border":    "#E8E8E4",
    "accent":    "#1A1A1A",
    "green":     "#2D6A4F",
    "red":       "#C0392B",
    "orange":    "#E67E22",
    "gray":      "#95A5A6",
    "sidebar_bg":"#F5F5F0",
}

OUTCOME_COLORS = {
    "booked":             C["green"],
    "negotiation_failed": C["red"],
    "carrier_ineligible": C["orange"],
    "no_match":           C["gray"],
    "hung_up":            C["muted"],
}
SENTIMENT_COLORS = {
    "positive":  C["green"],
    "neutral":   C["gray"],
    "frustrated":C["orange"],
    "hostile":   C["red"],
}
OUTCOME_BADGE = {
    "booked":             ("#EDF7F2", C["green"]),
    "negotiation_failed": ("#FDECEA", C["red"]),
    "carrier_ineligible": ("#FEF0E6", C["orange"]),
    "no_match":           ("#F5F5F5", C["muted"]),
    "hung_up":            ("#F5F5F5", "#4A4A4A"),
}
SENTIMENT_BADGE = {
    "positive":  ("#EDF7F2", C["green"]),
    "neutral":   ("#F5F5F5", C["muted"]),
    "frustrated":("#FEF0E6", C["orange"]),
    "hostile":   ("#FDECEA", C["red"]),
}

CHART_BASE = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color=C["muted"], size=12),
    margin=dict(l=8, r=8, t=36, b=8),
)

LOGO_SVG = """
<svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg"
     style="flex-shrink:0;margin-top:3px">
  <path d="M8 4C8 4 4 4 4 8v8c0 4 4 4 4 4s4 0 4-4V8c0-4-4-4-4-4z" fill="#1A1A1A"/>
  <path d="M20 12c0 0-4 0-4 4v8c0 4 4 4 4 4s4 0 4-4v-8c0-4-4-4-4-4z" fill="#1A1A1A"/>
</svg>
"""

# ---------------------------------------------------------------------------
# Page config + global CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HappyRobot — Carrier Sales Ops",
    page_icon="",
    layout="wide",
)

st.markdown(
    f"""
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap"
          rel="stylesheet">
    <style>
        html, body, [class*="css"] {{
            font-family: 'DM Sans', sans-serif;
            background-color: {C["bg"]};
        }}

        /* Page background */
        .stApp {{ background-color: {C["bg"]}; }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {C["sidebar_bg"]} !important;
        }}
        [data-testid="stSidebar"] * {{
            font-family: 'DM Sans', sans-serif !important;
        }}

        /* Hide Streamlit chrome */
        #MainMenu {{ visibility: hidden; }}
        footer    {{ visibility: hidden; }}
        header    {{ visibility: hidden; }}

        /* KPI card — no colored top border */
        .kpi-card {{
            background: {C["white"]};
            border: 1px solid {C["border"]};
            border-radius: 8px;
            padding: 20px 20px 18px;
            min-height: 100px;
        }}
        .kpi-label {{
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {C["muted"]};
            margin-bottom: 10px;
        }}
        .kpi-value {{
            font-size: 28px;
            font-weight: 700;
            color: {C["text"]};
            line-height: 1;
        }}

        /* Section label */
        .section-label {{
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: {C["muted"]};
            margin: 0 0 14px;
        }}

        /* Badge */
        .badge {{
            display: inline-block;
            padding: 2px 9px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.03em;
        }}

        /* Stat card */
        .stat-card {{
            background: {C["white"]};
            border: 1px solid {C["border"]};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 10px;
        }}
        .stat-card-label {{
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {C["muted"]};
            margin-bottom: 6px;
        }}
        .stat-card-value {{
            font-size: 22px;
            font-weight: 700;
            color: {C["text"]};
        }}

        /* Table */
        .log-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .log-table th {{
            text-align: left;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: {C["muted"]};
            border-bottom: 1px solid {C["border"]};
            padding: 8px 12px;
            background: transparent;
        }}
        .log-table td {{
            padding: 11px 12px;
            border-bottom: 1px solid {C["border"]};
            color: {C["text"]};
            vertical-align: middle;
            background: transparent;
        }}
        .log-table tr:last-child td {{ border-bottom: none; }}

        /* Summary list */
        .summary-item {{
            padding: 10px 14px;
            border-bottom: 1px solid {C["border"]};
            font-size: 13px;
            color: {C["text"]};
            line-height: 1.55;
        }}
        .summary-item:last-child {{ border-bottom: none; }}
        .summary-num {{
            font-size: 11px;
            font-weight: 600;
            color: {C["muted"]};
            margin-right: 10px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def fetch_metrics() -> tuple[dict, bool]:
    try:
        r = requests.get(
            f"{API_BASE_URL}/dashboard/metrics",
            headers={"X-API-Key": API_KEY},
            timeout=8,
        )
        r.raise_for_status()
        return r.json(), True
    except Exception:
        return {}, False


@st.cache_data(ttl=30)
def fetch_call_logs(limit: int = 10) -> list[dict]:
    try:
        r = requests.get(
            f"{API_BASE_URL}/calls/log",
            headers={"X-API-Key": API_KEY},
            params={"limit": limit},
            timeout=8,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


metrics, api_ok = fetch_metrics()
call_logs = fetch_call_logs(10)

# Safe accessors
def _outcome(key: str) -> int:
    return metrics.get("outcome_breakdown", {}).get(key, 0)

def _sentiment(key: str) -> int:
    return metrics.get("sentiment_breakdown", {}).get(key, 0)

total_calls: int            = metrics.get("total_calls", 0)
booked: int                 = _outcome("booked")
booking_rate: float         = (booked / total_calls * 100) if total_calls else 0.0
avg_final_rate              = metrics.get("avg_final_rate_usd")
avg_initial_rate            = metrics.get("avg_initial_rate_usd")
avg_rounds: float           = metrics.get("avg_negotiation_rounds", 0.0)
avg_duration_s: float       = metrics.get("avg_call_duration_seconds", 0.0)
total_revenue: float        = metrics.get("total_revenue_booked_usd", 0.0)
available_loads: int        = metrics.get("available_loads", 0)
top_lanes: list[dict]       = metrics.get("top_lanes", [])
sentiment_agreement_rate    = metrics.get("sentiment_agreement_rate")
recent_summaries: list[str] = metrics.get("recent_summaries", [])

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Short aliases — avoids backslash-escaped quotes inside f-string expressions
_text   = C["text"]
_muted  = C["muted"]
_border = C["border"]
_white  = C["white"]
_green  = C["green"]
_orange = C["orange"]
_red    = C["red"]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"<p style='font-size:15px;font-weight:700;color:{C['text']};margin-bottom:2px;line-height:1.3'>"
        "Carrier Sales Ops</p>"
        f"<p style='font-size:12px;color:{C['muted']};margin:0 0 20px'>HappyRobot AI</p>",
        unsafe_allow_html=True,
    )

    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<p style='font-size:12px;color:{C['muted']};margin-top:10px'>Updated: {now_str}</p>",
        unsafe_allow_html=True,
    )

    dot_color = C["green"] if api_ok else C["red"]
    status_label = "API connected" if api_ok else "API unreachable"
    st.markdown(
        f"<p style='font-size:12px;font-weight:500;color:{dot_color};margin-top:4px'>"
        f"&#9679; {status_label}</p>",
        unsafe_allow_html=True,
    )

    st.markdown(f"<hr style='border:none;border-top:1px solid {C['border']};margin:16px 0'>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='font-size:11px;color:{C['muted']}'>Data refreshes on every call logged.</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    f"<div style='display:flex;align-items:flex-start;gap:12px;margin-bottom:4px'>"
    f"  {LOGO_SVG}"
    f"  <div>"
    f"    <h1 style='font-family:DM Sans,sans-serif;font-size:26px;font-weight:700;"
    f"        color:{C['text']};margin:0;letter-spacing:-0.02em;line-height:1.2'>"
    f"      Carrier Sales Operations</h1>"
    f"    <p style='font-family:DM Sans,sans-serif;font-size:13px;font-weight:400;"
    f"        color:{C['muted']};margin:3px 0 0'>"
    f"      Acme Freight Brokerage &mdash; Powered by HappyRobot</p>"
    f"  </div>"
    f"</div>",
    unsafe_allow_html=True,
)

if not api_ok:
    st.error(
        "Could not reach the API. Displaying empty data. "
        f"Check the backend is running at {API_BASE_URL} and the API key is set correctly."
    )

st.markdown("<div style='margin:20px 0 4px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Row 1 — KPI cards
# ---------------------------------------------------------------------------

def kpi(label: str, value: str) -> str:
    return (
        f"<div class='kpi-card'>"
        f"  <div class='kpi-label'>{label}</div>"
        f"  <div class='kpi-value'>{value}</div>"
        f"</div>"
    )

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(kpi("Total Calls", f"{total_calls:,}"), unsafe_allow_html=True)
k2.markdown(kpi("Booking Rate", f"{booking_rate:.1f}%"), unsafe_allow_html=True)
k3.markdown(kpi("Avg Final Rate", f"${avg_final_rate:,.0f}" if avg_final_rate else "&mdash;"), unsafe_allow_html=True)
k4.markdown(kpi("Avg Rounds", f"{avg_rounds:.1f}"), unsafe_allow_html=True)
k5.markdown(kpi("Revenue Booked", f"${total_revenue:,.0f}"), unsafe_allow_html=True)

st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Row 2 — Outcome bar + Sentiment donut
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    outcome_keys   = ["booked", "negotiation_failed", "carrier_ineligible", "no_match", "hung_up"]
    outcome_labels = [k.replace("_", " ").title() for k in outcome_keys]
    outcome_values = [_outcome(k) for k in outcome_keys]
    outcome_colors = [OUTCOME_COLORS[k] for k in outcome_keys]

    fig_outcomes = go.Figure(
        go.Bar(
            x=outcome_values,
            y=outcome_labels,
            orientation="h",
            marker_color=outcome_colors,
            text=outcome_values,
            textposition="outside",
            textfont=dict(size=12, color=C["muted"]),
        )
    )
    fig_outcomes.update_layout(
        title=dict(text="Call Outcomes", font=dict(size=13, weight="bold", color=C["text"])),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   showline=True, linecolor=C["border"]),
        yaxis=dict(showgrid=False, autorange="reversed",
                   tickfont=dict(size=12, color=C["muted"])),
        **CHART_BASE,
    )
    st.plotly_chart(fig_outcomes, use_container_width=True)

with col_right:
    sentiment_keys   = ["positive", "neutral", "frustrated", "hostile"]
    sentiment_labels = [k.title() for k in sentiment_keys]
    sentiment_values = [_sentiment(k) for k in sentiment_keys]
    sentiment_colors = [SENTIMENT_COLORS[k] for k in sentiment_keys]

    fig_sentiment = go.Figure(
        go.Pie(
            labels=sentiment_labels,
            values=sentiment_values,
            hole=0.55,
            marker_colors=sentiment_colors,
            textinfo="label+percent",
            textfont=dict(size=12),
        )
    )
    fig_sentiment.update_layout(
        title=dict(text="Carrier Sentiment", font=dict(size=13, weight="bold", color=C["text"])),
        **CHART_BASE,
    )
    st.plotly_chart(fig_sentiment, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3 — Top lanes + secondary stats
# ---------------------------------------------------------------------------

col_lanes, col_stats = st.columns(2)

with col_lanes:
    if top_lanes:
        lane_labels = [f"{l['origin']} → {l['destination']}" for l in top_lanes]
        lane_calls  = [l["call_count"] for l in top_lanes]
        lane_booked = [l["booked_count"] for l in top_lanes]

        fig_lanes = go.Figure(
            go.Bar(
                x=lane_calls,
                y=lane_labels,
                orientation="h",
                marker=dict(
                    color=lane_booked,
                    colorscale=[[0, C["border"]], [1, C["green"]]],
                    showscale=True,
                    colorbar=dict(title="Booked", thickness=10,
                                  tickfont=dict(size=11, color=C["muted"])),
                ),
                text=[f"{c} calls" for c in lane_calls],
                textposition="outside",
                textfont=dict(size=12, color=C["muted"]),
            )
        )
        fig_lanes.update_layout(
            title=dict(text="Top Lanes by Volume", font=dict(size=13, weight="bold", color=C["text"])),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                       showline=True, linecolor=C["border"]),
            yaxis=dict(showgrid=False, autorange="reversed",
                       tickfont=dict(size=12, color=C["muted"])),
            **CHART_BASE,
        )
        st.plotly_chart(fig_lanes, use_container_width=True)
    else:
        st.info("No lane data yet. Call logs with load IDs will populate this chart.")

with col_stats:
    st.markdown(
        f"<p class='section-label'>Load Board &amp; Call Stats</p>",
        unsafe_allow_html=True,
    )
    mins, secs = divmod(int(avg_duration_s), 60)
    for label, value in [
        ("Available Loads",        str(available_loads)),
        ("Avg Initial Rate",       f"${avg_initial_rate:,.0f}" if avg_initial_rate else "&mdash;"),
        ("Avg Call Duration",      f"{mins}m {secs}s"),
    ]:
        st.markdown(
            f"<div class='stat-card'>"
            f"  <div class='stat-card-label'>{label}</div>"
            f"  <div class='stat-card-value'>{value}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# AI Quality Layer
# ---------------------------------------------------------------------------

st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
st.markdown(
    f"<p class='section-label'>AI Quality Layer</p>",
    unsafe_allow_html=True,
)

ai_left, ai_right = st.columns([1, 2])

with ai_left:
    if sentiment_agreement_rate is not None:
        agree_color = (
            C["green"] if sentiment_agreement_rate >= 80
            else C["orange"] if sentiment_agreement_rate >= 60
            else C["red"]
        )
        st.markdown(
            f"<div class='stat-card'>"
            f"  <div class='stat-card-label'>Sentiment Agreement Rate</div>"
            f"  <div class='stat-card-value' style='color:{agree_color}'>"
            f"    {sentiment_agreement_rate:.1f}%"
            f"  </div>"
            f"  <div style='font-size:11px;color:{_muted};margin-top:6px'>"
            f"    Agent vs. AI Classify"
            f"  </div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='stat-card'>"
            f"  <div class='stat-card-label'>Sentiment Agreement Rate</div>"
            f"  <div class='stat-card-value'>&mdash;</div>"
            f"  <div style='font-size:11px;color:{_muted};margin-top:6px'>"
            f"    No enriched calls yet"
            f"  </div>"
            f"</div>",
            unsafe_allow_html=True,
        )

with ai_right:
    st.markdown(
        f"<p class='section-label'>Recent Negotiation Summaries</p>",
        unsafe_allow_html=True,
    )
    if recent_summaries:
        items_html = "".join(
            f"<div class='summary-item'>"
            f"  <span class='summary-num'>{i + 1}</span>{s}"
            f"</div>"
            for i, s in enumerate(recent_summaries)
        )
        st.markdown(
            f"<div style='background:{C['white']};border:1px solid {C['border']};"
            f"border-radius:8px;overflow:hidden'>{items_html}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='background:{C['white']};border:1px solid {C['border']};"
            f"border-radius:8px;padding:20px 16px;font-size:13px;color:{C['muted']}'>"
            "No summaries yet. Summaries appear after calls are enriched via POST /calls/enrich."
            "</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Call log table
# ---------------------------------------------------------------------------

st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
st.markdown(f"<p class='section-label'>Recent Call Log</p>", unsafe_allow_html=True)

def badge(text: str, bg: str, fg: str) -> str:
    return (
        f"<span class='badge' style='background:{bg};color:{fg}'>"
        f"{text.replace('_', ' ').title()}</span>"
    )

if call_logs:
    rows_html = ""
    for c in call_logs:
        ts        = c.get("timestamp", "")[:16].replace("T", " ")
        carrier   = c.get("carrier_name", "&mdash;")
        load_id   = c.get("load_id") or "&mdash;"
        outcome   = c.get("outcome", "")
        sentiment = c.get("sentiment", "")
        rate      = c.get("final_agreed_rate")
        dur_s     = c.get("call_duration_seconds", 0)
        dur_m, dur_rem = divmod(int(dur_s), 60)

        obg, ofg = OUTCOME_BADGE.get(outcome, ("#F5F5F5", C["muted"]))
        sbg, sfg = SENTIMENT_BADGE.get(sentiment, ("#F5F5F5", C["muted"]))
        rate_str = f"${rate:,.0f}" if rate is not None else "&mdash;"
        dur_str  = f"{dur_m}m {dur_rem}s" if dur_m else f"{dur_rem}s"

        rows_html += (
            f"<tr>"
            f"  <td style='color:{_muted};font-size:12px'>{ts}</td>"
            f"  <td style='font-weight:500;color:{_text}'>{carrier}</td>"
            f"  <td style='color:{_muted}'>{load_id}</td>"
            f"  <td>{badge(outcome, obg, ofg)}</td>"
            f"  <td style='font-weight:600;color:{_text}'>{rate_str}</td>"
            f"  <td>{badge(sentiment, sbg, sfg)}</td>"
            f"  <td style='color:{_muted}'>{dur_str}</td>"
            f"</tr>"
        )

    st.markdown(
        f"<div style='background:{_white};border:1px solid {_border};"
        f"border-radius:8px;overflow:hidden'>"
        f"<table class='log-table'>"
        f"<thead><tr>"
        f"<th>Timestamp</th><th>Carrier</th><th>Load</th>"
        f"<th>Outcome</th><th>Final Rate</th><th>Sentiment</th><th>Duration</th>"
        f"</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<div style='background:{_white};border:1px solid {_border};"
        f"border-radius:8px;padding:32px;text-align:center;"
        f"font-size:14px;color:{_muted}'>"
        "No call logs yet. Calls handled by the AI agent will appear here."
        "</div>",
        unsafe_allow_html=True,
    )
