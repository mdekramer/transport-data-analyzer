import streamlit as st
import plotly.express as px
import pandas as pd
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("📊 Overview")

    # ── KPI row ──────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Shipments", f"{df['Shipment Weight'].sum():,.1f}")
    c2.metric("Unique Customers", df["Customer Name"].nunique() if "Customer Name" in df.columns else "N/A")
    c3.metric("Total Weight (t)", f"{df['Weight'].sum() / 1000:,.1f}" if "Weight" in df.columns else "N/A")
    c4.metric(
        "Avg Total KM",
        f"{df['Total KM'].mean():,.0f}" if "Total KM" in df.columns and df["Total KM"].notna().any() else "N/A",
    )

    st.divider()

    # ── Status breakdown ─────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        if "Shipment Status" in df.columns:
            st.subheader("Shipment Status")
            status_counts = df.groupby("Shipment Status")["Shipment Weight"].sum().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig = px.pie(status_counts, names="Status", values="Count", hole=0.4)
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    with col_right:
        if "Spot / Dedicated" in df.columns:
            st.subheader("Spot vs Dedicated")
            sd_counts = df.groupby("Spot / Dedicated")["Shipment Weight"].sum().reset_index()
            sd_counts.columns = ["Type", "Count"]
            fig = px.bar(sd_counts, x="Type", y="Count", color="Type", text_auto=True)
            fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    # ── Market & Business Line ───────────────────────────────
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        if "Market" in df.columns:
            st.subheader("Market Breakdown")
            market = df.groupby("Market")["Shipment Weight"].sum().reset_index()
            market.columns = ["Market", "Count"]
            fig = px.bar(market, x="Market", y="Count", color="Market", text_auto=True)
            fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    with col_right2:
        if "Business Line" in df.columns:
            st.subheader("Business Line")
            bl = df.groupby("Business Line")["Shipment Weight"].sum().reset_index()
            bl.columns = ["Business Line", "Count"]
            fig = px.bar(bl, x="Business Line", y="Count", color="Business Line", text_auto=True)
            fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')
