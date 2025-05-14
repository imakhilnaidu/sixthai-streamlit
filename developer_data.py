import re
from urllib.parse import quote_plus
import pandas as pd
import streamlit as st
from pymongo import MongoClient
from datetime import datetime, date
from collections import Counter
from rapidfuzz import fuzz
from googletrans import Translator
from langdetect import detect


def get_data():
    try:
        password = quote_plus("@kkiS2000")

        MONGO_URI = f"mongodb+srv://akhil:{password}@demo.8t589sg.mongodb.net/?retryWrites=true&w=majority&appName=demo"
        client = MongoClient(MONGO_URI)
        db = client["instagram"]
        collection = db["realestate-developers"]
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")


    # Fetch all documents
    data = list(collection.find())

    return data


def get_date_range(data):
    """
    Get minimum and maximum dates from all posts in the data
    
    Args:
        data (list): List of account data
        
    Returns:
        tuple: (min_date, max_date) as datetime.date objects, or (None, None) if no valid dates
    """
    all_dates = []
    
    for account in data:
        for post in account.get("posts", []):
            upload_date_str = post.get("upload_date")
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                    all_dates.append(upload_date)
                except ValueError:
                    pass  # Skip malformed dates
    
    if all_dates:
        return min(all_dates), max(all_dates)
    else:
        return None, None


def filter_data(data, selected_themes=None, selected_keywords=None, selected_accounts=None, date_range=None, selected_countries=None):
    """
    Filter the data based on selected themes, keywords, accounts, date range, and countries
    """
    # If no filters applied, return original data
    if not selected_themes and not selected_keywords and not selected_accounts and not date_range and not selected_countries:
        return data
        
    filtered_data = []
    
    for account in data:
        username = account.get("username", "")
        country = account.get("country", "")
        
        # Filter by account
        account_match = True
        if selected_accounts:
            account_match = username in selected_accounts
        
        # Filter by country
        country_match = True
        if selected_countries:
            country_match = country in selected_countries
        
        if not (account_match and country_match):
            continue
        
        filtered_account = account.copy()
        filtered_posts = []
        
        for post in account.get("posts", []):
            caption = (post.get("caption") or "").lower()
            hashtags = [h.lower() for h in post.get("hashtags", [])]
            text_blob = caption + " " + " ".join(hashtags)
            
            # Check date range
            date_match = True
            if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
                upload_date_str = post.get("upload_date")
                if upload_date_str:
                    try:
                        upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                        start_date, end_date = date_range
                        if isinstance(start_date, datetime):
                            start_date = start_date.date()
                        if isinstance(end_date, datetime):
                            end_date = end_date.date()
                        date_match = start_date <= upload_date <= end_date
                    except ValueError:
                        date_match = False
                else:
                    date_match = False
            
            if not date_match:
                continue

            # Check themes
            theme_match = True
            if selected_themes:
                post_themes = []
                for theme, keywords in THEME_KEYWORDS.items():
                    if any(keyword.lower() in text_blob for keyword in keywords):
                        post_themes.append(theme)
                
                if not post_themes and "Others" in selected_themes:
                    theme_match = True
                elif any(theme in selected_themes for theme in post_themes):
                    theme_match = True
                else:
                    theme_match = False

            # Check keywords
            keyword_match = True
            if selected_keywords:
                if not any(keyword.lower() in text_blob for keyword in selected_keywords):
                    keyword_match = False
            
            if theme_match and keyword_match:
                filtered_posts.append(post)
        
        if filtered_posts:
            filtered_account["posts"] = filtered_posts
            filtered_data.append(filtered_account)
    
    return filtered_data



def get_total_accounts(data):
    return len(data)


def get_total_engagements(data):
    total_engagements = 0
    for account in data:
        for post in account.get("posts", []):
            total_engagements += post.get("number_of_likes", 0) or 0
            total_engagements += post.get("number_of_comments", 0) or 0
            total_engagements += post.get("video_view_count", 0) or 0

    return total_engagements


def get_total_posts(data):
    total_posts = 0
    for account in data:
        total_posts += len(account.get("posts", []))

    return total_posts


# Heuristic: assume ~10% of followers see a post + a boost from engagement
def estimate_post_reach(post, followers):
    likes = post.get("number_of_likes", 0) or 0
    comments = post.get("number_of_comments", 0) or 0
    views = post.get("video_view_count", 0) or 0

    engagement = likes + comments + views
    return (0.1 * followers) + (0.05 * engagement)


