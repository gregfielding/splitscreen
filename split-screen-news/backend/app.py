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

PREFERRED_SOURCES = {
    "New York Times", "CNN", "Fox News", "The Guardian", "NPR",
    "BBC News", "Reuters", "Associated Press", "NBC News", "The Hill", "Al Jazeera",
    "Breitbart News"
}

@app.route("/")
def index():
    return "✅ Flask backend is live."

@app.route("/api/sources/live")
def get_live_sources():
    try:
        all_sources = set()
        for offset in [0, 100, 200, 300, 400]:
            params = {
                'access_key': MEDIASTACK_KEY,
                'languages': 'en',
                'countries': 'us',
                'sort': 'published_desc',
                'limit': 100,
                'offset': offset
            }
            response = requests.get(MEDIASTACK_URL, params=params)
            response.raise_for_status()
            data = response.json()
            all_sources.update(
                a.get("source") for a in data.get("data", []) if a.get("source")
            )

        return jsonify({"sources": sorted(all_sources)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# all other routes unchanged...

if __name__ == "__main__":
    app.run(debug=True)
