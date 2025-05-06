from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

PREFERRED_SOURCES = {
    "New York Times", "CNN", "Fox News", "The Guardian", "NPR",
    "BBC News", "Reuters", "Associated Press", "NBC News", "The Hill",
    "Al Jazeera", "Washington Post"
}

# Scraping utility

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
    api_key = "e2deb908a64f6d8830292dc66d08e0e2"  # Replace with env in production
    url = f"http://api.mediastack.com/v1/news?access_key={api_key}&categories={slug}&languages=en&countries=us&limit=100&sort=published_desc"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        filtered = [a for a in data.get("data", []) if a.get("source") in PREFERRED_SOURCES and a.get("title") and a.get("url")]
        headlines = [
            {
                "title": a["title"],
                "url": a["url"],
                "source": a["source"],
                "description": a.get("description", ""),
                "published_at": a.get("published_at", "")
            } for a in filtered
        ]
        return jsonify({"headlines": headlines})
    except Exception as e:
        logging.error(f"Category fetch failed for {slug}: {e}")
        return jsonify({"headlines": []})

@app.route("/api/health")
def health():
    return jsonify({"message": "Stub for health check."})

if __name__ == '__main__':
    app.run(debug=True)