def get_estimated_reach(data):
    estimated_reach = 0
    for account in data:
        followers = account.get("followers", 0)
        for post in account.get("posts", []):
            estimated_reach += estimate_post_reach(post, followers)
    return int(estimated_reach)


def get_post_trend_data(data):
    post_dates = []
    for account in data:
        for post in account.get("posts", []):
            upload_date_str = post.get("upload_date")
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                    post_dates.append(upload_date)
                except ValueError:
                    pass  # skip malformed dates

    # If no posts match the filters, return an empty dataframe
    if not post_dates:
        return pd.DataFrame(columns=["month", "post_count"])
        
    # Step 2: Create DataFrame and convert the date column to datetime
    df_posts = pd.DataFrame(post_dates, columns=["date"])
    df_posts["date"] = pd.to_datetime(df_posts["date"])  # Ensure 'date' column is datetime type

    # Extract month-year for grouping
    df_posts["month"] = df_posts["date"].dt.to_period("M").dt.to_timestamp()

    # Group by month and count posts
    post_counts_by_month = df_posts.groupby("month").size().reset_index(name="post_count")

    return post_counts_by_month


def get_engagement_trend_data(data):
    engagement_data = []
    for account in data:
        for post in account.get("posts", []):
            upload_date_str = post.get("upload_date")
            likes = post.get("number_of_likes", 0) or 0
            comments = post.get("number_of_comments", 0) or 0
            video_view_count = post.get("video_view_count", 0) or 0
            
            if upload_date_str:
                try:
                    upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d").date()
                    total_engagement = likes + comments + video_view_count  # Sum of likes, comments, and video views
                    engagement_data.append((upload_date, total_engagement))
                except ValueError:
                    pass  # skip malformed dates

    # If no engagement data matches the filters, return an empty dataframe
    if not engagement_data:
        return pd.DataFrame(columns=["month", "total_engagement"])
        
    # Step 2: Create DataFrame and convert the date column to datetime
    df_engagement = pd.DataFrame(engagement_data, columns=["date", "engagement"])
    df_engagement["date"] = pd.to_datetime(df_engagement["date"])  # Ensure 'date' column is datetime type

    # Extract month-year for grouping
    df_engagement["month"] = df_engagement["date"].dt.to_period("M").dt.to_timestamp()

    # Group by month and calculate total engagement for each month
    engagement_by_month = df_engagement.groupby("month")["engagement"].sum().reset_index(name="total_engagement")

    return engagement_by_month


