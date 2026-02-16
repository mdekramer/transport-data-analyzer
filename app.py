import sys
import os

# Ensure the project root is on the path so page imports work
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data
from views import overview, order_intake, customers, geography, operations, new_business, new_business_week, heatmap_comparison

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Transport Analyzer",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global theming (Hoyer-inspired) ─────────────────────────
BRAND_RED = "#E3000F"
TEXT_DARK = "#404040"
TEXT_MUTED = "#555555"
BG_GRAD_TOP = "#ffffff"
BG_GRAD_BOTTOM = "#f9f9fb"

# Plotly defaults
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [BRAND_RED, TEXT_DARK, "#8A8A8A", "#2E86C1", "#17A589"]

st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
      html, body, .stApp {{
        font-family: 'Montserrat', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        color: {TEXT_DARK};
        background: linear-gradient(180deg, {BG_GRAD_TOP} 0%, {BG_GRAD_BOTTOM} 100%);
      }}
      /* Top brand bar */
      .brand-bar {{
        position: sticky; top: 0; z-index: 1000;
        background: {BRAND_RED}; color: #fff; padding: 10px 16px; border-radius: 8px;
        margin-bottom: 8px;
      }}
      .brand-bar .title {{ font-weight: 700; letter-spacing: 0.4px; }}
      /* Sidebar polish */
      section[data-testid='stSidebar'] {{ background: #ffffff; }}
      input[type='radio'], input[type='checkbox'] {{ accent-color: {BRAND_RED}; }}
      .stButton > button {{ background: {BRAND_RED}; color:#fff; border:0; border-radius:6px; }}
      .stButton > button:hover {{ filter: brightness(0.95); }}
      /* Metrics */
      [data-testid='stMetricValue'] {{ color: {BRAND_RED}; }}
    </style>
    <div class="brand-bar"><span class="title">Transport Data Analyzer</span></div>
    """,
    unsafe_allow_html=True,
)

# ── Password Authentication ────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🚛 Transport Data Analyzer - Login")
    st.write("Please enter the password to access the dashboard.")
    
    password_input = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if password_input == "Kara2014+++":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect password. Please try again.")
    
    st.stop()

st.title("🚛 Transport Data Analyzer")

# ── File upload ────────────────────────────────────────────────
with st.sidebar:
    # Move Navigation ABOVE filters per request
    st.header("Navigation")
    # Define pages early for the radio
    PAGES = {
        "📊 Overview": overview,
        "📈 Order Intake": order_intake,
        "👥 Customers": customers,
        "🆕 New Business - Month": new_business,
        "🆕 New Business - Week": new_business_week,
        "🔥 Heatmap Comparison": heatmap_comparison,
        "🌍 Geography": geography,
        "⚙️ Operations": operations,
    }
    page = st.radio("Go to", list(PAGES.keys()), label_visibility="collapsed")

    st.header("Data Source")
    uploaded = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

    # Auto-detect Excel files in the app folder
    app_dir = os.path.dirname(__file__)
    local_files = sorted(
        f for f in os.listdir(app_dir)
        if f.lower().endswith((".xlsx", ".xls")) and not f.startswith("~$")
    )
    selected_local = None
    if local_files and uploaded is None:
        selected_local = st.selectbox(
            "Or pick a file from the folder",
            ["(none)"] + local_files,
            index=1 if len(local_files) == 1 else 0,
        )
        if selected_local == "(none)":
            selected_local = None

if uploaded is not None:
    df_raw = load_data(uploaded)
elif selected_local:
    df_raw = load_data(os.path.join(app_dir, selected_local))
else:
    st.info("👈 Upload an Excel file or pick one from the folder to get started.")
    st.stop()

# Store full unfiltered data in session state for new_business page
st.session_state.df_raw = df_raw

st.sidebar.success(f"Loaded **{len(df_raw):,}** rows, **{len(df_raw.columns)}** columns")

# ── Sidebar filters ──────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # Date range (Order Placed Date)
    if "Order Placed Date" in df_raw.columns:
        valid_dates = df_raw["Order Placed Date"].dropna()
        if len(valid_dates) > 0:
            from datetime import date as _date
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            default_start = max(_date(2025, 1, 1), min_date)
            date_range = st.date_input(
                "Order Placed Date Range",
                value=(default_start, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        else:
            date_range = None
    else:
        date_range = None

    # Customer
    if "Customer Name" in df_raw.columns:
        all_customers = sorted(df_raw["Customer Name"].dropna().unique())
        sel_customers = st.multiselect("Customer Name", all_customers)
    else:
        sel_customers = []

    # Load Country
    if "Load Country" in df_raw.columns:
        all_load_countries = sorted(df_raw["Load Country"].dropna().unique())
        sel_load_countries = st.multiselect("Load Country", all_load_countries)
    else:
        sel_load_countries = []

    # Unload Country
    if "Unload Country" in df_raw.columns:
        all_unload_countries = sorted(df_raw["Unload Country"].dropna().unique())
        sel_unload_countries = st.multiselect("Unload Country", all_unload_countries)
    else:
        sel_unload_countries = []

    # Market
    if "Market" in df_raw.columns:
        all_markets = sorted(df_raw["Market"].dropna().unique())
        sel_markets = st.multiselect("Market", all_markets)
    else:
        sel_markets = []

    # Shipment Status
    if "Shipment Status" in df_raw.columns:
        all_statuses = sorted(df_raw["Shipment Status"].dropna().unique())
        sel_statuses = st.multiselect("Shipment Status", all_statuses)
    else:
        sel_statuses = []

    # Modality
    if "Modality" in df_raw.columns:
        all_modalities = sorted(df_raw["Modality"].dropna().unique())
        sel_modalities = st.multiselect("Modality", all_modalities)
    else:
        sel_modalities = []

    # Business Line
    if "Business Line" in df_raw.columns:
        all_blines = sorted(df_raw["Business Line"].dropna().unique())
        sel_blines = st.multiselect("Business Line", all_blines)
    else:
        sel_blines = []

    # Order Allocation
    if "Order Allocation" in df_raw.columns:
        all_allocs = sorted(df_raw["Order Allocation"].dropna().unique())
        sel_allocs = st.multiselect("Order Allocation", all_allocs)
    else:
        sel_allocs = []

    # Spot / Dedicated
    if "Spot / Dedicated" in df_raw.columns:
        all_spotded = sorted(df_raw["Spot / Dedicated"].dropna().unique())
        sel_spotded = st.multiselect("Spot / Dedicated", all_spotded)
    else:
        sel_spotded = []

    # Order Placed Day
    if "Order Placed Day" in df_raw.columns:
        all_opdays = sorted(df_raw["Order Placed Day"].dropna().astype(str).unique())
        sel_opdays = st.multiselect("Order Placed Day", all_opdays)
    else:
        sel_opdays = []

# ── Apply filters ────────────────────────────────────────────
df = df_raw.copy()

if date_range and len(date_range) == 2 and "Order Placed Date" in df.columns:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[df["Order Placed Date"].between(start, end) | df["Order Placed Date"].isna()]

if sel_customers:
    df = df[df["Customer Name"].isin(sel_customers)]
if sel_load_countries:
    df = df[df["Load Country"].isin(sel_load_countries)]
if sel_unload_countries:
    df = df[df["Unload Country"].isin(sel_unload_countries)]
if sel_markets:
    df = df[df["Market"].isin(sel_markets)]
if sel_statuses:
    df = df[df["Shipment Status"].isin(sel_statuses)]
if sel_modalities:
    df = df[df["Modality"].isin(sel_modalities)]
if sel_blines:
    df = df[df["Business Line"].isin(sel_blines)]
if sel_allocs:
    df = df[df["Order Allocation"].isin(sel_allocs)]
if sel_spotded:
    df = df[df["Spot / Dedicated"].isin(sel_spotded)]
if sel_opdays:
    df = df[df["Order Placed Day"].astype(str).isin(sel_opdays)]

if len(df) == 0:
    st.warning("No data matches the current filters. Adjust the sidebar filters.")
    st.stop()

st.caption(f"Showing **{len(df):,}** of {len(df_raw):,} shipments after filters")

# ── Render page ─────────────────────────────────────────────
PAGES[page].render(df)
