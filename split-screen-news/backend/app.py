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

# Helper to fetch headlines from a given URL using basic scraping
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
    combined = [a for a in combined if a['title'] and a['url']]
    return jsonify({"top_stories": combined})

@app.route("/api/health")
def health():
    return jsonify({"message": "Stub for health check."})

if __name__ == '__main__':
    app.run(debug=True)
