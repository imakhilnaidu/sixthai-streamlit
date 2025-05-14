from pymongo import MongoClient
import pandas as pd
import streamlit as st
from urllib.parse import quote_plus
import plotly.express as px

# ------------------------------
# Configuration
# ------------------------------

password = quote_plus("@kkiS2000")

MONGO_URI = f"mongodb+srv://akhil:{password}@demo.8t589sg.mongodb.net/?retryWrites=true&w=majority&appName=demo"
# MONGO_URI = "mongodb://172.23.64.1:27017/"
DB_NAME = "google-trends"
COLLECTION_NAME = "realestate"
vibrant_colors = px.colors.qualitative.Vivid

# Country code to full name mapping
COUNTRY_CODE_MAP = {
    "AE": "United Arab Emirates",
    "EG": "Egypt",
    "GB": "United Kingdom",
    "SA": "Saudi Arabia"
}

# ------------------------------
# Load Data from MongoDB
# ------------------------------

all_docs = list(MongoClient(MONGO_URI)[DB_NAME][COLLECTION_NAME].find({}))
timeline_data = []

for doc in all_docs:
    theme = doc.get("theme")
    timeline = doc.get("timeline", [])
    for entry in timeline:
        entry["theme"] = theme
        geo_code = entry.get("geo")
        entry["country"] = COUNTRY_CODE_MAP.get(geo_code, geo_code)  # Full country name
        timeline_data.append(entry)

df = pd.DataFrame(timeline_data)

if df.empty:
    st.warning("No data available.")
    st.stop()


# ------------------------------
# Filter Section (Top of Page)
# ------------------------------

