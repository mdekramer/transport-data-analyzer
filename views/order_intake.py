import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("📈 Order Intake Patterns")

    if "Order Placed Date" not in df.columns or df["Order Placed Date"].isna().all():
        st.warning("No 'Order Placed Date' data available for this analysis.")
        return

    orders = df.dropna(subset=["Order Placed Date"]).copy()
    orders["OPD"] = orders["Order Placed Date"]
    orders["Year"] = orders["OPD"].dt.year.astype(str)
    orders["ISOWeek"] = orders["OPD"].dt.isocalendar().week.astype(int)

    available_years = sorted(orders["Year"].unique())

    # ── Aggregation toggle ───────────────────────────────────
    agg = st.radio("Aggregate by", ["Week", "Month"], horizontal=True, key="yoy_agg")

    # ══════════════════════════════════════════════════════════
    # 1. YEAR-OVER-YEAR RUNNING TOTAL
    # ══════════════════════════════════════════════════════════
    st.subheader("Year-over-Year Running Total")
    # Colorblind-friendly colors: red and blue
    colors_yoy = {available_years[0]: "#d62728", available_years[1]: "#1f77b4"} if len(available_years) >= 2 else {year: ["#d62728", "#1f77b4"][i % 2] for i, year in enumerate(available_years)}
    
    fig = go.Figure()
    for year in available_years:
        yr_df = orders[orders["Year"] == year].copy()
        if agg == "Week":
            grouped = yr_df.groupby("ISOWeek")["Shipment Weight"].sum().reset_index(name="Orders")
            grouped = grouped.sort_values("ISOWeek")
            grouped["Cumulative"] = grouped["Orders"].cumsum()
            x_vals = grouped["ISOWeek"]
            x_title = "Week #"
        else:
            yr_df["Month"] = yr_df["OPD"].dt.month
            grouped = yr_df.groupby("Month")["Shipment Weight"].sum().reset_index(name="Orders")
            grouped = grouped.sort_values("Month")
            grouped["Cumulative"] = grouped["Orders"].cumsum()
            x_vals = grouped["Month"]
            x_title = "Month"

        fig.add_trace(go.Scatter(
            x=x_vals, y=grouped["Cumulative"],
            mode="lines+markers", name=year,
            line=dict(color=colors_yoy.get(year, "#1f77b4")),
            marker=dict(color=colors_yoy.get(year, "#1f77b4")),
            hovertemplate=f"<b>{year}</b><br>{x_title}: %{{x}}<br>Cumulative: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title=x_title, yaxis_title="Cumulative Orders",
        hovermode="x unified", margin=dict(t=30, b=40), legend_title="Year",
    )
    st.plotly_chart(fig, width='stretch')

    # ══════════════════════════════════════════════════════════
    # 2. WEEKLY COMPARISON (years side-by-side by day-of-year)
    # ══════════════════════════════════════════════════════════
    st.subheader("Order Volume — Year Comparison (Same Period)")
    c1, c2 = st.columns([3, 1])
    with c2:
        week_window = st.selectbox("Rolling avg (weeks)", [1, 2, 3, 4], index=0, key="smooth_window", label_visibility="collapsed")
    
    # Colorblind-friendly colors: red and blue
    colors = {available_years[0]: "#d62728", available_years[1]: "#1f77b4"} if len(available_years) >= 2 else {year: ["#d62728", "#1f77b4"][i % 2] for i, year in enumerate(available_years)}
    
    fig2 = go.Figure()
    # First pass: add all lines (aligned by day-of-year)
    for year in available_years:
        yr_df = orders[orders["Year"] == year].copy()
        # Aggregate by day
        daily = yr_df.groupby(yr_df["OPD"].dt.date)["Shipment Weight"].sum().reset_index(name="Orders")
        daily.columns = ["Date", "Orders"]
        daily = daily.sort_values("Date")
        # Calculate day-of-year (1-366) for x-axis alignment
        daily["DayOfYear"] = pd.to_datetime(daily["Date"]).dt.dayofyear
        daily["DateStr"] = pd.to_datetime(daily["Date"]).dt.strftime("%d-%b")
        # Calculate rolling average per week (days in a week = 7)
        daily["Smoothed"] = daily["Orders"].rolling(window=week_window * 7, min_periods=1, center=True).mean()
        fig2.add_trace(go.Scatter(
            x=daily["DayOfYear"], y=daily["Smoothed"],
            mode="lines", name=year, line=dict(width=2, color=colors.get(year, "#1f77b4")),
            customdata=daily["DateStr"],
            hovertemplate="<b>%{customdata}</b><br>" + year + "<br>Avg: %{y:.1f}<extra></extra>",
        ))
    # Second pass: add all dots (on top) with matching colors
    for year in available_years:
        yr_df = orders[orders["Year"] == year].copy()
        daily = yr_df.groupby(yr_df["OPD"].dt.date)["Shipment Weight"].sum().reset_index(name="Orders")
        daily.columns = ["Date", "Orders"]
        daily = daily.sort_values("Date")
        daily["DayOfYear"] = pd.to_datetime(daily["Date"]).dt.dayofyear
        daily["DateStr"] = pd.to_datetime(daily["Date"]).dt.strftime("%d-%b")
        fig2.add_trace(go.Scatter(
            x=daily["DayOfYear"], y=daily["Orders"],
            mode="markers", name=f"{year} (daily)", marker=dict(size=4, opacity=0.5, color=colors.get(year, "#1f77b4")),
            customdata=daily["DateStr"],
            hovertemplate="<b>%{customdata}</b><br>" + year + " (daily)<br>Orders: %{y}<extra></extra>",
            showlegend=False,
        ))

    fig2.update_layout(
        xaxis_title="Day of Year (Jan 1 → Dec 31)", yaxis_title=f"# Orders ({week_window}-week rolling avg)",
        hovermode="x unified", margin=dict(t=30, b=40), legend_title="Year",
    )
    st.plotly_chart(fig2, width='stretch')

    # ══════════════════════════════════════════════════════════
    # 3. FULL TIMELINE (all years continuous, daily detail with week smoothing)
    # ══════════════════════════════════════════════════════════
    st.subheader("Full Timeline — All Years (Continuous)")
    c1_tl, c2_tl = st.columns([3, 1])
    with c2_tl:
        tl_window = st.selectbox("Rolling avg (weeks)", [1, 2, 3, 4], index=0, key="timeline_window", label_visibility="collapsed")
    
    fig3 = go.Figure()
    # First pass: add all lines per year
    for year in available_years:
        yr_df = orders[orders["Year"] == year].copy()
        daily = yr_df.groupby(yr_df["OPD"].dt.date)["Shipment Weight"].sum().reset_index(name="Orders")
        daily.columns = ["Date", "Orders"]
        daily = daily.sort_values("Date")
        daily["DateStr"] = pd.to_datetime(daily["Date"]).dt.strftime("%d-%b-%Y")
        daily["Smoothed"] = daily["Orders"].rolling(window=tl_window * 7, min_periods=1, center=True).mean()
        fig3.add_trace(go.Scatter(
            x=daily["Date"], y=daily["Smoothed"],
            mode="lines", name=year, line=dict(width=2, color=colors_yoy.get(year, "#1f77b4")),
            customdata=daily["DateStr"],
            hovertemplate="<b>%{customdata}</b><br>" + year + "<br>Avg: %{y:.1f}<extra></extra>",
        ))
    # Second pass: add all dots per year
    for year in available_years:
        yr_df = orders[orders["Year"] == year].copy()
        daily = yr_df.groupby(yr_df["OPD"].dt.date)["Shipment Weight"].sum().reset_index(name="Orders")
        daily.columns = ["Date", "Orders"]
        daily = daily.sort_values("Date")
        daily["DateStr"] = pd.to_datetime(daily["Date"]).dt.strftime("%d-%b-%Y")
        fig3.add_trace(go.Scatter(
            x=daily["Date"], y=daily["Orders"],
            mode="markers", name=f"{year} (daily)", marker=dict(size=4, opacity=0.5, color=colors_yoy.get(year, "#1f77b4")),
            customdata=daily["DateStr"],
            hovertemplate="<b>%{customdata}</b><br>" + year + " (daily)<br>Orders: %{y}<extra></extra>",
            showlegend=False,
        ))
    
    fig3.update_layout(
        xaxis_title="Date", yaxis_title=f"# Orders ({tl_window}-week rolling avg)",
        hovermode="x unified", margin=dict(t=30, b=40), legend_title="Year",
    )
    st.plotly_chart(fig3, width='stretch')

    # ══════════════════════════════════════════════════════════
    # 4. HEATMAP — full continuous timeline (Mon–Fri, weekends → Friday)
    # ══════════════════════════════════════════════════════════
    st.subheader("Order Volume Heatmap (Week × Day) — Full Timeline")
    dow_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    if "Order DOW" in orders.columns:
        # Move Saturday/Sunday orders to Friday
        heat_orders = orders.copy()
        heat_orders.loc[heat_orders["Order DOW"].isin(["Saturday", "Sunday"]), "Order DOW"] = "Friday"
        heat_orders["YearWeek"] = heat_orders["Year"] + "-W" + heat_orders["ISOWeek"].astype(str).str.zfill(2)
        heat = heat_orders.groupby(["YearWeek", "Order DOW"])["Shipment Weight"].sum().reset_index(name="Orders")
        if not heat.empty:
            heat_pivot = heat.pivot(index="Order DOW", columns="YearWeek", values="Orders").fillna(0)
            heat_pivot = heat_pivot[sorted(heat_pivot.columns)]
            heat_pivot = heat_pivot.reindex([d for d in dow_weekdays if d in heat_pivot.index])
            fig5 = px.imshow(
                heat_pivot,
                labels=dict(x="Year-Week", y="Day", color="Orders"),
                color_continuous_scale="YlOrRd",
                aspect="auto",
            )
            fig5.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig5, width='stretch')

    # ══════════════════════════════════════════════════════════
    # 5. LEAD TIME TABLE (working days)
    # ══════════════════════════════════════════════════════════
    st.subheader("Lead Time (Working Days: Order Placed → Load Date)")
    if "Order Placed Date" in orders.columns and "Load Date From" in df.columns:
        lt_df = orders[["Shipment No", "Customer Name", "Order Placed Date", "Load Date From"]].dropna().copy()
        if len(lt_df) > 0:
            # Calculate working days (exclude Sat/Sun)
            lt_df["Lead Time (Working Days)"] = lt_df.apply(
                lambda r: np.busday_count(
                    r["Order Placed Date"].date(),
                    r["Load Date From"].date(),
                ), axis=1,
            )
            # Filter out negatives
            lt_df = lt_df[lt_df["Lead Time (Working Days)"] >= 0]

            if len(lt_df) > 0:
                avg_lt = lt_df["Lead Time (Working Days)"].mean()
                med_lt = lt_df["Lead Time (Working Days)"].median()
                c1, c2, c3 = st.columns(3)
                c1.metric("Average Lead Time", f"{avg_lt:.1f} working days")
                c2.metric("Median Lead Time", f"{med_lt:.0f} working days")
                c3.metric("Orders with Lead Time", f"{len(lt_df):,}")

                # Histogram
                lt_vals = lt_df["Lead Time (Working Days)"]
                lt_clipped = lt_vals[lt_vals <= lt_vals.quantile(0.99)]
                fig6 = px.histogram(lt_clipped, nbins=30, labels={"value": "Working Days"})
                fig6.update_layout(
                    xaxis_title="Lead Time (working days)", yaxis_title="# Shipments",
                    showlegend=False, margin=dict(t=20, b=20),
                )
                st.plotly_chart(fig6, width='stretch')

                # Lead time distribution by week
                st.subheader("Lead Time Distribution by Week")
                lt_df["YearWeek"] = lt_df["Order Placed Date"].dt.year.astype(str) + "-W" + lt_df["Order Placed Date"].dt.isocalendar().week.astype(str).str.zfill(2)
                
                # Create lead time buckets (ordered by duration)
                def bucket_leadtime(lt):
                    if lt < 3:
                        return "1. <3 Days"
                    elif lt < 7:
                        return "2. 4-7 Days"
                    elif lt < 14:
                        return "3. 7-14 Days"
                    else:
                        return "4. >14 Days"
                
                lt_df["Bucket"] = lt_df["Lead Time (Working Days)"].apply(bucket_leadtime)
                
                # Pivot: weeks as columns, buckets as rows
                pivot = lt_df.groupby(["Bucket", "YearWeek"]).size().unstack(fill_value=0)
                # Reverse columns to show most recent (latest week) on the left
                pivot = pivot[[c for c in sorted(pivot.columns, reverse=True)]]
                # Add total row
                total_row = pivot.sum()
                pivot.loc["0. Total Orders"] = total_row
                # Add average row
                avg_row = lt_df.groupby("YearWeek")["Lead Time (Working Days)"].mean()
                pivot.loc["5. Average"] = avg_row
                # Sort rows by bucket order
                pivot = pivot.sort_index()
                
                st.dataframe(pivot, width='stretch')
            else:
                st.info("No valid lead time data available.")
    else:
        st.info("Order Placed Date or Load Date From column not available.")
