import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS
from openai import OpenAI
from datetime import datetime, timedelta
import re

app = Flask(__name__)
CORS(app)

MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

MEDIASTACK_URL = "https://api.mediastack.com/v1/news"
RENDER_URL = "https://splitscreen-jkbx.onrender.com"

PREFERRED_SOURCE_IDS = [
    "cnn", "foxnews", "abcnews", "usatoday", "cbsnews", "nbcnews", "reuters",
    "bloomberg", "businessinsider", "forbes", "espn", "cbssports.com", "tmz",
    "techcrunch", "nypost", "thehill", "yahoo-news", "new-york-times",
    "washingtonpost", "theguardian", "bbc", "aljazeera",
    "bostonherald", "denverpost", "latimes", "mercurynews", "ocregister"
]

TOP_STORY_SOURCES = ["cnn", "foxnews", "the-new-york-times"]

VALID_CATEGORIES = [
    "general", "business", "entertainment", "health", "science", "sports", "technology"
]

@app.route("/")
def index():
    return "✅ Flask backend is live."

@app.route("/api/category/<slug>")
def get_category_news(slug):
    if slug not in VALID_CATEGORIES:
        return jsonify({"error": "Invalid category."}), 400
    try:
        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 40,
            'sources': ",".join(PREFERRED_SOURCE_IDS),
            'categories': slug
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        response.raise_for_status()
        data = response.json()
        articles = data.get("data", [])

        headlines = [
            {
                "title": a["title"],
                "description": a.get("description"),
                "url": a["url"],
                "source": a.get("source"),
                "published_at": a.get("published_at")
            }
            for a in articles
        ]
        return jsonify({"category": slug, "headlines": headlines})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/topstories")
def get_top_stories():
    try:
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 50,
            'sources': ",".join(TOP_STORY_SOURCES),
            'date': today_str
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        response.raise_for_status()
        raw_articles = response.json().get("data", [])

        front_page_worthy = []
        for article in raw_articles:
            pub_date_str = article.get("published_at")
            if not pub_date_str:
                continue
            try:
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%S+0000")
                if pub_date < twenty_four_hours_ago:
                    continue
            except:
                continue

            title = article.get("title")
            description = article.get("description")
            if not title:
                continue
            prompt = (
                f"Title: {title}\n"
                f"Description: {description or ''}\n"
                "Is this article about a major national or international news story likely to appear on the front page of Apple News, CNN, or the NY Times today? Answer 'yes' or 'no'."
            )
            try:
                result = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a political editor deciding what stories deserve national front-page attention."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                verdict = result.choices[0].message.content.lower()
                if "yes" in verdict:
                    front_page_worthy.append(article)
            except Exception as e:
                print(f"AI error on article: {e}")
                continue

        highlights = [
            {
                "title": a["title"],
                "description": a.get("description"),
                "url": a["url"],
                "source": a.get("source"),
                "published_at": a.get("published_at")
            }
            for a in front_page_worthy
        ][:8]  # limit to top 8 results

        return jsonify({"top_stories": highlights})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
