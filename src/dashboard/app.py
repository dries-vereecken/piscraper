#!/usr/bin/env python3
"""
Pilates Bookings Dashboard
A Streamlit-based dashboard for visualizing pilates class booking data from the silver layer.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timezone, timedelta
import numpy as np
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Pilates Bookings Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Set Arial font for the entire app */
    html, body, [class*="css"] {
        font-family: Arial, sans-serif !important;
    }
    
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 0.25rem solid #ff6b6b;
    }
    .stMetric > label {
        font-size: 14px !important;
        font-weight: 600 !important;
        font-family: Arial, sans-serif !important;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
        font-family: Arial, sans-serif !important;
    }
    
    /* Remove default Streamlit fonts */
    .stApp {
        font-family: Arial, sans-serif !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: Arial, sans-serif !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Tighter spacing for sidebar elements */
    .stSidebar .element-container {
        margin-bottom: 0.5rem !important;
    }
    
    /* Compact checkbox styling */
    .stSidebar .stCheckbox > label {
        display: flex;
        align-items: center;
        padding: 0.1rem 0 !important;
        font-weight: 500;
        margin-bottom: 0.2rem !important;
    }
    
    /* Compact button styling */
    .stSidebar .stButton > button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
        padding: 0.25rem 0.5rem !important;
        margin-bottom: 0.2rem !important;
    }
    
    /* Reduce header spacing */
    .stSidebar h3 {
        margin-top: 1rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Reduce container padding */
    .stSidebar .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    
    /* Compact date input */
    .stSidebar .stDateInput > div {
        margin-bottom: 0.3rem !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_database_connection():
    """Get database connection with caching."""
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        st.error("DATABASE_URL not found in environment variables")
        st.stop()
    return DATABASE_URL

@st.cache_data(ttl=300)
def load_silver_data(start_date, end_date, sources=None):
    """Load data from silver layer with filters."""
    DATABASE_URL = get_database_connection()
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            # Build WHERE conditions
            where_conditions = ["start_ts BETWEEN %s AND %s"]
            params = [start_date, end_date]
            
            if sources and len(sources) > 0:
                where_conditions.append("source = ANY(%s)")
                params.append(sources)
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
                SELECT *
                FROM silver_classes
                WHERE {where_clause}
                ORDER BY start_ts DESC
            """
            
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                data = cur.fetchall()
                
            return pd.DataFrame(data) if data else pd.DataFrame()
            
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_available_sources():
    """Get all available sources from the database."""
    DATABASE_URL = get_database_connection()
    
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT source
                    FROM silver_classes
                    WHERE source NOT ILIKE '%test%'
                    ORDER BY source
                """)
                sources = [row[0] for row in cur.fetchall()]
                return sources
    except Exception as e:
        st.error(f"Error fetching sources: {e}")
        return []

def calculate_fill_percentage(capacity, spots_available):
    """Calculate class fill percentage.
    
    Note: spots_available actually means 'spots booked' in our data schema.
    capacity = total spots in class
    spots_available = spots that are booked (not available)
    """
    if pd.isna(capacity) or capacity == 0:
        return None
    if pd.isna(spots_available):
        return None
    
    # spots_available is actually spots_booked
    spots_booked = spots_available
    return (spots_booked / capacity) * 100

def calculate_booking_metrics(df):
    """Calculate booking metrics for KPI cards."""
    if df.empty:
        return {
            'total_classes': 0,
            'avg_fill_rate': 0,
            'fully_booked_pct': 0,
            'cancelled_pct': 0
        }
    
    # Calculate fill rates
    df = df.copy()  # Avoid SettingWithCopyWarning
    df['fill_percentage'] = df.apply(
        lambda row: calculate_fill_percentage(row['capacity'], row['spots_available']), 
        axis=1
    )
    
    valid_fill_rates = df['fill_percentage'].dropna()
    
    return {
        'total_classes': len(df),
        'avg_fill_rate': valid_fill_rates.mean() if len(valid_fill_rates) > 0 else 0,
        'fully_booked_pct': (valid_fill_rates >= 100).sum() / len(valid_fill_rates) * 100 if len(valid_fill_rates) > 0 else 0,
        'cancelled_pct': df['is_cancelled'].sum() / len(df) * 100 if len(df) > 0 else 0
    }

def create_revenue_chart(df):
    """Create daily and cumulative revenue chart."""
    if df.empty:
        return go.Figure()
    
    # For demo purposes, assign estimated revenue per class
    # You can adjust these values based on actual pricing
    revenue_per_class = {
        'coolcharm': 25,
        'koepel': 20,
        'rite': 30,
        'rowreformer': 28
    }
    
    # Calculate revenue
    # Note: spots_available actually means spots_booked in our schema
    df = df.copy()  # Avoid SettingWithCopyWarning
    df['revenue'] = df.apply(
        lambda row: (row['spots_available'] if pd.notna(row['spots_available']) else 0) * 
                   revenue_per_class.get(row['source'], 25), axis=1
    )
    
    # Group by date and source
    df['date'] = pd.to_datetime(df['start_ts']).dt.date
    daily_revenue = df.groupby(['date', 'source'])['revenue'].sum().reset_index()
    
    # Create subplot with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add daily revenue bars by source
    sources = daily_revenue['source'].unique()
    colors = px.colors.qualitative.Set3[:len(sources)]
    
    for i, source in enumerate(sources):
        source_data = daily_revenue[daily_revenue['source'] == source]
        fig.add_trace(
            go.Bar(
                x=source_data['date'],
                y=source_data['revenue'],
                name=source.title(),
                marker_color=colors[i],
                opacity=0.8
            ),
            secondary_y=False
        )
    
    # Add cumulative revenue line
    cumulative_daily = daily_revenue.groupby('date')['revenue'].sum().cumsum().reset_index()
    fig.add_trace(
        go.Scatter(
            x=cumulative_daily['date'],
            y=cumulative_daily['revenue'],
            mode='lines+markers',
            name='Cumulative Revenue',
            line=dict(color='black', width=3),
            marker=dict(size=6)
        ),
        secondary_y=True
    )
    
    # Update layout
    fig.update_layout(
        title="Daily and Cumulative Revenue (Estimated)",
        xaxis_title="Date",
        barmode='stack',
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Arial"),
        autosize=True
    )
    
    fig.update_yaxes(title_text="Daily Revenue (€)", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative Revenue (€)", secondary_y=True)
    
    return fig

def create_fill_heatmap(df, source=None):
    """Create heatmap showing class fill percentages by day and hour."""
    if df.empty:
        return go.Figure()
    
    # Filter by source if specified
    if source and source != "All":
        df = df[df['source'] == source]
    
    # Calculate fill percentages
    df = df.copy()  # Avoid SettingWithCopyWarning
    df['fill_percentage'] = df.apply(
        lambda row: calculate_fill_percentage(row['capacity'], row['spots_available']), 
        axis=1
    )
    
    # Extract day of week and hour
    df['datetime'] = pd.to_datetime(df['start_ts'])
    df['day_of_week'] = df['datetime'].dt.day_name()
    df['hour'] = df['datetime'].dt.hour
    
    # Create pivot table
    heatmap_data = df.groupby(['day_of_week', 'hour'])['fill_percentage'].mean().reset_index()
    pivot_data = heatmap_data.pivot(index='day_of_week', columns='hour', values='fill_percentage')
    
    # Reorder days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot_data = pivot_data.reindex(day_order)
    
    # Create text array that shows percentages only for non-NaN values
    # Fix numpy string concatenation issue by using list comprehension
    rounded_values = np.round(pivot_data.values, 1)
    text_array = np.array([[
        "" if np.isnan(val) else f"{val}%"
        for val in row
    ] for row in rounded_values])
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=[f"{h:02d}:00" for h in pivot_data.columns],
        y=pivot_data.index,
        colorscale='RdYlBu_r',
        zmin=0,
        zmax=100,
        colorbar=dict(title="Fill %"),
        text=text_array,
        texttemplate="%{text}",
        textfont={"size": 10, "family": "Arial"},
        hoverongaps=False
    ))
    
    title = f"Class Fill Percentage Heatmap ({source})" if source and source != "All" else "Class Fill Percentage Heatmap (All Sources)"
    
    fig.update_layout(
        title=title,
        xaxis_title="Hour",
        yaxis_title="Weekday",
        height=500,
        font=dict(family="Arial"),
        autosize=True
    )
    
    return fig

def main():
    """Main dashboard function."""
    st.title("Pilates Bookings in Belgium")
    
    # Get available sources
    available_sources = get_available_sources()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range selector
    today = datetime.now().date()
    default_start = today - timedelta(days=90)  # Last 3 months
    default_end = today + timedelta(days=30)    # Next month
    
    with st.sidebar.container():
        st.markdown("### Date Range")
        date_range = st.date_input(
            "Select period:",
            value=[default_start, default_end],
            min_value=datetime(2019, 1, 1).date(),
            max_value=datetime(2030, 12, 31).date(),
            help="Choose the date range for analysis"
        )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range[0]
        end_date = start_date + timedelta(days=7)
    
    # Source filter with improved styling
    with st.sidebar.container():
        st.markdown("### Pilates Studios")
        
        # Add select all/none buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Select All"):
                st.session_state.selected_sources = available_sources
        with col2:
            if st.button("Clear All"):
                st.session_state.selected_sources = []
        
        # Initialize session state if not exists
        if 'selected_sources' not in st.session_state:
            st.session_state.selected_sources = available_sources
        
        # Create checkboxes for each source with nice styling
        selected_sources = []
        for source in available_sources:
            is_selected = source in st.session_state.selected_sources
            if st.checkbox(f"{source.title()}", value=is_selected, key=f"checkbox_{source}"):
                selected_sources.append(source)
        
        # Update session state
        st.session_state.selected_sources = selected_sources
        
        # Show selection summary
        if selected_sources:
            st.caption(f"Selected: {len(selected_sources)} of {len(available_sources)} studios")
        else:
            st.error("No studios selected!")
    
    # Load data
    with st.spinner("Loading data..."):
        df = load_silver_data(start_date, end_date, selected_sources)
    
    if df.empty:
        st.warning("No data found for the selected filters.")
        st.stop()
    
    # Display last update info
    st.caption(f"Latest update: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Showing data from {start_date} to {end_date}")
    
    # Calculate metrics for KPI cards
    metrics = calculate_booking_metrics(df)
    
    # Source-specific metrics for comparison
    source_metrics = {}
    for source in selected_sources:
        source_df = df[df['source'] == source]
        source_metrics[source] = calculate_booking_metrics(source_df)
    
    # KPI Cards Row
    st.header("Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Classes",
            value=f"{metrics['total_classes']:,}",
            help="Total number of classes in selected period"
        )
    
    with col2:
        st.metric(
            label="Avg Fill Rate",
            value=f"{metrics['avg_fill_rate']:.0f}%",
            help="Average class fill percentage"
        )
    
    with col3:
        st.metric(
            label="Fully Booked",
            value=f"{metrics['fully_booked_pct']:.0f}%",
            help="Percentage of classes that are fully booked"
        )
    
    with col4:
        st.metric(
            label="Cancelled",
            value=f"{metrics['cancelled_pct']:.1f}%",
            help="Percentage of cancelled classes"
        )
    
    # Charts Row 1: Revenue
    st.header("Revenue Analysis")
    revenue_chart = create_revenue_chart(df)
    st.plotly_chart(revenue_chart, use_container_width=True)
    
    # Charts Row 2: Heatmap
    st.header("Class Fill Heatmap")
    
    heatmap_chart = create_fill_heatmap(df, "All")
    st.plotly_chart(heatmap_chart, use_container_width=True)
    
    # Source breakdown at bottom
    if len(selected_sources) > 1:
        st.header("By Source")
        source_cols = st.columns(len(selected_sources))
        
        for i, source in enumerate(selected_sources):
            with source_cols[i]:
                st.markdown(f"**{source.title()}**")
                st.write(f"Fill Rate: {source_metrics[source]['avg_fill_rate']:.0f}%")
                st.write(f"Classes: {source_metrics[source]['total_classes']}")
                
                # Calculate trend (simplified)
                current_fill = source_metrics[source]['avg_fill_rate']
                if current_fill > 75:
                    trend = "Good"
                elif current_fill > 50:
                    trend = "Average"
                else:
                    trend = "Low"
                st.write(f"Status: {trend}")
    
    # Data table (optional)
    with st.expander("Raw Data"):
        st.dataframe(
            df[['source', 'class_name', 'instructor', 'location', 'start_ts', 'capacity', 'spots_available', 'status']].head(100),
            use_container_width=True
        )

if __name__ == "__main__":
    main()
