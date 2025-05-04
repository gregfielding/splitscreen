import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

MEDIASTACK_URL = "https://api.mediastack.com/v1/news"
RENDER_URL = "https://splitscreen-jkbx.onrender.com"

@app.route("/")
def index():
    return "✅ Flask backend is live."

@app.route("/api/headlines/raw")
def fetch_mediastack_headlines():
    try:
        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 60
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        if response.status_code == 429:
            return jsonify({"error": "Mediastack rate limit hit. Please wait and try again."}), 429
        response.raise_for_status()
        data = response.json()

        headlines = [
            {
                "title": article["title"],
                "description": article["description"],
                "url": article["url"],
                "source": article.get("source")
            }
            for article in data.get("data", [])
        ]
        return jsonify({"headlines": headlines})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/topics/today")
def get_dynamic_topic_map():
    try:
        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 60
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        if response.status_code == 429:
            return jsonify({"error": "Mediastack rate limit hit. Please wait and try again."}), 429
        response.raise_for_status()
        data = response.json()

        headlines = [article["title"] for article in data.get("data", []) if article.get("title")]
        joined = "\n".join(f"- {title}" for title in headlines)

        prompt = (
            "Group these headlines into 8–12 topic categories. Return a JSON object with category labels as keys and "
            "lists of 2–5 lowercase hyphenated topic slugs as values. Example:\n"
            "{\"Politics\": [\"trump-trial\", \"student-loans\"]}\n\n"
            f"Headlines:\n{joined}"
        )

        chat = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        structured = json.loads(chat.choices[0].message.content.strip())
        return jsonify(structured)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def dedupe_articles(articles):
    seen = set()
    unique = []
    for a in articles:
        key = a["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique

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
                    'keywords': keyword
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

        deduped = dedupe_articles(articles)
        article_texts = [f"{a.get('source', '')}: {a['title']}" for a in deduped if 'title' in a]
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
                "left": deduped[:3],
                "right": deduped[3:6]
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

@app.route("/api/topstories")
def get_top_stories():
    try:
        sources = {
            "CNN": "https://www.cnn.com",
            "Fox News": "https://www.foxnews.com",
            "NYT": "https://www.nytimes.com",
            "NPR": "https://www.npr.org"
        }

        results = []

        for name, url in sources.items():
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            if "cnn.com" in url:
                headlines = soup.select("h3.cd__headline a")
            elif "foxnews.com" in url:
                headlines = soup.select("h2.title a")
            elif "nytimes.com" in url:
                headlines = soup.select("section[data-block-tracking-id='Top Stories'] h3")
            elif "npr.org" in url:
                headlines = soup.select(".story-text h3.title a")
            else:
                headlines = []

            for h in headlines[:2]:
                text = h.get_text(strip=True)
                link = h.get("href")
                if not link.startswith("http"):
                    link = url + link
                results.append({"source": name, "title": text, "url": link})

        deduped = dedupe_articles(results)
        return jsonify({"top_stories": deduped})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