THEME_KEYWORDS = {
    "Sustainability": [
        "solar", "eco", "green", "leed", "renewable", "sustainable", "energy-efficient", "water saving",
        "recycled", "salvaged", "cork", "hemp", "rammed earth", "bamboo", "clay plaster", "greywater", "composting",
        "carbon footprint", "net-zero", "passive design", "insulation", "low-flow", "rainwater", "green building",
        "carbon neutral", "green energy", "eco-friendly", "sustainable design", "sustainable architecture", "environmentally friendly", "clean energy", "energy-efficient appliances", "solar panels", "green roofs"
    ],
    "Smart Home Technology": [
        "smart", "automation", "voice control", "connectivity", "remote access", "security", "alexa", "smart meters",
        "smart locks", "home automation", "remote surveillance", "motion sensors", "ai-powered", "energy monitoring",
        "virtual concierge", "smart thermostat", "app-controlled", "voice assistant",
        "smart lights", "home assistant", "intelligent home", "smart home system", "IoT", "connected home", "smart appliances", "automated home", "home automation system", "smart lighting"
    ],
    "Wellness Amenities": [
        "meditation", "spa", "health club", "wellness center", "hydrotherapy", "soaking tub", "massage", "therapy",
        "sauna", "nutritional counseling", "jetted bathtub", "wellness", "relaxation", "well-being", "health retreat", "meditation room", "rejuvenation", "holistic health"
    ],
    "House Features": [
        "open floor plan", "granite countertops", "stainless steel appliances", "hardwood floors", "walk-in closet",
        "master suite", "fireplace", "attached garage", "high ceilings", "laundry room", "bonus room", "covered patio",
        "central air", "kitchen island", "breakfast bar", "pantry", "mudroom", "wine cellar", "nanny room", "sunroom",
        "wet bar", "vaulted ceilings", "custom cabinetry", "spacious", "terrace", "balcony", "large windows",
        "modern kitchen", "open-plan", "wood floors", "recessed lighting", "crown molding", "storage space", "basement",
        "stainless steel", "walk-in pantry", "bay window", "stone countertops", "luxury bathroom", "home office", "high ceilings", "floor-to-ceiling windows", "chef’s kitchen", "custom-built"
    ],
    "Interior Design": [
        "luxury flooring", "neutral palette", "architectural", "feature walls", "tile work", "backsplash", "cozy",
        "modern", "classic", "bohemian", "contemporary", "minimalist", "industrial", "farmhouse", "scandinavian",
        "mediterranean", "victorian", "craftsman", "mid-century", "eclectic", "transitional", "rustic", "coastal",
        "colonial", "art deco", "tudor", "asian-inspired", "chic", "prestigious", "custom homes", "timeless", "award-winning",
        "luxurious", "sleek design", "chandeliers", "furniture design", "high-end finishes", "open shelving", "design trends", "custom-built", "artsy", "statement pieces"
    ],
    "Sports/Activities": [
        "tennis", "basketball", "soccer", "baseball", "volleyball", "fitness", "running", "golf", "yoga", "cycling",
        "crossfit", "climbing", "dance", "aerobics", "training", "billiards", "sports", "bike", "jogging", "gymnasium",
        "swimming", "gym", "martial arts", "gymnastics", "sports court", "fitness classes", "exercise", "swimming pool", "fitness equipment", "athletics"
    ],
    "Amenities": [
        "gated community", "security", "cameras", "access control", "club", "pool", "fitness center", "neighborhood watch",
        "visitor management", "bbq", "community parties", "outdoor concerts", "events", "picnic", "craft nights",
        "holiday celebrations", "cultural festivals", "cinema", "playground", "clubhouse", "gym", "spa", "restaurant", "barbecue area", "pet park", "garden", "swimming pool", "fitness studio", "community garden"
    ],
    "Safety": [
        "security patrols", "emergency", "motion sensor", "crime prevention", "controlled access", "well-lit", "intercom",
        "evacuation", "fire safety", "alarms", "visitor management", "alarm system", "surveillance", "emergency exit", "fire alarm", "security cameras", "fenced perimeter", "security gate", "neighborhood patrol", "smoke detectors", "secure entrance"
    ],
    "Entertainment": [
        "gaming", "game room", "movie theater", "bbq area", "live music", "comedy shows", "cooking classes",
        "art workshops", "talent shows", "family game nights", "coffee bar", "bars", "lounge", "entertainment",
        "event space", "cinema", "concerts", "karaoke", "poolside bar", "family events", "nightlife", "music room", "comedy club", "concert venue"
    ],
    "Working Space": [
        "co-working", "business center", "conference rooms", "private offices", "high-speed internet", "printing", "copying",
        "workstations", "meeting pods", "quiet zones", "collaborative workspace", "networking events", "workshops",
        "seminars", "lounge areas", "flexible workspace", "telecommuting", "video conferencing", "hot desk", "meeting space", "remote work", "business lounge", "coworking space", "office suite", "tech-enabled office"
    ],
    "Greenery": [
        "community gardens", "parks", "nature trails", "green belts", "arboretum", "botanical", "green rooftops",
        "urban forests", "rain gardens", "butterfly gardens", "shade trees", "flowering", "orchards", "rooftop gardens",
        "tree-lined", "green vibes", "green living", "nature", "lagoon", "river", "vertical gardens", "outdoor yoga deck",
        "botanical gardens", "forest area", "eco gardens", "native plants", "green spaces", "organic garden", "landscape design", "green walls", "environmental design", "outdoor lounge"
    ],
    "Pet-Friendly Amenities": [
        "dog park", "pet grooming", "pet clinic", "pet events", "pet spa", "pet concierge", "pet trails",
        "pet waste stations", "pet friendly", "dog-friendly", "pet lounge", "dog walking area", "pet play area", "pet park", "cat-friendly", "pet relief station", "pet-friendly cafe", "pet daycare"
    ],
    "Disabled People Amenities": [
        "accessible", "wheelchair", "elevators", "handicap", "roll-in showers", "lowered countertops",
        "accessible pathways", "visual fire alarms", "hearing loop", "accessible pathways", "adapted bathrooms", "low counters", "wheelchair ramps", "elevator access", "accessible parking", "accessible showers", "assistive devices", "visual aids"
    ],
    "Children Amenities": [
        "playground", "splash pad", "kids club", "nursery", "childcare", "babysitting", "scooter lanes",
        "children's library", "storytime", "summer camps", "teen center", "school bus", "play area", "kids zone", "children's pool", "family entertainment", "playhouse", "kids events", "child-friendly", "safe play areas", "sandbox", "youth programs"
    ],
    "Parking Amenities": [
        "garage", "driveway", "carport", "parking", "valet", "bike racks", "tandem", "remote-controlled garage",
        "on-street parking", "car wash", "electric vehicle charging", "covered parking", "parking garage", "multi-level parking", "secure parking", "visitor parking", "car charging stations", "parking space availability", "dedicated parking"
    ],
    "Views": [
        "panoramic views", "city skyline", "mountain views", "waterfront", "golf course views", "lake views",
        "oceanfront", "sunset views", "scenic", "coastalliving", "lagoon", "river", "mountain view", "cityscape", "scenic view", "water views", "beachfront", "sunrise view", "sunset views", "park view", "forest view", "skyline"
    ],
    "Accessibility": [
        "quick access", "highway", "marina", "malls", "walking distance", "minutes' drive", "connectivity", "metro",
        "train", "bus station", "prime location", "easy access", "close to amenities", "public transport", "walkable", "central location", "bike paths", "nearby services", "close to shopping", "public transportation access"
    ],
    "Lifestyle": [
        "luxury", "modern living", "convenience", "elegant", "city living", "first-class", "comfort", "beachside",
        "urban", "elegant ambiance", "prestigious", "resort-style", "retreat", "work-life", "community living",
        "minimalist design", "luxurious living", "exclusive living", "premium amenities", "luxury lifestyle", "urban living", "designer homes", "first-class living", "high-end living", "premium location", "urban chic"
    ],
    "Types of Residential Properties": [
        "townhouse", "penthouse", "apartment", "glasshouse", "single-family", "duplex", "villa", "cottage", "bungalow",
        "loft", "studio apartment", "mobile home", "mansion", "ranch", "row house", "tiny house", "cluster home",
        "mixed-use", "student housing", "senior living", "digital nomad", "mansion", "luxury apartment", "gated community", "villa", "townhouse", "single-family home", "multi-family house", "condo", "loft", "new construction"
    ],
    "Branded Developments": [
        "armani", "fendi", "missoni", "versace", "bulgari", "baccarat", "porsche", "bentley", "bugatti", "aston martin",
        "branded", "signature collection", "limited edition", "private lift", "concierge", "luxury branded", "exclusive development", "celebrity homes", "branded residences", "luxury brands", "signature homes", "premium developers", "designer homes", "luxury lifestyle"
    ]
}





