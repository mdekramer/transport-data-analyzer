import streamlit as st
import pandas as pd
from datetime import timedelta
from data_loader import count_weighted_shipments


def render(df: pd.DataFrame):
    st.header("🆕 New Business - Week")

    # Use full unfiltered data from session state for new business analysis
    if "df_raw" not in st.session_state or st.session_state.df_raw is None:
        st.warning("Data not loaded. Please go back and load a file.")
        return
    
    df_full = st.session_state.df_raw.copy()
    
    if "Order Placed Date" not in df_full.columns or "Customer Name" not in df_full.columns:
        st.warning("Missing 'Order Placed Date' or 'Customer Name' columns.")
        return

    # ══════════════════════════════════════════════════════════
    # Week selector (ISO week: Mon-Sun)
    # ══════════════════════════════════════════════════════════
    df_copy = df_full.copy()
    df_copy["Date"] = df_copy["Order Placed Date"].dt.date
    df_copy["ISOWeek"] = df_copy["Order Placed Date"].dt.isocalendar().week
    df_copy["Year"] = df_copy["Order Placed Date"].dt.year.astype("Int64")  # Int64 nullable type handles NaN
    df_copy["YearWeek"] = df_copy["Year"].astype(str) + "-W" + df_copy["ISOWeek"].astype(str).str.zfill(2)
    
    available_weeks = sorted(df_copy["YearWeek"].unique())
    
    col1, col2 = st.columns([2, 1])
    with col2:
        # Reverse weeks so most recent is first
        weeks_reversed = list(reversed(available_weeks))
        selected_week = st.selectbox(
            "Select Week",
            weeks_reversed,
            index=0,
            format_func=lambda x: str(x),
            label_visibility="collapsed"
        )
    
    if selected_week is None:
        st.warning("No data available for the selected week.")
        return

    # Extract year and week number from YearWeek string
    selected_year, selected_week_num = selected_week.split("-W")
    selected_year = int(selected_year)
    selected_week_num = int(selected_week_num)
    
    # Get first order date for each customer (across ALL data)
    customer_first_order = (
        df_copy.groupby("Customer Name")["Order Placed Date"]
        .min()
        .reset_index()
    )
    customer_first_order.columns = ["Customer Name", "First Order Date"]

    # Filter to customers whose first order was in the selected week
    # ISO week starts on Monday and ends on Sunday
    selected_week_start = pd.Timestamp(year=selected_year, month=1, day=4).isocalendar()[0]
    # Calculate the Monday of the selected week
    first_day_of_year = pd.Timestamp(year=selected_year, month=1, day=1)
    # Find Monday of week 1
    days_to_monday = (7 - first_day_of_year.dayofweek) % 7
    if days_to_monday == 0 and first_day_of_year.dayofweek != 0:
        days_to_monday = 7
    monday_week_1 = first_day_of_year + timedelta(days=days_to_monday)
    # Monday of selected week
    selected_week_monday = monday_week_1 + timedelta(weeks=selected_week_num - 1)
    selected_week_sunday = selected_week_monday + timedelta(days=6)
    
    new_customers_in_week = customer_first_order[
        (customer_first_order["First Order Date"] >= selected_week_monday) &
        (customer_first_order["First Order Date"] <= selected_week_sunday)
    ].copy()

    # ══════════════════════════════════════════════════════════
    # 1. NEW CUSTOMERS with first-week orders (7 days from first order)
    # ══════════════════════════════════════════════════════════
    st.subheader(f"🆕 New Customers — {selected_week}")

    if len(new_customers_in_week) > 0:
        new_customers_display = new_customers_in_week.sort_values("First Order Date", ascending=False).copy()
        
        # Calculate orders in first 7 days from first order
        first_week_orders = []
        for _, row in new_customers_display.iterrows():
            cust = row["Customer Name"]
            first_date = row["First Order Date"]
            cutoff = first_date + timedelta(days=7)
            orders_count = df_copy[
                (df_copy["Customer Name"] == cust) &
                (df_copy["Order Placed Date"] >= first_date) &
                (df_copy["Order Placed Date"] <= cutoff)
            ]["Shipment Weight"].sum()
            first_week_orders.append(orders_count)
        
        new_customers_display["Orders (First 7 Days)"] = first_week_orders
        new_customers_display["First Order Date"] = new_customers_display["First Order Date"].dt.strftime("%d-%b-%Y")
        
        display_cols = ["Customer Name", "First Order Date", "Orders (First 7 Days)"]
        st.dataframe(new_customers_display[display_cols], use_container_width=True, hide_index=True)
        st.caption(f"**{len(new_customers_display)}** new customers in {selected_week}")
    else:
        st.info(f"No new customers in {selected_week}.")

    st.divider()

    # ══════════════════════════════════════════════════════════
    # 2. NEW BUSINESS LANES (clustered by customer, expandable)
    # ══════════════════════════════════════════════════════════
    st.subheader(f"🆕 New Business Lanes — {selected_week}")

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

        # Filter to lanes with first order in selected week
        new_lanes = lane_first_order[
            (lane_first_order["First Order Date"] >= selected_week_monday) &
            (lane_first_order["First Order Date"] <= selected_week_sunday)
        ].copy()

        if len(new_lanes) > 0:
            # Extract customer name from lane
            new_lanes["Customer Name"] = new_lanes["Lane"].str.split(r" \| ").str[0]
            
            # Mark which lanes belong to new customers
            new_customer_names = set(new_customers_in_week["Customer Name"].tolist()) if len(new_customers_in_week) > 0 else set()
            new_lanes["Is New Customer"] = new_lanes["Customer Name"].isin(new_customer_names)
            
            # Calculate orders in first 7 days per lane
            lane_first_week_orders = []
            for _, row in new_lanes.iterrows():
                lane = row["Lane"]
                first_date = row["First Order Date"]
                cutoff = first_date + timedelta(days=7)
                orders_count = df_lanes[
                    (df_lanes["Lane"] == lane) &
                    (df_lanes["Order Placed Date"] >= first_date) &
                    (df_lanes["Order Placed Date"] <= cutoff)
                ]["Shipment Weight"].sum()
                lane_first_week_orders.append(orders_count)
            
            new_lanes["Orders (First 7 Days)"] = lane_first_week_orders
            
            # Group by customer and display with collapsible sections
            # Calculate total orders per customer for sorting
            customer_totals = new_lanes.groupby("Customer Name")["Orders (First 7 Days)"].sum().sort_values(ascending=False)
            customers_with_lanes = customer_totals.index.tolist()
            total_new_lanes = len(new_lanes)
            new_customer_lanes = len(new_lanes[new_lanes["Is New Customer"]])
            existing_customer_lanes = total_new_lanes - new_customer_lanes
            
            for cust in customers_with_lanes:
                cust_lanes = new_lanes[new_lanes["Customer Name"] == cust].sort_values("First Order Date", ascending=False)
                total_lane_orders = cust_lanes["Orders (First 7 Days)"].sum()
                is_new = cust_lanes["Is New Customer"].iloc[0]
                badge = "🆕 NEW" if is_new else "➕ EXISTING"
                
                with st.expander(f"📦 **{cust}** {badge} — {len(cust_lanes)} lane(s), {total_lane_orders:.1f} order(s)"):
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
                            "Orders (First 7 Days)": lane_row["Orders (First 7 Days)"]
                        })
                    
                    lanes_df = pd.DataFrame(lanes_table)
                    st.dataframe(lanes_df, use_container_width=True, hide_index=True)
            
            st.caption(f"**{total_new_lanes}** total new lanes | **{new_customer_lanes}** from new customers | **{existing_customer_lanes}** from existing customers")
        else:
            st.info(f"No new business lanes in {selected_week}.")
    else:
        st.warning("Missing 'Load City' or 'Unload City' columns.")
