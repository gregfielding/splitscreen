from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import logging
import os

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

PREFERRED_SOURCES = {
    "New York Times", "CNN", "Fox News", "The Guardian", "NPR",
    "BBC News", "Reuters", "Associated Press", "NBC News", "The Hill",
    "Al Jazeera", "Washington Post"
}

MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY") or "e2deb908a64f6d8830292dc66d08e0e2"
MEDIASTACK_BASE_URL = "http://api.mediastack.com/v1/news"

# UTIL: clean titles
seen_titles = set()
def is_duplicate(title):
    t = re.sub(r'[^a-zA-Z0-9 ]', '', title).strip().lower()
    if t in seen_titles:
        return True
    seen_titles.add(t)
    return False

# UTIL: fetch from MediaStack with filters
def fetch_mediastack_articles(category):
    try:
        params = {
            'access_key': MEDIASTACK_API_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 75,
            'categories': category
        }
        response = requests.get(MEDIASTACK_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        articles = []
        for a in data.get('data', []):
            if not a.get("title") or not a.get("url"):
                continue
            if a["source"] not in PREFERRED_SOURCES or is_duplicate(a["title"]):
                continue
            articles.append({
                "title": a["title"],
                "url": a["url"],
                "source": a["source"],
                "description": a.get("description", ""),
                "published_at": a.get("published_at", datetime.utcnow().isoformat())
            })
        return articles
    except Exception as e:
        logging.error(f"Error fetching {category} category: {e}")
        return []

# TOP STORIES (from homepage scraping)
def scrape_homepage(url, selector, source_name):
    try:
        response = requests.get(url, timeout=6)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.select(selector)
        headlines = []
        for el in elements:
            title = el.get_text(strip=True)
            href = el.get("href")
            if not title or not href:
                continue
            if not href.startswith("http"):
                href = requests.compat.urljoin(url, href)
            if is_duplicate(title):
                continue
            headlines.append({
                "title": title,
                "url": href,
                "source": source_name,
                "published_at": datetime.utcnow().isoformat(),
                "description": ""
            })
        logging.info(f"{source_name} found {len(headlines)} headlines")
        return headlines
    except Exception as e:
        logging.error(f"Error scraping {source_name}: {e}")
        return []

@app.route("/api/topstories")
def top_stories():
    cnn = scrape_homepage("https://www.cnn.com", "h3.cd__headline a", "CNN")
    nyt = scrape_homepage("https://www.nytimes.com", "section[data-block-tracking-id='Top Stories'] h3 a", "New York Times")
    fox = scrape_homepage("https://www.foxnews.com", "main h2.title a", "Fox News")

    combined = cnn + nyt + fox
    combined = [a for a in combined if a['title'] and a['url'] and a['source'] in PREFERRED_SOURCES]
    return jsonify({"top_stories": combined})

@app.route("/api/category/<slug>")
def category(slug):
    logging.info(f"Fetching category: {slug}")
    articles = fetch_mediastack_articles(slug)
    return jsonify({"headlines": articles})

@app.route("/api/health")
def health():
    return jsonify({"message": "OK"})

if __name__ == '__main__':
    app.run(debug=True)
