import streamlit as st
import plotly.express as px
import pandas as pd


def render(df: pd.DataFrame):
    st.header("👥 Customer Analysis")

    if "Customer Name" not in df.columns:
        st.warning("No 'Customer Name' column found.")
        return

    # ── Top N selector ───────────────────────────────────────
    top_n = st.slider("Show top N customers", 5, 30, 10)

    # ── Top customers by shipment count ──────────────────────
    st.subheader(f"Top {top_n} Customers by Shipment Count")
    top = df["Customer Name"].value_counts().head(top_n).reset_index()
    top.columns = ["Customer", "Shipments"]
    fig = px.bar(top, x="Shipments", y="Customer", orientation="h", text_auto=True, color="Shipments",
                 color_continuous_scale="Teal")
    fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
                      margin=dict(t=20, b=20, l=150))
    st.plotly_chart(fig, width='stretch')

    # ── Customer trend over time ─────────────────────────────
    st.subheader("Customer Volume Trend Over Time")
    if "Load Month Name" in df.columns:
        top_names = df["Customer Name"].value_counts().head(top_n).index.tolist()
        trend_df = df[df["Customer Name"].isin(top_names)].copy()
        trend = (
            trend_df.groupby(["Load Month Name", "Customer Name"])
            .size()
            .reset_index(name="Shipments")
        )
        fig = px.line(trend, x="Load Month Name", y="Shipments", color="Customer Name", markers=True)
        fig.update_layout(xaxis_title="Month", margin=dict(t=20, b=20))
        st.plotly_chart(fig, width='stretch')

    # ── Customer × Business Line breakdown ───────────────────────────
    if "Business Line" in df.columns:
        st.subheader(f"Top {top_n} Customers × Business Line")
        top_names = df["Customer Name"].value_counts().head(top_n).index.tolist()
        cb = df[df["Customer Name"].isin(top_names)].groupby(
            ["Customer Name", "Business Line"]
        ).size().reset_index(name="Shipments")
        fig = px.bar(cb, x="Customer Name", y="Shipments", color="Business Line", text_auto=True)
        fig.update_layout(margin=dict(t=20, b=20))
        st.plotly_chart(fig, width='stretch')
