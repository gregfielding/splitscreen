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

MEDIASTACK_URL = "http://api.mediastack.com/v1/news"
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
            'limit': 40
        }
        response = requests.get(MEDIASTACK_URL, params=params)
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
def get_top_topics():
    try:
        params = {
            'access_key': MEDIASTACK_KEY,
            'languages': 'en',
            'countries': 'us',
            'sort': 'published_desc',
            'limit': 40
        }
        response = requests.get(MEDIASTACK_URL, params=params)
        response.raise_for_status()
        data = response.json()
        headlines = [article["title"] for article in data.get("data", [])]

        joined = "\n".join(f"- {title}" for title in headlines)
        prompt = (
            "You are a media analyst. Group these headlines into 4-6 story clusters and return "
            "a JSON array of lowercase hyphenated topic slugs like: [\"trump-trial\", \"student-loans\"]\n\n"
            f"{joined}"
        )

        chat = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = chat.choices[0].message.content.strip()
        topics = json.loads(content)
        return jsonify({"topics": topics})

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
            params = {
                'access_key': MEDIASTACK_KEY,
                'languages': 'en',
                'countries': 'us',
                'sort': 'published_desc',
                'limit': 20,
                'keywords': slug.replace("-", " ")
            }
            response = requests.get(MEDIASTACK_URL, params=params)
            response.raise_for_status()
            data = response.json()
            articles = data.get("data", [])

        article_texts = [f"{a.get('source', '')}: {a['title']}" for a in articles if 'title' in a]
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
                "left": articles[:3],
                "right": articles[3:6]
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

def dedupe_stories(stories):
    seen = set()
    unique = []
    for s in stories:
        key = s["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique

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

        deduped = dedupe_stories(results)
        return jsonify({"top_stories": deduped})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
