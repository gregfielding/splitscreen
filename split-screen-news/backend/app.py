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

PREFERRED_SOURCE_IDS = [
    "forbes", "cbssports.com", "espn", "tmz", "techcrunch",
    "the-new-york-times", "bloomberg-latest-and-live-business", "yahoo-news"
]

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
                'offset': offset,
                'sources': ",".join(PREFERRED_SOURCE_IDS)
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

# Other routes remain unchanged except where sources are used...

@app.route("/api/headlines/raw")
def fetch_mediastack_headlines():
    try:
        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 60,
            'sources': ",".join(PREFERRED_SOURCE_IDS)
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        if response.status_code == 429:
            return jsonify({"error": "Mediastack rate limit hit. Please wait and try again."}), 429
        response.raise_for_status()
        data = response.json()

        articles = [a for a in data.get("data", []) if is_recent(a)]
        articles = dedupe_articles(articles)
        articles = prioritize_articles(articles)

        headlines = [
            {
                "title": a["title"],
                "description": a["description"],
                "url": a["url"],
                "source": a.get("source")
            }
            for a in articles
        ]
        return jsonify({"headlines": headlines})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/topic/<slug>")
def get_topic_data(slug):
    try:
        if slug == "top-headlines":
            res = requests.get(f"{RENDER_URL}/api/headlines/raw")
            data = res.json()
            articles = data.get("headlines", [])
        else:
            def query_articles(keyword):
                params = {
                    'access_key': MEDIASTACK_KEY,
                    'languages': 'en',
                    'countries': 'us',
                    'sort': 'published_desc',
                    'limit': 20,
                    'keywords': keyword,
                    'sources': ",".join(PREFERRED_SOURCE_IDS)
                }
                r = requests.get(MEDIASTACK_URL, params=params)
                if r.status_code == 429:
                    return []
                r.raise_for_status()
                return r.json().get("data", [])

            search_terms = [slug.replace("-", " "), slug.replace("-", ""), slug.split("-")[0]]
            articles = []
            for term in search_terms:
                articles = query_articles(term)
                if articles:
                    break

        articles = [a for a in articles if is_recent(a)]
        deduped = dedupe_articles(articles)
        sorted_articles = prioritize_articles(deduped)
        article_texts = [f"{a.get('source', '')}: {a['title']}" for a in sorted_articles if 'title' in a]
        sample = "\n".join(article_texts[:12])

        prompt = (
            f"Topic: {slug.replace('-', ' ')}\n"
            f"Here are example article headlines:\n{sample}\n\n"
            "Summarize the media coverage of this topic. Compare how left and right-leaning sources are covering it differently."
        )

        chat = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a neutral political analyst summarizing US media bias."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )

        summary = chat.choices[0].message.content.strip()

        return jsonify({
            "topic": slug.replace("-", " ").title(),
            "ai_summary": summary,
            "comparison": "This section will later compare left vs right framing in more detail.",
            "articles": {
                "left": sorted_articles[:3],
                "right": sorted_articles[3:6]
            },
            "commentary": {
                "left": [],
                "right": []
            },
            "facts": {
                "summary": "Placeholder: factual context about this issue goes here.",
                "sources": ["Wikipedia", "Britannica"]
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