def get_theme_distribution(data, allow_multiple_themes=True, fuzzy_threshold=60):
    """
    Optimized theme distribution function that uses fuzzy matching but with better performance
    """
    theme_counts = Counter()
    
    # Precompile lowercase keywords for faster matching
    theme_keywords_lower = {
        theme: [keyword.lower() for keyword in keywords] 
        for theme, keywords in THEME_KEYWORDS.items()
    }
    
    # Process all posts more efficiently
    for account in data:
        for post in account.get("posts", []):
            # Create text blob only once per post
            caption = (post.get("caption") or "").lower()
            hashtags = " ".join(tag.lower() for tag in post.get("hashtags", []))
            text_blob = caption + " " + hashtags
            
            matched_themes = set()
            
            # Two-phase matching for better performance:
            # 1. First try exact substring matching (very fast)
            # 2. Only use fuzzy matching if no exact matches found
            
            # Phase 1: Fast substring matching
            for theme, keywords in theme_keywords_lower.items():
                if any(keyword in text_blob for keyword in keywords):
                    matched_themes.add(theme)
                    if not allow_multiple_themes:
                        break
            
            # Phase 2: Only use fuzzy matching if no themes matched and text_blob isn't too short
            if not matched_themes and len(text_blob) > 3:
                # For performance, only check the first 10 keywords of each theme
                for theme, keywords in theme_keywords_lower.items():
                    # Check at most 10 keywords per theme for performance
                    for keyword in list(keywords)[:10]:
                        if len(keyword) > 3:  # Only fuzzy match keywords that are long enough
                            if fuzz.partial_ratio(keyword, text_blob) >= fuzzy_threshold:
                                matched_themes.add(theme)
                                if not allow_multiple_themes:
                                    break
                    if not allow_multiple_themes and matched_themes:
                        break
            
            # Add to theme counts
            if matched_themes:
                for theme in matched_themes:
                    theme_counts[theme] += 1
            else:
                theme_counts["Others"] += 1
    
    return dict(theme_counts)

