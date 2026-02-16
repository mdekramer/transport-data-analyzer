import streamlit as st
import plotly.express as px
import pandas as pd
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("🌍 Geography")

    col_left, col_right = st.columns(2)

    # ── Load country ──────────────────────────────
    with col_left:
        if "Load Country" in df.columns:
            st.subheader("Load Country Volume")
            lc = df.groupby("Load Country")["Shipment Weight"].sum().nlargest(15).reset_index()
            lc.columns = ["Country", "Shipments"]
            fig = px.bar(lc, x="Shipments", y="Country", orientation="h", text_auto=True,
                         color="Shipments", color_continuous_scale="Greens")
            fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                              margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    # ── Unload country ─────────────────────────────
    with col_right:
        if "Unload Country" in df.columns:
            st.subheader("Unload Country Volume")
            uc = df.groupby("Unload Country")["Shipment Weight"].sum().nlargest(15).reset_index()
            uc.columns = ["Country", "Shipments"]
            fig = px.bar(uc, x="Shipments", y="Country", orientation="h", text_auto=True,
                         color="Shipments", color_continuous_scale="Purples")
            fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                              margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    # ── Top routes ──────────────────────────────────────────
    if "Route" in df.columns:
        st.subheader("Top 15 Routes (Load → Unload Country)")
        routes = df.groupby("Route")["Shipment Weight"].sum().nlargest(15).reset_index()
        routes.columns = ["Route", "Shipments"]
        fig = px.bar(routes, x="Shipments", y="Route", orientation="h", text_auto=True,
                     color="Shipments", color_continuous_scale="Sunset")
        fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                          margin=dict(t=20, b=20, l=120))
        st.plotly_chart(fig, width='stretch')

    # ── Region drill-down ────────────────────────────────────────
    st.subheader("Region Drill-Down")
    region_col = st.selectbox("Region type", ["Load Region", "Unload Region"])
    if region_col in df.columns:
        reg = df.groupby(region_col)["Shipment Weight"].sum().nlargest(20).reset_index()
        reg.columns = ["Region", "Shipments"]
        fig = px.bar(reg, x="Shipments", y="Region", orientation="h", text_auto=True,
                     color="Shipments", color_continuous_scale="Viridis")
        fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                          margin=dict(t=20, b=20, l=180))
        st.plotly_chart(fig, width='stretch')
