from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import logging
import os
import openai
import time

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

PREFERRED_SOURCES = {
    "new-york-times", "cnn", "fox-news", "the-guardian", "npr",
    "bbc-news", "reuters", "associated-press", "nbc-news", "the-hill",
    "al-jazeera", "washington-post", "latimes", "denverpost", "ocregister",
    "mercurynews", "bostonherald"
}

MEDIASTACK_API_KEY = os.environ["MEDIASTACK_API_KEY"]
MEDIASTACK_BASE_URL = "http://api.mediastack.com/v1/news"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

seen_titles = set()
def is_duplicate(title):
    t = re.sub(r'[^a-zA-Z0-9 ]', '', title).strip().lower()
    if t in seen_titles:
        return True
    seen_titles.add(t)
    return False

# In-memory cache
cache = {}
CACHE_DURATION = 600  # seconds (10 minutes)

def get_cached(key):
    entry = cache.get(key)
    if entry and (time.time() - entry['timestamp'] < CACHE_DURATION):
        return entry['data']
    return None

def set_cache(key, data):
    cache[key] = {'data': data, 'timestamp': time.time()}

def fetch_mediastack_articles(category):
    cached = get_cached(f"category:{category}")
    if cached:
        return cached
    try:
        params = {
            'access_key': MEDIASTACK_API_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 75,
            'categories': 'general' if category.lower() == 'top-stories' else category
        }
        response = requests.get(MEDIASTACK_BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        articles = []
        seen_titles.clear()
        for a in data.get('data', []):
            source = a.get("source", "").lower()
            if not a.get("title") or not a.get("url") or source not in PREFERRED_SOURCES or is_duplicate(a["title"]):
                continue
            articles.append({
                "title": a["title"],
                "url": a["url"],
                "source": a["source"],
                "description": a.get("description", ""),
                "published_at": a.get("published_at", datetime.utcnow().isoformat())
            })
        set_cache(f"category:{category}", articles)
        return articles
    except Exception as e:
        logging.error(f"Error fetching {category} category: {e}")
        return []

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
    cached = get_cached("topstories")
    if cached:
        return jsonify({"top_stories": cached})
    seen_titles.clear()
    cnn = scrape_homepage("https://www.cnn.com", "h3.cd__headline a", "cnn")
    nyt = scrape_homepage("https://www.nytimes.com", "section[data-block-tracking-id='Top Stories'] h3 a", "new-york-times")
    fox = scrape_homepage("https://www.foxnews.com", "main h2.title a", "fox-news")
    combined = cnn + nyt + fox
    combined = [a for a in combined if a['title'] and a['url'] and a['source'].lower() in PREFERRED_SOURCES]
    set_cache("topstories", combined)
    return jsonify({"top_stories": combined})

@app.route("/api/category/<slug>")
def category(slug):
    logging.info(f"Fetching category: {slug}")
    articles = fetch_mediastack_articles(slug)
    return jsonify({"headlines": articles})

@app.route("/api/trending/<slug>")
def trending(slug):
    logging.info(f"Extracting trending topics for: {slug}")
    articles = fetch_mediastack_articles(slug)
    titles = [a.get("title", "") for a in articles if isinstance(a.get("title"), str)]
    title_text = "\n".join(titles)
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that extracts trending topics from news headlines and summarizes the general theme."},
            {"role": "user", "content": f"From these headlines, summarize what the news is mostly about and return a short paragraph followed by 8-10 trending topic tags:\n{title_text}"}
        ]
        chat = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.4
        )
        content = chat.choices[0].message.content.strip()
        summary_part, *tags_part = content.split("Tags:") if "Tags:" in content else (content, [])
        tags = re.findall(r"\b([A-Z][a-zA-Z0-9\-']{2,})\b", ''.join(tags_part))
        return jsonify({"summary": summary_part.strip(), "trending": list(set(tags))[:10]})
    except Exception as e:
        logging.warning(f"Fallback to keyword extraction: {e}")
        keyword_counts = {}
        for t in titles:
            words = re.findall(r"\b[A-Z][a-z]+\b", t)
            for w in words:
                keyword_counts[w] = keyword_counts.get(w, 0) + 1
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return jsonify({"summary": "", "trending": [kw for kw, _ in sorted_keywords[:10]]})

@app.route("/api/health")
def health():
    return jsonify({"message": "OK"})

if __name__ == '__main__':
    app.run(debug=True)