# Use memoization for even faster repeated calls with the same data
from functools import lru_cache

@lru_cache(maxsize=32)
def fuzzy_match_cached(text, keyword, threshold=80):
    """Cache fuzzy match results to avoid repeat calculations"""
    return fuzz.partial_ratio(keyword, text) >= threshold





# Optimized theme distribution over time function
def get_theme_distribution_over_time(data):
    theme_counts_over_time = {}
    
    # Pre-process keywords once
    theme_keywords_lower = {}
    for theme, keywords in THEME_KEYWORDS.items():
        theme_keywords_lower[theme] = set(keyword.lower() for keyword in keywords)
    
    # Process all posts
    for account in data:
        for post in account.get("posts", []):
            upload_date = post.get("upload_date")
            if not upload_date:
                continue
                
            # Try to parse the date
            try:
                upload_date = datetime.strptime(upload_date, "%Y-%m-%d")
                month_year = upload_date.strftime("%Y-%m")
            except ValueError:
                continue
            
            # Initialize counter for this month if needed
            if month_year not in theme_counts_over_time:
                theme_counts_over_time[month_year] = Counter()
            
            # Prepare text blob
            caption = (post.get("caption") or "").lower()
            hashtags = " ".join(h.lower() for h in post.get("hashtags", []))
            text_blob = caption + " " + hashtags
            
            # Fast matching
            matched = False
            for theme, keywords in theme_keywords_lower.items():
                if any(keyword in text_blob for keyword in keywords):
                    theme_counts_over_time[month_year][theme] += 1
                    matched = True
                    break
            
            if not matched:
                theme_counts_over_time[month_year]["Others"] += 1

    # ✅ No top_theme_limit anymore - include all themes
    theme_data_over_time = []
    for month_year, theme_counts in theme_counts_over_time.items():
        for theme, count in theme_counts.items():
            theme_data_over_time.append({
                "Month": month_year, 
                "Theme": theme, 
                "Post Count": count
            })

    return pd.DataFrame(theme_data_over_time)



def get_top_keywords(data, top_n=10):
    keyword_counts = Counter()

    for account in data:
        for post in account.get("posts", []):
            caption = (post.get("caption") or "").lower()
            hashtags = [h.lower() for h in post.get("hashtags", [])]
            text_blob = caption + " " + " ".join(hashtags)

            # Iterate through all the keywords in THEME_KEYWORDS and count their occurrences
            for theme, keywords in THEME_KEYWORDS.items():
                for keyword in keywords:
                    keyword_counts[keyword] += text_blob.count(keyword)

    # Get the top N keywords
    top_keywords = keyword_counts.most_common(top_n)

    # Convert the dictionary to a DataFrame for easier plotting
    top_keyword_data = [{"Keyword": keyword, "Count": count} for keyword, count in top_keywords]

    return pd.DataFrame(top_keyword_data)


def get_accounts(data):
    rows = []

    for account in data:
        username = account.get("username", "")
        profile_url = f"https://www.instagram.com/{username}"

        for post in account.get("posts", []):
            post_url = post.get("url", "")  # Assuming each post has a `url` field

            rows.append({
                "User Name": username,
                "Full Name": account.get("full_name", ""),
                "Followers": account.get("followers", 0),
                "Following": account.get("following", 0),
                "Countries": account.get("country", ""),
                "Post URL": post_url,  # Each post gets its own URL in a separate row
                "Profile URL": profile_url,
                "External URL": account.get("external_url", ""),
            })
    
    # Convert the rows into a DataFrame
    df = pd.DataFrame(rows)
    return df


def format_number(num):
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)



def get_total_countries(data):
    countries = set()

    for account in data:
        country = account.get("country", "")
        if country:
            countries.add(country)

    return len(countries)