def trends_dashboard():

    themes = sorted(df["theme"].dropna().unique().tolist())
    countries = sorted(df["country"].dropna().unique().tolist())

    col1, col2 = st.columns(2)

    with col1:
        selected_theme = st.selectbox("🎨 Select Theme", ["All"] + themes)

    with col2:
        selected_country = st.selectbox("🌍 Select Country", ["All"] + countries)

    # Apply filters
    filtered_df = df.copy()
    if selected_theme != "All":
        filtered_df = filtered_df[filtered_df["theme"] == selected_theme]
    if selected_country != "All":
        filtered_df = filtered_df[filtered_df["country"] == selected_country]

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        st.stop()

    # ------------------------------
    # Charts
    # ------------------------------

    col1, col2 = st.columns(2)

    with col1:
        # Top 5 Themes by Avg Interest
        theme_avg = filtered_df.groupby("theme", as_index=False)["value"].mean()
        top_5_themes = theme_avg.sort_values("value", ascending=False).head(5)

        fig_theme_bar = px.bar(
            top_5_themes,
            x="theme",
            y="value",
            labels={"value": "Average Interest (%)", "theme": "Theme"},
            color="theme",
            title="Top 5 Themes by Average Interest",
            color_discrete_sequence=vibrant_colors
        )
        fig_theme_bar.update_layout(
            showlegend=False,
            yaxis_tickformat=".0f",
            bargap=0.5
        )
        st.plotly_chart(fig_theme_bar, use_container_width=True)

    with col2:
        # Theme Distribution (Donut Chart)
        theme_distribution = (
            filtered_df.groupby("theme", as_index=False)["value"]
            .mean()
            .query("value > 0")
            .sort_values("value", ascending=False)
        )

        fig_theme_pie = px.pie(
            theme_distribution,
            names="theme",
            values="value",
            title="Theme Distribution by Average Interest",
            hole=0.4,
            color_discrete_sequence=vibrant_colors
        )

        fig_theme_pie.update_traces(
            textinfo="percent",
            pull=[0.03] * len(theme_distribution),
            hovertemplate="%{label}: %{value:.1f}%"
        )
        st.plotly_chart(fig_theme_pie, use_container_width=True)

    st.markdown("### &nbsp;")

    # Top 3 Themes Over Time
    top_3_themes = (
        filtered_df.groupby("theme")["value"]
        .mean()
        .nlargest(3)
        .index.tolist()
    )

    top_themes_df = filtered_df[filtered_df["theme"].isin(top_3_themes)]
    top_themes_df["date"] = pd.to_datetime(top_themes_df["date"])

    theme_trend_df = (
        top_themes_df.groupby(["date", "theme"], as_index=False)["value"]
        .mean()
    )

    fig_theme_trends = px.line(
        theme_trend_df,
        x="date",
        y="value",
        color="theme",
        title="Top 3 Themes – Trend Over Time",
        labels={"value": "Interest (%)", "date": "Date", "theme": "Theme"},
        line_shape="spline",
        color_discrete_sequence=vibrant_colors
    )
    fig_theme_trends.update_traces(marker=dict(size=4))
    fig_theme_trends.update_layout(
        yaxis_tickformat=".0f",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        xaxis=dict(tickformat="%b\n%Y", tickangle=0)
    )
    st.plotly_chart(fig_theme_trends, use_container_width=True)

    st.markdown("### &nbsp;")

    # Top 10 Keywords (Global)
    keyword_avg = filtered_df.groupby("keyword", as_index=False)["value"].mean()
    top_keywords = keyword_avg.sort_values("value", ascending=False).head(15)

    fig_keywords = px.bar(
        top_keywords,
        x="keyword",
        y="value",
        labels={"value": "Interest (%)", "keyword": "Keyword"},
        color="keyword",
        title="Top 10 Keywords by Average Interest",
        color_discrete_sequence=px.colors.qualitative.Vivid
    )
    fig_keywords.update_layout(
        showlegend=False,
        yaxis_tickformat=".0f",
        xaxis_tickangle=0,
        bargap=0.4
    )
    st.plotly_chart(fig_keywords, use_container_width=True)

    st.markdown("### &nbsp;")

    # Keyword Trends Over Time (Top 3 Keywords)
    top_3_keywords = (
        filtered_df.groupby("keyword")["value"]
        .mean()
        .nlargest(3)
        .index.tolist()
    )

    top_keyword_df = filtered_df[filtered_df["keyword"].isin(top_3_keywords)]
    top_keyword_df["date"] = pd.to_datetime(top_keyword_df["date"])

    keyword_trend = (
        top_keyword_df.groupby(["date", "keyword"], as_index=False)["value"].mean()
    )

    fig_keyword_trends = px.line(
        keyword_trend,
        x="date",
        y="value",
        color="keyword",
        labels={"value": "Interest (%)", "date": "Date", "keyword": "Keyword"},
        title="Trend Over Time – Top 3 Keywords",
        line_shape="spline",
        color_discrete_sequence=vibrant_colors
    )
    fig_keyword_trends.update_traces(marker=dict(size=4))
    fig_keyword_trends.update_layout(
        yaxis_tickformat=".0f",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        xaxis=dict(tickformat="%b\n%Y", tickangle=0)
    )
    st.plotly_chart(fig_keyword_trends, use_container_width=True)


    # ---------------------------------------------
    # Top 3 Fastest Growing Keywords Over Time
    # ---------------------------------------------

    # Prepare time series by keyword
    keyword_time = (
        filtered_df.groupby(["keyword", "date"], as_index=False)["value"].mean()
    )
    keyword_time["date"] = pd.to_datetime(keyword_time["date"])

    # Compute growth: latest - earliest value for each keyword
    growth_data = keyword_time.sort_values("date").groupby("keyword").agg(
        start_value=("value", "first"),
        end_value=("value", "last")
    )
    growth_data["growth"] = growth_data["end_value"] - growth_data["start_value"]
    top_growing_keywords = growth_data.sort_values("growth", ascending=False).head(3).index.tolist()

    # Filter for top 3 growing keywords
    growing_df = keyword_time[keyword_time["keyword"].isin(top_growing_keywords)]

    # Plot line chart
    fig_growth = px.line(
        growing_df,
        x="date",
        y="value",
        color="keyword",
        title="📈 Top 3 Fastest Growing Keywords Over Time",
        labels={"value": "Interest (%)", "date": "Date", "keyword": "Keyword"},
        line_shape="spline",
        color_discrete_sequence=vibrant_colors
    )
    fig_growth.update_traces(marker=dict(size=4))
    fig_growth.update_layout(
        yaxis_tickformat=".0f",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="center",
            x=0.5,
            font=dict(size=12)
        ),
        xaxis=dict(tickformat="%b\n%Y", tickangle=0)
    )
    st.plotly_chart(fig_growth, use_container_width=True)

