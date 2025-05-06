import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

MEDIASTACK_API_KEY = os.environ.get("MEDIASTACK_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Preferred sources formatted to match Mediastack
PREFERRED_SOURCES = {
    "the-new-york-times",
    "cnn",
    "fox-news",
    "the-guardian",
    "npr",
    "bbc-news",
    "reuters",
    "associated-press",
    "nbc-news",
    "the-hill",
    "al-jazeera",
    "breitbart-news",
    "washington-post",
    "barrons",
    "the-wall-street-journal",
    "msnbc",
    "cnbc"
}

@app.route("/api/category/<category>")
def get_category_news(category):
    try:
        print(f"Fetching category: {category}")

        url = "http://api.mediastack.com/v1/news"
        params = {
            "access_key": MEDIASTACK_API_KEY,
            "languages": "en",
            "countries": "us",
            "sort": "published_desc",
            "limit": 75,
            "keywords": category,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json().get("data", [])

        # Normalize sources and log what was returned
        sources = set(a.get("source", "").lower().replace(" ", "-") for a in articles if a.get("source"))
        print("Sources from Mediastack:", sources)

        # Filter articles by preferred sources only
        filtered = [
            {
                "title": a["title"],
                "url": a["url"],
                "source": a["source"],
                "image": a.get("image"),
                "published": a.get("published_at")
            }
            for a in articles
            if a.get("title") and a.get("url") and a.get("source")
            and a.get("source", "").lower().replace(" ", "-") in PREFERRED_SOURCES
        ]

        return jsonify(filtered)
    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "Split Screen API Running"

if __name__ == "__main__":
    app.run(debug=True)
