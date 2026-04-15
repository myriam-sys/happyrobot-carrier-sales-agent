"""
HappyRobot — Carrier Sales Operations Dashboard
Clean, professional Streamlit UI backed by the FastAPI metrics endpoint.

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

# Design tokens
C = {
    "near_black": "#0f172a",
    "dark":       "#1e293b",
    "medium":     "#334155",
    "muted":      "#64748b",
    "border":     "#e2e8f0",
    "surface":    "#f8fafc",
    "green":      "#22c55e",
    "red":        "#ef4444",
    "orange":     "#f97316",
    "blue":       "#3b82f6",
    "slate":      "#94a3b8",
    "gray":       "#64748b",
}

OUTCOME_COLORS = {
    "booked":              C["green"],
    "negotiation_failed":  C["red"],
    "carrier_ineligible":  C["orange"],
    "no_match":            C["slate"],
    "hung_up":             C["gray"],
}
SENTIMENT_COLORS = {
    "positive":  C["green"],
    "neutral":   C["blue"],
    "frustrated":C["orange"],
    "hostile":   C["red"],
}
OUTCOME_BADGE_BG = {
    "booked":              ("#dcfce7", "#166534"),
    "negotiation_failed":  ("#fee2e2", "#991b1b"),
    "carrier_ineligible":  ("#ffedd5", "#9a3412"),
    "no_match":            ("#f1f5f9", "#475569"),
    "hung_up":             ("#f1f5f9", "#334155"),
}
SENTIMENT_BADGE_BG = {
    "positive":  ("#dcfce7", "#166534"),
    "neutral":   ("#dbeafe", "#1e40af"),
    "frustrated":("#ffedd5", "#9a3412"),
    "hostile":   ("#fee2e2", "#991b1b"),
}

CHART_BASE = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=C["medium"]),
    margin=dict(l=10, r=10, t=44, b=10),
)

# ---------------------------------------------------------------------------
# Page config + global CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HappyRobot — Carrier Sales Ops",
    page_icon="",
    layout="wide",
)

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        /* Hide Streamlit chrome */
        #MainMenu { visibility: hidden; }
        footer    { visibility: hidden; }

        /* KPI card */
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px 20px 16px;
            height: 110px;
        }
        .kpi-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #64748b;
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 26px;
            font-weight: 700;
            color: #0f172a;
            line-height: 1;
        }

        /* Section header */
        .section-title {
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: #64748b;
            margin: 0 0 12px;
        }

        /* Badge */
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.04em;
        }

        /* Stat row */
        .stat-row {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 10px;
        }
        .stat-row-label {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 4px;
        }
        .stat-row-value {
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
        }

        /* Table */
        .log-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .log-table th {
            text-align: left;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: #64748b;
            border-bottom: 1px solid #e2e8f0;
            padding: 8px 12px;
        }
        .log-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
            vertical-align: middle;
        }
        .log-table tr:last-child td { border-bottom: none; }
        .log-table tr:hover td    { background: #f8fafc; }
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

total_calls: int       = metrics.get("total_calls", 0)
booked: int            = _outcome("booked")
booking_rate: float    = (booked / total_calls * 100) if total_calls else 0.0
avg_final_rate         = metrics.get("avg_final_rate_usd")
avg_initial_rate       = metrics.get("avg_initial_rate_usd")
avg_rounds: float      = metrics.get("avg_negotiation_rounds", 0.0)
avg_duration_s: float  = metrics.get("avg_call_duration_seconds", 0.0)
total_revenue: float   = metrics.get("total_revenue_booked_usd", 0.0)
available_loads: int   = metrics.get("available_loads", 0)
top_lanes: list[dict]  = metrics.get("top_lanes", [])

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"<p style='font-size:18px;font-weight:700;color:{C['near_black']};margin-bottom:4px'>"
        "Carrier Sales Ops</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-size:12px;color:{C['muted']};margin-top:0'>HappyRobot AI</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<p style='font-size:12px;color:{C['muted']};margin-top:8px'>"
        f"Updated: {now_str}</p>",
        unsafe_allow_html=True,
    )

    status_color = C["green"] if api_ok else C["red"]
    status_label = "API Connected" if api_ok else "API Unreachable"
    st.markdown(
        f"<p style='font-size:12px;font-weight:500;color:{status_color}'>"
        f"&#9679; {status_label}</p>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        f"<p style='font-size:11px;color:{C['muted']}'>Data updates on every call logged</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    f"<h1 style='font-family:Inter,sans-serif;font-size:28px;font-weight:700;"
    f"color:{C['near_black']};margin-bottom:4px;line-height:1.2'>"
    "Carrier Sales Operations</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='font-family:Inter,sans-serif;font-size:14px;font-weight:400;"
    f"color:{C['muted']};margin-top:0;margin-bottom:20px'>"
    "Powered by HappyRobot AI &mdash; Acme Freight Brokerage</p>",
    unsafe_allow_html=True,
)

if not api_ok:
    st.error(
        "Could not reach the API. Displaying zero/empty data. "
        f"Check that the backend is running at {API_BASE_URL} and that your API key is correct."
    )

# ---------------------------------------------------------------------------
# Row 1 — KPI cards
# ---------------------------------------------------------------------------

def kpi_card(label: str, value: str, accent: str) -> str:
    return (
        f"<div class='kpi-card' style='border-top:3px solid {accent}'>"
        f"  <div class='kpi-label'>{label}</div>"
        f"  <div class='kpi-value'>{value}</div>"
        f"</div>"
    )

k1, k2, k3, k4, k5 = st.columns(5)

k1.markdown(kpi_card("Total Calls", f"{total_calls:,}", C["blue"]), unsafe_allow_html=True)
k2.markdown(kpi_card("Booking Rate", f"{booking_rate:.1f}%", C["green"]), unsafe_allow_html=True)
k3.markdown(
    kpi_card("Avg Final Rate", f"${avg_final_rate:,.0f}" if avg_final_rate else "&mdash;", C["blue"]),
    unsafe_allow_html=True,
)
k4.markdown(kpi_card("Avg Negotiation Rounds", f"{avg_rounds:.1f}", C["orange"]), unsafe_allow_html=True)
k5.markdown(kpi_card("Total Revenue Booked", f"${total_revenue:,.0f}", C["green"]), unsafe_allow_html=True)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

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
        )
    )
    fig_outcomes.update_layout(
        title=dict(text="Call Outcomes", font=dict(size=14, weight="bold")),
        xaxis=dict(title="Calls", showgrid=False, zeroline=False),
        yaxis=dict(autorange="reversed", showgrid=False),
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
            hole=0.52,
            marker_colors=sentiment_colors,
            textinfo="label+percent",
            textfont=dict(size=12),
        )
    )
    fig_sentiment.update_layout(
        title=dict(text="Carrier Sentiment", font=dict(size=14, weight="bold")),
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
                    colorscale=[[0, C["slate"]], [1, C["green"]]],
                    showscale=True,
                    colorbar=dict(title="Booked", thickness=12),
                ),
                text=[f"{c} calls / {b} booked" for c, b in zip(lane_calls, lane_booked)],
                textposition="outside",
            )
        )
        fig_lanes.update_layout(
            title=dict(text="Top Lanes by Volume", font=dict(size=14, weight="bold")),
            xaxis=dict(title="Calls", showgrid=False, zeroline=False),
            yaxis=dict(autorange="reversed", showgrid=False),
            **CHART_BASE,
        )
        st.plotly_chart(fig_lanes, use_container_width=True)
    else:
        st.info("No lane data yet — call logs with load IDs will appear here.")

with col_stats:
    st.markdown(
        "<p class='section-title'>Load Board &amp; Call Stats</p>",
        unsafe_allow_html=True,
    )

    mins, secs = divmod(int(avg_duration_s), 60)

    for label, value in [
        ("Available Loads on Board",  str(available_loads)),
        ("Avg Initial Rate Offered",  f"${avg_initial_rate:,.0f}" if avg_initial_rate else "&mdash;"),
        ("Avg Call Duration",         f"{mins} min {secs}s"),
    ]:
        st.markdown(
            f"<div class='stat-row'>"
            f"  <div class='stat-row-label'>{label}</div>"
            f"  <div class='stat-row-value'>{value}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Call log table
# ---------------------------------------------------------------------------

st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
st.markdown(
    "<p class='section-title'>Recent Call Log</p>",
    unsafe_allow_html=True,
)

def badge(text: str, bg: str, fg: str) -> str:
    return (
        f"<span class='badge' style='background:{bg};color:{fg}'>"
        f"{text.replace('_', ' ').title()}</span>"
    )

if call_logs:
    rows_html = ""
    for c in call_logs:
        ts = c.get("timestamp", "")[:16].replace("T", " ")
        carrier  = c.get("carrier_name", "&mdash;")
        load_id  = c.get("load_id") or "&mdash;"
        outcome  = c.get("outcome", "")
        sentiment= c.get("sentiment", "")
        rate     = c.get("final_agreed_rate")
        dur_s    = c.get("call_duration_seconds", 0)
        dur_m, dur_rem = divmod(int(dur_s), 60)

        obg, ofg = OUTCOME_BADGE_BG.get(outcome, ("#f1f5f9", "#334155"))
        sbg, sfg = SENTIMENT_BADGE_BG.get(sentiment, ("#f1f5f9", "#334155"))

        rate_str = f"${rate:,.0f}" if rate is not None else "&mdash;"
        dur_str  = f"{dur_m}m {dur_rem}s" if dur_m else f"{dur_rem}s"

        rows_html += (
            f"<tr>"
            f"  <td style='color:{C['muted']};font-size:12px'>{ts}</td>"
            f"  <td style='font-weight:500'>{carrier}</td>"
            f"  <td style='color:{C['muted']}'>{load_id}</td>"
            f"  <td>{badge(outcome, obg, ofg)}</td>"
            f"  <td style='font-weight:600;color:{C['near_black']}'>{rate_str}</td>"
            f"  <td>{badge(sentiment, sbg, sfg)}</td>"
            f"  <td style='color:{C['muted']}'>{dur_str}</td>"
            f"</tr>"
        )

    st.markdown(
        f"""
        <div style='background:#ffffff;border:1px solid {C['border']};
                    border-radius:8px;overflow:hidden;padding:4px 0'>
          <table class='log-table'>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Carrier</th>
                <th>Load ID</th>
                <th>Outcome</th>
                <th>Final Rate</th>
                <th>Sentiment</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<div style='background:#f8fafc;border:1px solid {C['border']};"
        f"border-radius:8px;padding:32px;text-align:center;"
        f"color:{C['muted']};font-size:14px'>"
        "No call logs yet. Calls logged by the AI agent will appear here."
        "</div>",
        unsafe_allow_html=True,
    )
