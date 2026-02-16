import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("🔥 Treemap Comparison")

    # Use full unfiltered data from session state
    if "df_raw" not in st.session_state or st.session_state.df_raw is None:
        st.warning("Data not loaded. Please go back and load a file.")
        return
    
    df_full = st.session_state.df_raw.copy()
    
    if "Order Placed Date" not in df_full.columns or "Customer Name" not in df_full.columns:
        st.warning("Missing 'Order Placed Date' or 'Customer Name' columns.")
        return
    
    if "Business Line" not in df_full.columns:
        st.warning("Missing 'Business Line' column.")
        return

    # ══════════════════════════════════════════════════════════
    # Get available months (exclude NaT)
    # ══════════════════════════════════════════════════════════
    df_full["YearMonth"] = df_full["Order Placed Date"].dt.to_period("M")
    available_months = sorted(
        [m for m in df_full["YearMonth"].unique() if pd.notna(m)],
        reverse=True
    )
    
    if len(available_months) < 2:
        st.warning("Not enough data to compare. Need at least 2 months.")
        return

    # ══════════════════════════════════════════════════════════
    # Month selectors with two columns
    # ══════════════════════════════════════════════════════════
    # Initialize session state
    if "hm_main_month" not in st.session_state:
        st.session_state.hm_main_month = available_months[1] if len(available_months) > 1 else available_months[0]
    if "hm_compare_month" not in st.session_state:
        st.session_state.hm_compare_month = available_months[0]
    
    col_left, col_right = st.columns(2)
    
    def format_month(period):
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return months[period.month - 1]
    
    # Group months by year
    months_by_year = {}
    for month in available_months:
        year = month.year
        if year not in months_by_year:
            months_by_year[year] = []
        months_by_year[year].append(month)
    
    # Limit to max 3 years
    all_years = sorted(months_by_year.keys(), reverse=True)
    years_to_show = all_years[:3]
    
    with col_left:
        st.write("**Compare Against**")
        for year in sorted(years_to_show, reverse=True):
            year_months = months_by_year[year]
            # 6 columns = 2 rows of months per year
            year_cols = st.columns(6)
            for idx, month in enumerate(year_months):
                with year_cols[idx % 6]:
                    is_selected = st.session_state.hm_compare_month == month
                    icon = "✓" if is_selected else "○"
                    label = f"{icon} {format_month(month)} {year}"
                    
                    if st.button(label, key=f"btn_compare_{year}_{month.month}", use_container_width=False):
                        st.session_state.hm_compare_month = month
    
    with col_right:
        st.write("**Main Month**")
        for year in sorted(years_to_show, reverse=True):
            year_months = months_by_year[year]
            # 6 columns = 2 rows of months per year
            year_cols = st.columns(6)
            for idx, month in enumerate(year_months):
                with year_cols[idx % 6]:
                    is_selected = st.session_state.hm_main_month == month
                    icon = "✓" if is_selected else "○"
                    label = f"{icon} {format_month(month)} {year}"
                    
                    if st.button(label, key=f"btn_main_{year}_{month.month}", use_container_width=False):
                        st.session_state.hm_main_month = month
    
    selected_month1 = st.session_state.hm_main_month
    selected_month2 = st.session_state.hm_compare_month
    
    st.divider()
    st.write(f"**Comparing: {selected_month1} (Main) vs {selected_month2} (Compare Against)**")

    # ══════════════════════════════════════════════════════════
    # Prepare data for treemaps
    # ══════════════════════════════════════════════════════════
    month1_start = selected_month1.to_timestamp()
    month1_end = (selected_month1 + 1).to_timestamp() - timedelta(days=1)
    
    month2_start = selected_month2.to_timestamp()
    month2_end = (selected_month2 + 1).to_timestamp() - timedelta(days=1)
    
    df_m1 = df_full[
        (df_full["Order Placed Date"] >= month1_start) &
        (df_full["Order Placed Date"] <= month1_end)
    ].copy()
    
    df_m2 = df_full[
        (df_full["Order Placed Date"] >= month2_start) &
        (df_full["Order Placed Date"] <= month2_end)
    ].copy()
    
    # ══════════════════════════════════════════════════════════
    # Build treemap data with Business Line → Customer hierarchy
    # ══════════════════════════════════════════════════════════
    def prepare_treemap_data(df_month):
        treemap_data = []
        
        for bline in sorted(df_month["Business Line"].dropna().unique()):
            df_bline = df_month[df_month["Business Line"] == bline]
            
            # Get top 15 customers for this business line (by weighted shipments)
            top_customers = (
                df_bline.groupby("Customer Name")["Shipment Weight"]
                .sum()
                .nlargest(15)
                .index.tolist()
            )
            
            # Add top customers
            for cust in top_customers:
                count = df_bline[df_bline["Customer Name"] == cust]["Shipment Weight"].sum()
                treemap_data.append({
                    "Business Line": bline,
                    "Customer": cust,
                    "Orders": count
                })
            
            # Add "Others" for remaining customers
            others_count = df_bline[~df_bline["Customer Name"].isin(top_customers)]["Shipment Weight"].sum()
            if others_count > 0:
                treemap_data.append({
                    "Business Line": bline,
                    "Customer": "Others",
                    "Orders": others_count
                })
        
        return pd.DataFrame(treemap_data)
    
    df_tree_m1 = prepare_treemap_data(df_m1)
    df_tree_m2 = prepare_treemap_data(df_m2)

    # ══════════════════════════════════════════════════════════
    # Merge data for comparison and create single treemap
    # ══════════════════════════════════════════════════════════
    # Filter out business lines with "-"
    df_tree_m1 = df_tree_m1[df_tree_m1["Business Line"] != "-"].copy()
    df_tree_m2 = df_tree_m2[df_tree_m2["Business Line"] != "-"].copy()
    
    # Swap naming: Main month is base, Compare Against is for delta
    df_base_merged = df_tree_m1.rename(columns={"Orders": "Orders_Base"})
    df_compare_merged = df_tree_m2.rename(columns={"Orders": "Orders_Compare"})
    
    df_comparison = pd.merge(
        df_base_merged, df_compare_merged,
        on=["Business Line", "Customer"], how="outer"
    )
    df_comparison["Orders_Base"] = df_comparison["Orders_Base"].fillna(0).astype(int)
    df_comparison["Orders_Compare"] = df_comparison["Orders_Compare"].fillna(0).astype(int)
    # Difference = Base - Compare (Main month as base)
    df_comparison["Difference"] = df_comparison["Orders_Base"] - df_comparison["Orders_Compare"]
    df_comparison["Pct_Change"] = (
        (df_comparison["Difference"] / df_comparison["Orders_Base"] * 100)
        .where(df_comparison["Orders_Base"] > 0, 0)
    ).round(1)
    
    # Use max of both months for sizing so all customers are visible
    df_comparison["Size"] = df_comparison[["Orders_Base", "Orders_Compare"]].max(axis=1).clip(lower=1)
    
    # Calculate business line aggregates
    bline_agg = df_comparison.groupby("Business Line").agg({
        "Orders_Base": "sum",
        "Orders_Compare": "sum",
        "Difference": "sum"
    }).reset_index()
    bline_agg["Pct_Change"] = (
        (bline_agg["Difference"] / bline_agg["Orders_Base"] * 100)
        .where(bline_agg["Orders_Base"] > 0, 0)
    ).round(1)
    
    # Build hover text for customers
    selected_month1 = st.session_state.hm_main_month
    selected_month2 = st.session_state.hm_compare_month
    
    df_comparison["HoverText"] = df_comparison.apply(
        lambda row: (
            f"{selected_month1} (Main): {row['Orders_Base']} orders<br>"
            f"{selected_month2} (Compare): {row['Orders_Compare']} orders<br>"
            f"Change: {row['Difference']:+d} orders ({row['Pct_Change']:+.1f}%)"
        ), axis=1
    )
    
    # Business line hover text
    bline_hover_map = {}
    for _, row in bline_agg.iterrows():
        bline_hover_map[row["Business Line"]] = (
            f"{selected_month1} (Main): {int(row['Orders_Base'])} orders<br>"
            f"{selected_month2} (Compare): {int(row['Orders_Compare'])} orders<br>"
            f"Change: {int(row['Difference']):+d} orders ({row['Pct_Change']:+.1f}%)"
        )
    df_comparison["BLineHover"] = df_comparison["Business Line"].map(bline_hover_map)
    
    # ══════════════════════════════════════════════════════════
    # Display single treemap
    # ══════════════════════════════════════════════════════════
    if len(df_comparison) > 0:
        fig = px.treemap(
            df_comparison,
            path=["Business Line", "Customer"],
            values="Size",
            color="Difference",
            color_continuous_scale=[
                [0.0, "#d62728"],   # Red for negative (colorblind-safe)
                [0.5, "#f0f0f0"],   # Light gray for neutral
                [1.0, "#2ca02c"]    # Green for positive (colorblind-safe)
            ],
            color_continuous_midpoint=0,
            custom_data=["HoverText", "BLineHover"],
            title=f"Order Volume Comparison: {selected_month1} vs {selected_month2}",
        )
        
        fig.update_traces(
            textposition="middle center",
        )
        
        # Show customer data for customers (HoverText)
        fig.data[0].customdata = df_comparison[["HoverText", "BLineHover"]].values
        fig.data[0].hovertemplate = (
            "<b>%{label}</b><br>"
            "%{customdata[0]}<extra></extra>"
        )
        
        fig.update_layout(
            height=700,
            margin=dict(t=80, b=20, l=20, r=20),
            coloraxis_colorbar=dict(title="Order<br>Change"),
        )
        
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No data to display for the selected months.")

    # ══════════════════════════════════════════════════════════
    # Summary statistics
    # ══════════════════════════════════════════════════════════
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_m1 = df_tree_m1["Orders"].sum() if len(df_tree_m1) > 0 else 0
        st.metric(f"Total Orders — {selected_month1}", int(total_m1))
    
    with col2:
        total_m2 = df_tree_m2["Orders"].sum() if len(df_tree_m2) > 0 else 0
        st.metric(f"Total Orders — {selected_month2}", int(total_m2))
    
    with col3:
        change = total_m2 - total_m1
        pct_change = (change / total_m1 * 100) if total_m1 > 0 else 0
        st.metric("Month-over-Month Change", f"{int(change):+d}", f"{pct_change:+.1f}%")
