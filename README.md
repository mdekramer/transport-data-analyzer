# 🚛 Transport Data Analyzer

A comprehensive Streamlit dashboard for analyzing transport/shipment data with interactive visualizations, customer insights, and year-over-year comparisons.

## Features

- **Overview Dashboard**: KPI cards, shipment status breakdown, spot vs dedicated analysis
- **Order Intake**: Year-over-year comparisons, day-of-year analysis, full timeline tracking, lead time distribution
- **Customer Analysis**: Top customers by shipment count, customer volume trends, business line breakdown
- **New Business**: Track new customers and new business lanes by month
- **Treemap Comparison**: Compare order volumes across business lines and customers between two months
- **Geography**: Country volumes, top routes, region analysis
- **Operations**: KM utilization, weight distribution, carrier and modality breakdowns

## Prerequisites

- Python 3.8+
- Streamlit
- pandas, plotly, openpyxl, numpy

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Locally

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

## Deployment on Streamlit Cloud

1. Push this repository to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app" and select this repository
4. Set the main file path to `app.py`
5. Configure secrets (if needed) in the Cloud dashboard

## Password

The app is protected with a password. Contact the administrator for access credentials.

## Data Format

Upload Excel files with the following expected columns:
- Order Placed Date
- Customer Name
- Load Country, Unload Country
- Market, Business Line
- Shipment Status, Modality
- Order Allocation
- Spot / Dedicated
- Weight
- Load City, Unload City
- And other transport-related metrics

## Project Structure

```
.
├── app.py                          # Main entry point
├── data_loader.py                  # Data loading and processing
├── requirements.txt                # Python dependencies
├── .streamlit/config.toml          # Streamlit configuration
├── views/
│   ├── overview.py                # Overview dashboard
│   ├── order_intake.py             # Order analysis
│   ├── customers.py                # Customer insights
│   ├── new_business.py             # New business tracking
│   ├── heatmap_comparison.py       # Treemap comparison
│   ├── geography.py                # Geographic analysis
│   └── operations.py               # Operations metrics
└── README.md                       # This file
```

## License

Proprietary - Internal Use Only
