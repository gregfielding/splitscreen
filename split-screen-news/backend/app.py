import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from datetime import datetime, timedelta
import re
from collections import Counter

app = Flask(__name__)
CORS(app)

MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

MEDIASTACK_URL = "https://api.mediastack.com/v1/news"

PREFERRED_SOURCE_IDS = [
    "cnn", "foxnews", "abcnews", "usatoday", "cbsnews", "nbcnews", "reuters",
    "bloomberg", "businessinsider", "forbes", "espn", "cbssports.com", "tmz",
    "techcrunch", "nypost", "thehill", "yahoo-news", "new-york-times",
    "washingtonpost", "theguardian", "bbc", "aljazeera",
    "bostonherald", "denverpost", "latimes", "mercurynews", "ocregister"
]

TOP_STORY_SOURCES = ["cnn", "foxnews", "new-york-times"]

VALID_CATEGORIES = [
    "general", "business", "entertainment", "health", "science", "sports", "technology"
]

CACHE = {
    "data": [],
    "timestamp": None,
    "trending": {},
    "summaries": {}
}

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
            'limit': 80,
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

        phrases = extract_phrases([h["title"] for h in headlines])
        CACHE["trending"][slug] = phrases

        return jsonify({"category": slug, "headlines": headlines})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trending/<slug>")
def get_trending_keywords(slug):
    if slug not in CACHE["trending"]:
        return jsonify({"error": "No trending data yet for this category."}), 404
    return jsonify({"trending": CACHE["trending"][slug]})

@app.route("/api/search")
def search_keywords():
    keyword = request.args.get("q")
    if not keyword:
        return jsonify({"error": "Missing search term"}), 400

    try:
        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 60,
            'sources': ",".join(PREFERRED_SOURCE_IDS),
            'keywords': keyword
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        response.raise_for_status()
        data = response.json().get("data", [])

        filtered = [
            {
                "title": a["title"],
                "description": a.get("description"),
                "url": a["url"],
                "source": a.get("source"),
                "published_at": a.get("published_at")
            }
            for a in data
        ]
        return jsonify({"results": filtered})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/summary")
def generate_summary():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "Missing search query"}), 400

    if query in CACHE["summaries"]:
        return jsonify({"summary": CACHE["summaries"][query]})

    try:
        is_political_prompt = (
            f"Is the following topic political in nature?\n\n"
            f"Topic: {query}\n\n"
            f"Answer 'yes' or 'no'."
        )
        is_political_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": is_political_prompt}
            ],
            temperature=0.3
        )
        verdict = is_political_response.choices[0].message.content.strip().lower()

        if "yes" in verdict:
            prompt = f"Summarize how left-leaning and right-leaning media outlets are covering the topic '{query}'. Be concise but call out any differences in tone or emphasis."
        else:
            prompt = f"Summarize the major news or public events related to '{query}' in 3–5 sentences."

        summary_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert news analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        final_summary = summary_response.choices[0].message.content.strip()
        CACHE["summaries"][query] = final_summary

        return jsonify({"summary": final_summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_phrases(titles):
    phrases = []
    for title in titles:
        clean_title = re.sub(r'["\'\-]', '', title)
        words = clean_title.split()
        for i in range(len(words) - 1):
            if words[i][0].isupper() and words[i+1][0].isupper():
                phrases.append(f"{words[i]} {words[i+1]}")
    counter = Counter(phrases)
    return [phrase for phrase, count in counter.most_common(10)]

@app.route("/api/topstories")
def get_top_stories():
    try:
        now = datetime.utcnow()
        if CACHE["timestamp"] and now - CACHE["timestamp"] < timedelta(minutes=10):
            return jsonify({"top_stories": CACHE["data"]})

        today_str = now.strftime('%Y-%m-%d')
        twenty_four_hours_ago = now - timedelta(hours=24)

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
        ][:8]

        CACHE["data"] = highlights
        CACHE["timestamp"] = now

        return jsonify({"top_stories": highlights})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
