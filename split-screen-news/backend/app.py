import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
import openai
from collections import Counter
import re

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")
MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY")

HEADERS = {"User-Agent": "Mozilla/5.0"}

PREFERRED_SOURCES = {
 "new-york-times", "cnn", "fox-news", "the-guardian", "npr",
 "bbc-news", "reuters", "associated-press", "nbc-news", "the-hill",
 "al-jazeera", "washington-post", "latimes", "denverpost", "ocregister",
 "mercurynews", "bostonherald"
}

def scrape_cnn():
    res = requests.get("https://www.cnn.com", headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("h3.cd__headline a")
    return [
        {
            "title": link.get_text(strip=True),
            "url": f"https://www.cnn.com{link.get('href')}" if not link.get("href").startswith("http") else link.get("href"),
            "source": "CNN"
        }
        for link in links[:15] if link.get("href")
    ]

def scrape_nyt():
    res = requests.get("https://www.nytimes.com", headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("section[data-block-tracking-id='Top Stories'] h3 a")
    return [
        {
            "title": link.get_text(strip=True),
            "url": f"https://www.nytimes.com{link.get('href')}" if not link.get("href").startswith("http") else link.get("href"),
            "source": "New York Times"
        }
        for link in links[:15] if link.get("href")
    ]

def scrape_fox():
    res = requests.get("https://www.foxnews.com", headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("main article h2.title a")
    return [
        {
            "title": link.get_text(strip=True),
            "url": f"https://www.foxnews.com{link.get('href')}" if not link.get("href").startswith("http") else link.get("href"),
            "source": "Fox News"
        }
        for link in links[:15] if link.get("href")
    ]

@app.route("/api/topstories")
def top_stories():
    try:
        stories = scrape_cnn() + scrape_nyt() + scrape_fox()
        return jsonify(stories)
    except Exception as e:
        print(f"Top stories error: {e}")
        return jsonify([])

@app.route("/api/category/<category>")
def category_news(category):
    try:
        url = "http://api.mediastack.com/v1/news"
        params = {
            "access_key": MEDIASTACK_API_KEY,
            "languages": "en",
            "countries": "us",
            "sort": "published_desc",
            "limit": 50,
            "keywords": category
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        articles = res.json().get("data", [])
        filtered = [
            {
                "title": a["title"],
                "url": a["url"],
                "source": a["source"]
            }
            for a in articles
            if a.get("source") and a.get("source").lower().replace(" ", "-") in PREFERRED_SOURCES
        ]
        return jsonify(filtered)
    except Exception as e:
        print(f"Category fetch error ({category}): {e}")
        return jsonify([])

@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        titles = request.json.get("titles", [])
        if not titles or not isinstance(titles, list):
            return jsonify({"summary": "No headlines to summarize."})

        prompt = "Summarize the following headlines:\n" + "\n".join(titles)
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return jsonify({"summary": response.choices[0].message.content.strip()})
    except Exception as e:
        print(f"AI summary error: {e}")
        return jsonify({"summary": "Unable to generate summary."})

@app.route("/api/trending/<category>")
def trending_topics(category):
    try:
        url = "http://api.mediastack.com/v1/news"
        params = {
            "access_key": MEDIASTACK_API_KEY,
            "languages": "en",
            "countries": "us",
            "sort": "published_desc",
            "limit": 50,
            "keywords": category
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        articles = res.json().get("data", [])
        titles = [a["title"] for a in articles if a.get("title")]

        text = " ".join(titles)
        keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        counts = Counter(keywords)
        top = [k for k, v in counts.most_common(10) if len(k.split()) <= 3]

        return jsonify({"trending": top})
    except Exception as e:
        print(f"Trending topics error ({category}): {e}")
        return jsonify({"trending": []})

if __name__ == "__main__":
    app.run(debug=True)
