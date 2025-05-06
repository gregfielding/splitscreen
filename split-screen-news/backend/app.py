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
    "washingtonpost", "theguardian", "bbc", "bostonherald", "denverpost",
    "latimes", "mercurynews", "ocregister"
]

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

if __name__ == "__main__":
    app.run(debug=True)

