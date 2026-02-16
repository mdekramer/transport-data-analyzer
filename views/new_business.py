import streamlit as st
import pandas as pd
from datetime import timedelta
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("🆕 New Business")

    # Use full unfiltered data from session state for new business analysis
    if "df_raw" not in st.session_state or st.session_state.df_raw is None:
        st.warning("Data not loaded. Please go back and load a file.")
        return
    
    df_full = st.session_state.df_raw.copy()
    
    if "Order Placed Date" not in df_full.columns or "Customer Name" not in df_full.columns:
        st.warning("Missing 'Order Placed Date' or 'Customer Name' columns.")
        return

    # ══════════════════════════════════════════════════════════
    # Month selector
    # ══════════════════════════════════════════════════════════
    df_copy = df_full.copy()
    df_copy["YearMonth"] = df_copy["Order Placed Date"].dt.to_period("M")
    available_months = sorted(df_copy["YearMonth"].unique())
    
    col1, col2 = st.columns([2, 1])
    with col2:
        # Reverse months so most recent is first
        months_reversed = list(reversed(available_months))
        selected_month = st.selectbox(
            "Select Month",
            months_reversed,
            index=0,
            format_func=lambda x: str(x),
            label_visibility="collapsed"
        )
    
    if selected_month is None:
        st.warning("No data available for the selected month.")
        return

    # Get first order date for each customer (across ALL data)
    customer_first_order = (
        df_copy.groupby("Customer Name")["Order Placed Date"]
        .min()
        .reset_index()
    )
    customer_first_order.columns = ["Customer Name", "First Order Date"]

    # Filter to customers whose first order was in the selected month
    selected_month_start = selected_month.to_timestamp()
    selected_month_end = (selected_month + 1).to_timestamp() - timedelta(days=1)
    
    new_customers_in_month = customer_first_order[
        (customer_first_order["First Order Date"] >= selected_month_start) &
        (customer_first_order["First Order Date"] <= selected_month_end)
    ].copy()

    # ══════════════════════════════════════════════════════════
    # 1. NEW CUSTOMERS with first-month orders (30 days from first order)
    # ══════════════════════════════════════════════════════════
    st.subheader(f"🆕 New Customers — {selected_month}")

    if len(new_customers_in_month) > 0:
        new_customers_in_month = new_customers_in_month.sort_values("First Order Date", ascending=False)
        
        # Calculate orders in first 30 days from first order
        first_month_orders = []
        for _, row in new_customers_in_month.iterrows():
            cust = row["Customer Name"]
            first_date = row["First Order Date"]
            cutoff = first_date + timedelta(days=30)
            orders_count = df_copy[
                (df_copy["Customer Name"] == cust) &
                (df_copy["Order Placed Date"] >= first_date) &
                (df_copy["Order Placed Date"] <= cutoff)
            ]["Shipment Weight"].sum()
            first_month_orders.append(orders_count)
        
        new_customers_in_month["Orders (First 30 Days)"] = first_month_orders
        new_customers_in_month["First Order Date"] = new_customers_in_month["First Order Date"].dt.strftime("%d-%b-%Y")
        
        display_cols = ["Customer Name", "First Order Date", "Orders (First 30 Days)"]
        st.dataframe(new_customers_in_month[display_cols], use_container_width=True, hide_index=True)
        st.caption(f"**{len(new_customers_in_month)}** new customers in {selected_month}")
    else:
        st.info(f"No new customers in {selected_month}.")

    st.divider()

    # ══════════════════════════════════════════════════════════
    # 2. NEW BUSINESS LANES (clustered by customer, expandable)
    # ══════════════════════════════════════════════════════════
    st.subheader(f"🆕 New Business Lanes — {selected_month}")

    if "Load City" in df_copy.columns and "Unload City" in df_copy.columns:
        # Create lane identifier
        df_lanes = df_copy.copy()
        df_lanes["Lane"] = (
            df_lanes["Customer Name"].fillna("") + " | " +
            df_lanes["Load City"].fillna("") + " → " +
            df_lanes["Unload City"].fillna("")
        )

        # Get first order date for each lane
        lane_first_order = (
            df_lanes.groupby("Lane")["Order Placed Date"]
            .min()
            .reset_index()
        )
        lane_first_order.columns = ["Lane", "First Order Date"]

        # Filter to lanes with first order in selected month
        new_lanes = lane_first_order[
            (lane_first_order["First Order Date"] >= selected_month_start) &
            (lane_first_order["First Order Date"] <= selected_month_end)
        ].copy()

        if len(new_lanes) > 0:
            # Extract customer name from lane
            new_lanes["Customer Name"] = new_lanes["Lane"].str.split(r" \| ").str[0]
            
            # Calculate orders in first 30 days per lane
            lane_first_month_orders = []
            for _, row in new_lanes.iterrows():
                lane = row["Lane"]
                first_date = row["First Order Date"]
                cutoff = first_date + timedelta(days=30)
                orders_count = df_lanes[
                    (df_lanes["Lane"] == lane) &
                    (df_lanes["Order Placed Date"] >= first_date) &
                    (df_lanes["Order Placed Date"] <= cutoff)
                ]["Shipment Weight"].sum()
                lane_first_month_orders.append(orders_count)
            
            new_lanes["Orders (First 30 Days)"] = lane_first_month_orders
            
            # Group by customer and display with collapsible sections
            # Calculate total orders per customer for sorting
            customer_totals = new_lanes.groupby("Customer Name")["Orders (First 30 Days)"].sum().sort_values(ascending=False)
            customers_with_lanes = customer_totals.index.tolist()
            total_new_lanes = len(new_lanes)
            
            for cust in customers_with_lanes:
                cust_lanes = new_lanes[new_lanes["Customer Name"] == cust].sort_values("First Order Date", ascending=False)
                total_lane_orders = cust_lanes["Orders (First 30 Days)"].sum()
                
                with st.expander(f"📦 **{cust}** — {len(cust_lanes)} lane(s), {total_lane_orders} order(s)"):
                    # Build table for lanes under this customer
                    lanes_table = []
                    for _, lane_row in cust_lanes.iterrows():
                        lane_parts = lane_row["Lane"].split(" | ")
                        if len(lane_parts) >= 2:
                            route = lane_parts[1]
                        else:
                            route = ""
                        lanes_table.append({
                            "Route": route,
                            "First Order Date": lane_row["First Order Date"].strftime("%d-%b-%Y"),
                            "Orders (First 30 Days)": lane_row["Orders (First 30 Days)"]
                        })
                    
                    lanes_df = pd.DataFrame(lanes_table)
                    st.dataframe(lanes_df, use_container_width=True, hide_index=True)
            
            st.caption(f"**{len(customers_with_lanes)}** new customer(s) with **{total_new_lanes}** new lane(s)")
        else:
            st.info(f"No new business lanes in {selected_month}.")
    else:
        st.warning("Missing 'Load City' or 'Unload City' columns.")
