"""
HappyRobot — Carrier Sales Operations Dashboard
Streamlit app that pulls live metrics from the FastAPI backend.

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

OUTCOME_COLORS: dict[str, str] = {
    "booked": "#22c55e",
    "negotiation_failed": "#ef4444",
    "carrier_ineligible": "#f97316",
    "no_match": "#94a3b8",
    "hung_up": "#64748b",
}
SENTIMENT_COLORS: dict[str, str] = {
    "positive": "#22c55e",
    "neutral": "#3b82f6",
    "frustrated": "#f97316",
    "hostile": "#ef4444",
}
CHART_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=40, b=10),
)

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="HappyRobot — Carrier Sales Ops",
    page_icon="🤖",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data fetch
# ---------------------------------------------------------------------------

@st.cache_data(ttl=30)
def fetch_metrics() -> tuple[dict, bool]:
    """
    Fetch /dashboard/metrics from the API.

    Returns (metrics_dict, api_ok).  On failure returns empty defaults so the
    page still renders without crashing.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/dashboard/metrics",
            headers={"X-API-Key": API_KEY},
            timeout=8,
        )
        resp.raise_for_status()
        return resp.json(), True
    except Exception:
        return {}, False


metrics, api_ok = fetch_metrics()

# Safe accessors with zero defaults
def _outcome(key: str) -> int:
    return metrics.get("outcome_breakdown", {}).get(key, 0)

def _sentiment(key: str) -> int:
    return metrics.get("sentiment_breakdown", {}).get(key, 0)

total_calls: int = metrics.get("total_calls", 0)
booked: int = _outcome("booked")
booking_rate: float = (booked / total_calls * 100) if total_calls else 0.0
avg_final_rate: float | None = metrics.get("avg_final_rate_usd")
avg_initial_rate: float | None = metrics.get("avg_initial_rate_usd")
avg_rounds: float = metrics.get("avg_negotiation_rounds", 0.0)
avg_duration_s: float = metrics.get("avg_call_duration_seconds", 0.0)
total_revenue: float = metrics.get("total_revenue_booked_usd", 0.0)
available_loads: int = metrics.get("available_loads", 0)
booked_loads: int = metrics.get("booked_loads", 0)
top_lanes: list[dict] = metrics.get("top_lanes", [])

now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Controls")

    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown(f"**Last updated:** {now_str}")

    if api_ok:
        st.markdown("🟢 **API Connected**")
    else:
        st.markdown("🔴 **API Unreachable**")

    st.markdown("---")
    st.caption("Data updates on every call logged")
    st.caption(f"Endpoint: `{API_BASE_URL}`")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("# 🤖 Carrier Sales Operations Dashboard")
st.markdown("**Powered by HappyRobot AI — Acme Freight Brokerage**")
st.caption(f"Last updated: {now_str} · Refresh the page or click Refresh in the sidebar")

if not api_ok:
    st.error(
        "⚠️ Could not reach the API. Displaying zero/empty data. "
        f"Check that the backend is running at `{API_BASE_URL}` and that your API key is correct.",
        icon="🚨",
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1 — KPI cards
# ---------------------------------------------------------------------------

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("📞 Total Calls", f"{total_calls:,}")
k2.metric("✅ Booking Rate", f"{booking_rate:.1f}%")
k3.metric(
    "💵 Avg Final Rate",
    f"${avg_final_rate:,.0f}" if avg_final_rate is not None else "—",
)
k4.metric("🔁 Avg Negotiation Rounds", f"{avg_rounds:.1f}")
k5.metric("💰 Total Revenue", f"${total_revenue:,.0f}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 2 — Outcome bar + Sentiment donut
# ---------------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    outcome_keys = ["booked", "negotiation_failed", "carrier_ineligible", "no_match", "hung_up"]
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
        title="Call Outcomes",
        xaxis_title="Calls",
        yaxis=dict(autorange="reversed"),
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig_outcomes, use_container_width=True)

with col_right:
    sentiment_keys = ["positive", "neutral", "frustrated", "hostile"]
    sentiment_labels = [k.title() for k in sentiment_keys]
    sentiment_values = [_sentiment(k) for k in sentiment_keys]
    sentiment_colors = [SENTIMENT_COLORS[k] for k in sentiment_keys]

    fig_sentiment = go.Figure(
        go.Pie(
            labels=sentiment_labels,
            values=sentiment_values,
            hole=0.5,
            marker_colors=sentiment_colors,
            textinfo="label+percent",
        )
    )
    fig_sentiment.update_layout(
        title="Carrier Sentiment",
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig_sentiment, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 3 — Top lanes chart + stacked metric cards
# ---------------------------------------------------------------------------

col_lanes, col_stats = st.columns(2)

with col_lanes:
    if top_lanes:
        lane_labels = [f"{l['origin']} → {l['destination']}" for l in top_lanes]
        lane_calls = [l["call_count"] for l in top_lanes]
        lane_booked = [l["booked_count"] for l in top_lanes]

        fig_lanes = go.Figure(
            go.Bar(
                x=lane_calls,
                y=lane_labels,
                orientation="h",
                marker=dict(
                    color=lane_booked,
                    colorscale=[[0, "#94a3b8"], [1, "#22c55e"]],
                    showscale=True,
                    colorbar=dict(title="Booked"),
                ),
                text=[f"{c} calls / {b} booked" for c, b in zip(lane_calls, lane_booked)],
                textposition="outside",
            )
        )
        fig_lanes.update_layout(
            title="Top Lanes by Volume",
            xaxis_title="Calls",
            yaxis=dict(autorange="reversed"),
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig_lanes, use_container_width=True)
    else:
        st.info("No lane data yet — call logs with load IDs will appear here.")

with col_stats:
    st.markdown("### Load Board & Call Stats")

    st.metric("📦 Available Loads on Board", available_loads)

    st.metric(
        "📊 Avg Initial Rate Offered",
        f"${avg_initial_rate:,.0f}" if avg_initial_rate is not None else "—",
    )

    mins, secs = divmod(int(avg_duration_s), 60)
    st.metric("⏱️ Avg Call Duration", f"{mins} min {secs}s")
