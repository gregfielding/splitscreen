import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv("MEDIASTACK_API_KEY")
PREFERRED_SOURCES = {
    "new york times", "cnn", "fox news", "the guardian", "npr",
    "bbc news", "reuters", "associated press", "nbc news", "the hill",
    "al jazeera", "breitbart news", "washington post", "cnbc", "barrons",
    "msnbc", "the wall street journal"
}

@app.route("/api/category/<category>")
def get_category_news(category):
    url = "http://api.mediastack.com/v1/news"
    params = {
        "access_key": API_KEY,
        "languages": "en",
        "countries": "us",
        "sort": "published_desc",
        "limit": 100,
        "keywords": category
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        articles = data.get("data", [])

        # Debug logging
        print("Raw article count:", len(articles))
        print("Returned categories:", set([a.get("category") for a in articles]))
        print("Returned sources:", set([a.get("source") for a in articles]))

        filtered = [
            {
                "title": a.get("title"),
                "url": a.get("url"),
                "source": a.get("source"),
                "image": a.get("image"),
                "published": a.get("published_at")
            }
            for a in articles
            if a.get("source", "").lower() in PREFERRED_SOURCES
        ]
        return jsonify(filtered)
    except Exception as e:
        print("ERROR:", e)
        return jsonify([])

if __name__ == "__main__":
    app.run(debug=True)
