import streamlit as st
import plotly.express as px
import pandas as pd
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("⚙️ Operations")

    # ── KM Utilization ───────────────────────────────────────
    st.subheader("KM Utilization")
    has_km = all(c in df.columns for c in ["Full KM", "Empty KM", "Total KM"])
    if has_km:
        km_data = df[["Full KM", "Empty KM", "Total KM"]].dropna()
        if len(km_data) > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Full KM", f"{km_data['Full KM'].mean():,.0f}")
            c2.metric("Avg Empty KM", f"{km_data['Empty KM'].mean():,.0f}")
            avg_util = km_data["Full KM"].sum() / km_data["Total KM"].replace(0, pd.NA).sum() * 100
            c3.metric("Overall Utilization", f"{avg_util:.1f}%")

            # Distribution
            if "KM Utilization %" in df.columns:
                util = df["KM Utilization %"].dropna()
                util = util[(util >= 0) & (util <= 100)]
                if len(util) > 0:
                    fig = px.histogram(util, nbins=20, labels={"value": "Utilization %"})
                    fig.update_layout(
                        xaxis_title="KM Utilization %",
                        yaxis_title="# Shipments",
                        showlegend=False,
                        margin=dict(t=20, b=20),
                    )
                    st.plotly_chart(fig, width='stretch')
    else:
        st.info("KM data not available.")

    st.divider()

    # ── Weight distribution ──────────────────────────────────
    if "Weight" in df.columns:
        st.subheader("Weight Distribution")
        w = df["Weight"].dropna()
        if len(w) > 0:
            fig = px.histogram(w, nbins=30, labels={"value": "Weight"})
            fig.update_layout(
                xaxis_title="Weight",
                yaxis_title="# Shipments",
                showlegend=False,
                margin=dict(t=20, b=20),
            )
            st.plotly_chart(fig, width='stretch')

    st.divider()

    # ── Modality / Market / Business Line ────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        if "Modality" in df.columns:
            st.subheader("Modality")
            mod = df.groupby("Modality")["Shipment Weight"].sum().reset_index()
            mod.columns = ["Modality", "Count"]
            fig = px.pie(mod, names="Modality", values="Count", hole=0.4)
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    with col_right:
        if "Carrier" in df.columns:
            st.subheader("Top 10 Carriers")
            carriers_df = df[df["Carrier"].notna() & (df["Carrier"] != "-")].copy()
            if len(carriers_df) > 0:
                carr = carriers_df.groupby("Carrier")["Shipment Weight"].sum().nlargest(10).reset_index()
                carr.columns = ["Carrier", "Shipments"]
                fig = px.bar(carr, x="Shipments", y="Carrier", orientation="h", text_auto=True)
                fig.update_layout(
                    yaxis=dict(autorange="reversed"),
                    margin=dict(t=20, b=20, l=120),
                )
                st.plotly_chart(fig, width='stretch')

    # ── Legal Entity breakdown ────────────────────────────────────
    if "Legal Entity" in df.columns:
        st.subheader("Legal Entity")
        le = df.groupby("Legal Entity")["Shipment Weight"].sum().reset_index()
        le.columns = ["Legal Entity", "Count"]
        fig = px.bar(le, x="Legal Entity", y="Count", text_auto=True, color="Legal Entity")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig, width='stretch')
