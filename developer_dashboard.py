import streamlit as st

import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import json
from functools import lru_cache
from developer_data import *





def dashboard_developer():
    # Initialize session state for storing filter values
    if 'filter_themes' not in st.session_state:
        st.session_state['filter_themes'] = []
    if 'filter_keywords' not in st.session_state:
        st.session_state['filter_keywords'] = []
    if 'filter_accounts' not in st.session_state:
        st.session_state['filter_accounts'] = []
    if 'filter_date_range' not in st.session_state:
        st.session_state['filter_date_range'] = None
    if 'filter_countries' not in st.session_state:
        st.session_state['filter_countries'] = []



    # Initialize session state for applied filters
    if 'selected_themes' not in st.session_state:
        st.session_state['selected_themes'] = []
    if 'selected_keywords' not in st.session_state:
        st.session_state['selected_keywords'] = []
    if 'selected_accounts' not in st.session_state:
        st.session_state['selected_accounts'] = []
    if 'date_range' not in st.session_state:
        st.session_state['date_range'] = None
    if 'selected_countries' not in st.session_state:
        st.session_state['selected_countries'] = []


    data = get_data()

    print(f"Total accounts = {len(data)}")

    # Get list of all usernames for account filter
    all_usernames = list(set([account.get('username', '') for account in data]))
    all_usernames.sort()  # Sort alphabetically for better UX

    # Get min and max dates from the data for the date range filter
    min_date, max_date = get_date_range(data)
    # Set default date range if not already in session state
    if st.session_state['filter_date_range'] is None and min_date and max_date:
        st.session_state['filter_date_range'] = (min_date, max_date)
        st.session_state['date_range'] = (min_date, max_date)  # Also set applied date range

    # Define callback functions for all filters
    def update_theme_selection():
        if "theme_filter_callback" in st.session_state:
            st.session_state['filter_themes'] = st.session_state["theme_filter_callback"]

    def update_keyword_selection():
        if "keyword_filter_callback" in st.session_state:
            st.session_state['filter_keywords'] = st.session_state["keyword_filter_callback"]

    def update_account_selection():
        if "account_filter_callback" in st.session_state:
            st.session_state['filter_accounts'] = st.session_state["account_filter_callback"]

    def update_country_selection():
        if "country_filter_callback" in st.session_state:
            st.session_state['filter_countries'] = st.session_state["country_filter_callback"]


    def update_date_selection():
        if "date_filter_callback" in st.session_state:
            date_input = st.session_state["date_filter_callback"]
            # Handle both single date and date range selections
            if isinstance(date_input, tuple) and len(date_input) == 2:
                st.session_state['filter_date_range'] = date_input
            elif hasattr(date_input, '__len__') and len(date_input) == 2:
                st.session_state['filter_date_range'] = (date_input[0], date_input[1])
            else:
                # For single date selection
                st.session_state['filter_date_range'] = (date_input, date_input)

    # Set the title
    st.subheader("Developer Dashboard")

    # Create a container for filters
    filter_container = st.container()

    with filter_container:
        # Create two rows of filters
        filter_row1_col1, filter_row1_col2, filter_row1_col3 = st.columns(3)
        filter_row2_col1, filter_row2_col2 = st.columns(2)
        
        with filter_row1_col1:
            # Get all available themes
            all_themes = list(THEME_KEYWORDS.keys())
            all_themes.append("Others")  # Add "Others" as it's used in your theme distribution
            
            # Theme filter with callback
            st.multiselect(
                "Filter by Themes",
                options=all_themes,
                default=st.session_state['filter_themes'],
                key="theme_filter_callback",
                on_change=update_theme_selection
            )
        
        with filter_row1_col2:
            # Get all available keywords from all themes
            all_keywords = []
            for theme, keywords in THEME_KEYWORDS.items():
                all_keywords.extend(keywords)
            
            # Sort keywords alphabetically for better user experience
            all_keywords = sorted(list(set(all_keywords)))
            
            # Keyword filter with callback
            st.multiselect(
                "Filter by Keywords",
                options=all_keywords,
                default=st.session_state['filter_keywords'],
                key="keyword_filter_callback",
                on_change=update_keyword_selection
            )
        
        with filter_row1_col3:
            # Get all unique countries from data
            all_countries = sorted(list(set([account.get('country', '') for account in data if account.get('country')])))

            # Country filter
            st.multiselect(
                "Filter by Country",
                options=all_countries,
                default=st.session_state['filter_countries'],
                key="country_filter_callback",
                on_change=update_country_selection
            )
        
        with filter_row2_col1:
            # Account filter with callback
            st.multiselect(
                "Filter by Accounts",
                options=all_usernames,
                default=st.session_state['filter_accounts'],
                key="account_filter_callback",
                on_change=update_account_selection
            )
        
        with filter_row2_col2:
            # Date range filter with callback
            if min_date and max_date:
                st.date_input(
                    "Filter by Date Range",
                    value=st.session_state['filter_date_range'],
                    min_value=min_date,
                    max_value=max_date,
                    key="date_filter_callback",
                    on_change=update_date_selection
                )

        # Add buttons in a row
        button_col1, button_col2 = st.columns([1, 1])
        
        with button_col1:
            # Apply Filters button
            if st.button("Apply Filters", type="primary"):
                st.session_state['selected_themes'] = st.session_state['filter_themes']
                st.session_state['selected_keywords'] = st.session_state['filter_keywords']
                st.session_state['selected_accounts'] = st.session_state['filter_accounts']
                st.session_state['selected_countries'] = st.session_state['filter_countries']  
                st.session_state['date_range'] = st.session_state['filter_date_range']
                st.toast("Filters Applied", icon="✅")

        
        with button_col2:
            # Clear Filters button
            if st.button("Clear Filters"):
                # Clear both the filter values and the applied filters
                st.session_state['filter_themes'] = []
                st.session_state['filter_keywords'] = []
                st.session_state['filter_accounts'] = []
                st.session_state["filter_countries"] = []
                if min_date and max_date:
                    st.session_state['filter_date_range'] = (min_date, max_date)
                
                # Also clear the applied filters
                st.session_state['selected_themes'] = []
                st.session_state['selected_keywords'] = []
                st.session_state['selected_accounts'] = []
                st.session_state["selected_countries"] = []
                if min_date and max_date:
                    st.session_state['date_range'] = (min_date, max_date)
                
                st.rerun()

    # Apply filters to data based on the applied filters (not the filter input values)
    filtered_data = filter_data(
        data, 
        st.session_state['selected_themes'], 
        st.session_state['selected_keywords'],
        st.session_state['selected_accounts'],
        st.session_state['date_range'],
        st.session_state['selected_countries']
    )

    # Display the currently applied filters
    if (st.session_state['selected_themes'] or 
        st.session_state['selected_keywords'] or 
        st.session_state['selected_accounts'] or 
        st.session_state["selected_countries"] or
        (st.session_state['date_range'] and st.session_state['date_range'] != (min_date, max_date))):
        
        st.subheader("Applied Filters")
        applied_filters = []
        
        if st.session_state['selected_themes']:
            applied_filters.append(f"Themes: {', '.join(st.session_state['selected_themes'])}")
        
        if st.session_state['selected_keywords']:
            applied_filters.append(f"Keywords: {', '.join(st.session_state['selected_keywords'])}")
        
        if st.session_state['selected_accounts']:
            applied_filters.append(f"Accounts: {', '.join(st.session_state['selected_accounts'])}")

        if st.session_state["selected_countries"]:
            applied_filters.append(f"Countries: {', '.join(st.session_state['selected_countries'])}")
        
        if st.session_state['date_range'] and st.session_state['date_range'] != (min_date, max_date):
            start, end = st.session_state['date_range']
            applied_filters.append(f"Date Range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        
        st.info(" | ".join(applied_filters))



    # Dashboard metrics with filtered data
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Total Accounts", get_total_accounts(filtered_data))
    with col2:
        st.metric("🌍 Total Countries", get_total_countries(filtered_data))
    with col3:
        st.metric("📸 Total Posts", format_number(get_total_posts(filtered_data)))
    with col4:
        st.metric("💬 Total Engagements", format_number(get_total_engagements(filtered_data)))
    with col5:
        total_posts = get_total_posts(filtered_data)
        if total_posts > 0:
            ape = round(get_total_engagements(filtered_data) / total_posts)
            st.metric("👥 Avg Post Engagement", format_number(ape))
        else:
            st.metric("👥 Avg Post Engagement", "0")
    with col6:
        st.metric("🌟 Reach", format_number(get_estimated_reach(filtered_data)))


    # Apply styles

    st.markdown("""
    <style>
    /* Improve specificity and ensure metric styling is applied */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 1rem;
        border: 1px solid rgba(200, 200, 200, 0.6);
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        text-align: center;
        transition: all 0.3s ease-in-out;
        margin: 0.5rem 0;
    }

    /* Text inside the metric */
    div[data-testid="stMetric"] label, 
    div[data-testid="stMetric"] div {
        color: #000 !important;
    }

    /* Dark mode styles */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: #0E1117;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 2px 8px rgba(255, 255, 255, 0.05);
        }

        div[data-testid="stMetric"] label, 
        div[data-testid="stMetric"] div {
            color: #fff !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)



    # Get filtered accounts
    df = get_accounts(filtered_data)

    # ⚙️ Column config for links
    column_config = {
        "Profile URL": st.column_config.LinkColumn("Profile URL", display_text="Open"),
        "External URL": st.column_config.LinkColumn("External URL", display_text="Open"),
        "Post URL": st.column_config.LinkColumn("Post URL", display_text="Open"),
    }

    # Start index from 1 instead of 0
    df.index = range(1, len(df) + 1)

    # 📋 Show filtered table
    st.dataframe(df, column_config=column_config)

    # --- POST TREND LINE ---
    post_counts_by_month = get_post_trend_data(filtered_data)

    st.caption("Post Trend Line")
    if not post_counts_by_month.empty:
        st.line_chart(post_counts_by_month, x="month", y="post_count", x_label="Month", y_label="Post Count", use_container_width=True)
    else:
        st.info("No post trend data available for the selected filters.")

    # --- ENGAGEMENT TREND LINE ---
    engagement_by_month = get_engagement_trend_data(filtered_data)

    st.caption("Engagement Trend Line")
    if not engagement_by_month.empty:
        st.line_chart(engagement_by_month, x="month", y="total_engagement", x_label="Month", y_label="Engagement", use_container_width=True, )
    else:
        st.info("No engagement trend data available for the selected filters.")

    # Get the theme distribution over time
    theme_distribution_over_time = get_theme_distribution_over_time(filtered_data)

    st.caption("Theme Distribution Over Time")

    # Use st.cache_data to cache the theme distribution over time calculation
    @st.cache_data(ttl=3600)  # Cache results for 1 hour
    def get_cached_theme_distribution_over_time(data_hash):
        # This is a trick to force recalculation when filtered_data changes
        return get_theme_distribution_over_time(filtered_data)

    # Create a hash of the filtered data to track changes
    data_hash = hash(str([(a.get('username', ''), len(a.get('posts', []))) for a in filtered_data]))
    theme_distribution_over_time = get_cached_theme_distribution_over_time(data_hash)

    # Check if theme distribution over time data exists
    if not theme_distribution_over_time.empty:
        # Prepare the data - include all themes without limiting to top 5
        themes_to_include = list(theme_distribution_over_time['Theme'].unique())
        if 'Others' in theme_distribution_over_time['Theme'].unique() and 'Others' not in themes_to_include:
            themes_to_include.append('Others')
        
        stream_data = theme_distribution_over_time[theme_distribution_over_time['Theme'].isin(themes_to_include)]
        stream_data = stream_data.groupby(['Month', 'Theme']).agg({'Post Count': 'sum'}).reset_index()
        
        # Apply theme filter to streamgraph if themes are selected
        if st.session_state['selected_themes']:
            filtered_themes = [t for t in st.session_state['selected_themes'] if t in stream_data['Theme'].unique()]
            if filtered_themes:
                stream_data = stream_data[stream_data['Theme'].isin(filtered_themes)]
        
        # Only display the graph if we have data after filtering
        if not stream_data.empty:
            # Create a streamgraph using plotly with simplified settings
            fig_stream = px.area(
                stream_data,
                x="Month", 
                y="Post Count", 
                color="Theme",
                # Removed line_group for better performance
            )

            # Simplified layout
            fig_stream.update_layout(
                xaxis_title="Month", 
                yaxis_title="Post Count",
                margin=dict(l=20, r=20, t=30, b=20)
            )

            # Display the plot with static rendering for faster loading
            st.plotly_chart(fig_stream, use_container_width=True, config={'staticPlot': True})
        else:
            st.info("No theme distribution over time data available for the selected filters.")
    else:
        st.info("No theme distribution over time data available for the selected filters.")

    # Get the top 10 most used keywords
    top_keyword_data = get_top_keywords(filtered_data, top_n=15)

    st.caption("Top Keywords")

    # Check if top keyword data exists
    if not top_keyword_data.empty and len(top_keyword_data) > 0:
        # Create the vertical bar chart for top keywords
        fig_bar = px.bar(
            top_keyword_data, 
            x='Keyword', 
            y='Count',
            color='Keyword',
            text='Count',
            color_discrete_sequence=px.colors.qualitative.Vivid
        )

        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(showlegend=False)

        # Display the plot in Streamlit
        st.plotly_chart(fig_bar, use_container_width=True, key="top_keyword_bar_chart")
    else:
        st.info("No keyword data available for the selected filters.")

    # Calculate a stable hash for the filtered data to use as a cache key
    def get_data_hash(data):
        """Create a stable hash of the filtered data for caching purposes"""
        # Extract just the essential details to create a more stable hash
        hash_data = []
        for account in data:
            acc_data = {
                "username": account.get("username", ""),
                "post_count": len(account.get("posts", [])),
                # Add a hash of the first 5 posts to detect content changes
                "post_sample": [post.get("upload_date", "") + (post.get("caption", "") or "")[:50] 
                            for post in account.get("posts", [])[:5]]
            }
            hash_data.append(acc_data)
        
        # Create a stable string representation and hash it
        data_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    # Add these decorators to cache the theme distributions
    @st.cache_data(ttl=3600)
    def cached_theme_distribution(data_hash, allow_multiple_themes=True, fuzzy_threshold=80):
        """Cached version of theme distribution calculation"""
        try:
            return get_theme_distribution(filtered_data, allow_multiple_themes, fuzzy_threshold)
        except Exception as e:
            st.error(f"Error calculating theme distribution: {str(e)}")
            return {}

    @st.cache_data(ttl=3600)
    def cached_theme_distribution_over_time(data_hash):
        """Cached version of theme distribution over time calculation"""
        try:
            return get_theme_distribution_over_time(filtered_data)
        except Exception as e:
            st.error(f"Error calculating theme distribution over time: {str(e)}")
            return {}
            
    # Replace the Theme Distribution section with this code
    st.markdown(
        "<p style='text-align: center; color: gray; font-size: 0.9rem;'>Theme Distribution</p>", 
        unsafe_allow_html=True
    )

    # Get a hash of the current filtered data
    current_data_hash = get_data_hash(filtered_data)

    # Use the cached version
    with st.spinner("Calculating theme distribution..."):
        theme_distribution = cached_theme_distribution(current_data_hash)

    col1, col2 = st.columns(2)

    # Check if there's any data first before processing
    if theme_distribution and sum(theme_distribution.values()) > 0:
        # Create dataframe once
        theme_data = pd.DataFrame(list(theme_distribution.items()), 
                                columns=["Theme", "Post Count"])
        theme_data_sorted = theme_data.sort_values(by='Post Count', ascending=False)
        
        with col1:
            # Add progress indicator
            with st.spinner("Rendering pie chart..."):
                fig_pie = px.pie(
                    names=theme_data_sorted["Theme"],
                    values=theme_data_sorted["Post Count"],
                    color_discrete_sequence=px.colors.qualitative.Dark2
                )
                fig_pie.update_traces(textinfo='percent')
                # Simplify for better performance
                fig_pie.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Add progress indicator
            with st.spinner("Rendering bar chart..."):
                fig_bar = px.bar(
                    theme_data_sorted,
                    x='Post Count', 
                    y='Theme',
                    orientation='h',
                    color='Theme',
                    text='Post Count',
                    color_discrete_sequence=px.colors.qualitative.Vivid
                )
                fig_bar.update_traces(textposition='outside')
                fig_bar.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)
    else:
        # Display message once and reuse
        no_data_message = "No theme distribution data available for the selected filters."
        col1.info(no_data_message)
        col2.info(no_data_message)