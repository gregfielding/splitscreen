import os
import json
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from openai import OpenAI

# Flask setup
app = Flask(__name__)
CORS(app)

# API Keys
MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI client
client = OpenAI(api_key=OPENAI_KEY)

MEDIASTACK_URL = "http://api.mediastack.com/v1/news"


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
        # Step 1: Fetch latest headlines
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

        # Step 2: Ask OpenAI to generate topic clusters
        joined = "\n".join(f"- {title}" for title in headlines)
        prompt = (
            "You are a media analyst. Group these headlines into 4-6 story clusters and return "
            "a JSON array of lowercase hyphenated topic slugs like:\n"
            "[\"trump-trial\", \"student-loans\", \"congestion-pricing\"]\n\n"
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
            # Use the cached results
            res = requests.get("http://localhost:5000/api/headlines/raw")
            data = res.json()
            articles = data.get("headlines", [])
        else:
            # Fresh search based on topic
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

        # Shorten titles for OpenAI
        article_texts = [f"{a.get('source', '')}: {a['title']}" for a in articles if 'title' in a]
        sample = "\n".join(article_texts[:12])

        prompt = (
            f"Topic: {slug.replace('-', ' ')}\n"
            f"Here are example article headlines:\n{sample}\n\n"
            "Summarize the media coverage of this topic. "
            "Compare how left and right-leaning sources are covering it differently. "
            "Make it insightful but brief."
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


if __name__ == "__main__":
    app.run(debug=True)
