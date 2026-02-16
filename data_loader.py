import pandas as pd
import streamlit as st

# Excel serial date columns that need conversion
SERIAL_DATE_COLS = [
    "Load Date From",
    "Load Date Till",
    "Unload Date From",
    "Unload Date Till",
    "Order Placed Date",
    "Order Load Date",
    "Order Unload Date",
    "Cancelation Date",
]

# Numeric columns that may contain '-' as missing
NUMERIC_COLS = [
    "Weight",
    "Quote",
    "Total KM",
    "Full KM",
    "Empty KM",
    "Product Specific Gravity",
    "TC Total Capacity",
    "TC Volume",
    "TC Length",
    "# of Compartments",
]


def _convert_serial_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Excel serial number columns to proper datetime.
    
    Handles both Excel serial numbers and proper datetime objects.
    """
    # pandas Timedelta maxes out at ~106,752 days (nanosecond precision),
    # so we must discard anything beyond a reasonable range BEFORE converting.
    # Serial 1 = 1900-01-01, Serial 73050 = 2099-12-31.
    MIN_SERIAL = 1
    MAX_SERIAL = 73050  # year 2099 — well within pandas bounds

    for col in SERIAL_DATE_COLS:
        if col in df.columns:
            # First, try to convert to datetime directly (in case it's already a datetime)
            df[col] = pd.to_datetime(df[col], errors="coerce")
            
            # If that didn't work (all NaT), try serial conversion on numeric values
            if df[col].isna().all():
                numeric = pd.to_numeric(df[col], errors="coerce")
                # NaN-out anything outside [1, 73050]; keeps NaN as NaN
                numeric = numeric.where(numeric.between(MIN_SERIAL, MAX_SERIAL))
                # Convert using pd.to_datetime — NOT timedelta arithmetic
                df[col] = pd.to_datetime(
                    numeric, unit="D", origin="1899-12-30", errors="coerce"
                )
    return df


def _clean_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce numeric columns, replacing '-' and blanks with NaN."""
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _add_shipment_weight(df: pd.DataFrame) -> pd.DataFrame:
    """Add shipment weight column based on Step Business Name.
    
    1-Step Business = 1.0 (full count)
    All others = 0.5 (half count)
    """
    if "Step Business Name" in df.columns:
        df["Shipment Weight"] = df["Step Business Name"].apply(
            lambda x: 1.0 if (isinstance(x, str) and "1-Step Business" in x) else 0.5
        )
    else:
        # Default to 1.0 if column doesn't exist (backward compatibility)
        df["Shipment Weight"] = 1.0
    return df


def _derive_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived helper columns."""
    if "Order Placed Date" in df.columns and "Load Date From" in df.columns:
        df["Lead Time Days"] = (
            df["Load Date From"] - df["Order Placed Date"]
        ).dt.total_seconds() / 86400

    if "Load Date From" in df.columns:
        df["Load Date"] = df["Load Date From"].dt.normalize()
        df["Load Week"] = df["Load Date From"].dt.isocalendar().week.astype("Int64")
        df["Load DOW"] = df["Load Date From"].dt.day_name()
        df["Load Month Name"] = df["Load Date From"].dt.strftime("%Y-%m")

    if "Order Placed Date" in df.columns:
        df["Order Date"] = df["Order Placed Date"].dt.normalize()
        df["Order Week"] = (
            df["Order Placed Date"].dt.isocalendar().week.astype("Int64")
        )
        df["Order DOW"] = df["Order Placed Date"].dt.day_name()
        df["Order Month Name"] = df["Order Placed Date"].dt.strftime("%Y-%m")

    if "Full KM" in df.columns and "Total KM" in df.columns:
        df["KM Utilization %"] = (
            df["Full KM"] / df["Total KM"].replace(0, pd.NA) * 100
        )

    if "Load Country" in df.columns and "Unload Country" in df.columns:
        df["Route"] = df["Load Country"] + " → " + df["Unload Country"]

    return df


def count_weighted_shipments(df: pd.DataFrame, by_column=None):
    """Count shipments using Shipment Weight column.
    
    If by_column is None, returns total weighted count.
    If by_column is specified, returns Series grouped by that column.
    """
    if by_column is None:
        return df["Shipment Weight"].sum()
    else:
        return df.groupby(by_column)["Shipment Weight"].sum()


@st.cache_data(show_spinner="Loading Excel data…")
def load_data(file) -> pd.DataFrame:
    """Load and clean an Excel file, returning a processed DataFrame."""
    df = pd.read_excel(file, sheet_name=0, engine="openpyxl")
    df = _convert_serial_dates(df)
    df = _clean_numeric(df)
    df = _add_shipment_weight(df)
    df = _derive_columns(df)
    return df
