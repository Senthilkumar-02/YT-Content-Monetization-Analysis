from urllib.parse import urlparse, parse_qs
import streamlit as st
import pandas as pd
import pickle
from datetime import date
from googleapiclient.discovery import build
from dateutil import parser

def get_video_id(url):
    if "youtu.be" in url:
        return url.split('/')[-1]
    query = parse_qs(urlparse(url).query)
    return query.get("v", [None])[0]

API_KEY = "AIzaSyBJpJqvfT9N0-ZfaluiQqi1quC8iOr0Aa8"


def get_video_details(video_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    request = youtube.videos().list(
        part="statistics,snippet,contentDetails",
        id=video_id
    )
    response = request.execute()
    if not response["items"]:
        return None

    video = response["items"][0]
    stats = video["statistics"]
    snippet = video["snippet"]
    content_details = video["contentDetails"]
    
    # Convert publish date to datetime
    publish_date = parser.isoparse(snippet["publishedAt"])

    channel_id = snippet["channelId"]
    channel_subs = get_channel_subscribers(channel_id)

    duration = content_details.get("duration", "PT0S")
    duration_td = isoduration_to_minutes(duration)

    views = int(stats.get("viewCount", 0))
    
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "subscribers": channel_subs,  # Only available if you fetch channel stats
        "watch_time_minutes": duration_td * views,  # Estimate (cannot get exact from public API)
        "year": publish_date.year,
        "month": publish_date.month,
        "dayofweek": publish_date.weekday(),
        "category": snippet.get("categoryId", ""),
        "device": "unknown",  # Not available from API
        "country": "unknown"  # Not available from API
    }

def isoduration_to_minutes(duration):
    """
    Convert ISO 8601 duration (PT#H#M#S) to total minutes
    """
    import re
    hours = minutes = seconds = 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if match:
        if match.group(1): hours = int(match.group(1))
        if match.group(2): minutes = int(match.group(2))
        if match.group(3): seconds = int(match.group(3))
    total_minutes = hours * 60 + minutes + seconds / 60
    return total_minutes

def get_channel_subscribers(channel_id):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    request = youtube.channels().list(
        part="statistics",
        id=channel_id
    )
    response = request.execute()
    if response["items"]:
        return int(response["items"][0]["statistics"].get("subscriberCount", 0))
    return 0


st.set_page_config(page_title="YouTube Revenue Prediction", layout="centered")
st.title("📺 YouTube Revenue Prediction Dashboard")
model = pickle.load(open(r"C:\Users\WELCOME\Documents\YT-Analysis\lr.pkl", "rb"))

with st.form(key="video_form"):
    video_url = st.text_input("Enter YouTube Video URL")
    submit_button = st.form_submit_button(label="Fetch & Predict")

if submit_button and video_url:
    video_id = get_video_id(video_url)
    if video_id:
        input_stats = get_video_details(video_id)
        input_stats["engagement_rate"] = (
    (input_stats["likes"] + input_stats["comments"]) / input_stats["views"]
    if input_stats["views"] > 0 else 0
                )
        display_stats = {k: v for k, v in input_stats.items() if k not in ["device", "country"]}
        st.write("✅ Video Stats:", display_stats)
        
        input_data = pd.DataFrame([input_stats])
        try:
            prediction = model.predict(input_data)[0]
            st.success(f"💰 Predicted Revenue: ${prediction:.2f}")
        except Exception as e:
            st.error(f"Error predicting revenue: {e}")
    else:
        st.error("Invalid YouTube URL")