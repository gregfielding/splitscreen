import os
import json
import requests
import openai
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load keys
MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEDIASTACK_URL = "http://api.mediastack.com/v1/news"

openai.api_key = OPENAI_API_KEY

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
        # Fetch headlines
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

        joined_headlines = "\n".join(f"- {title}" for title in headlines)
        prompt = (
            "Group the following U.S. news headlines into 4–6 topic clusters.\n"
            "Return only a valid JSON array of lowercase hyphenated topic slugs like:\n"
            "[\"trump-trial\", \"student-loans\"]\n\n"
            f"Headlines:\n{joined_headlines}"
        )

        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            response_format="json",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        topics = json.loads(chat.choices[0].message.content.strip())
        return jsonify({"topics": topics})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/topic/<slug>")
def get_topic_data(slug):
    try:
        if slug == "top-headlines":
            res = requests.get("http://localhost:5000/api/headlines/raw")
        else:
            params = {
                'access_key': MEDIASTACK_KEY,
                'languages': 'en',
                'countries': 'us',
                'sort': 'published_desc',
                'limit': 20,
                'keywords': slug.replace("-", " ")
            }
            res = requests.get(MEDIASTACK_URL, params=params)

        data = res.json()
        articles = data.get("headlines", []) if slug == "top-headlines" else data.get("data", [])

        article_texts = [f"{a.get('source', '')}: {a['title']}" for a in articles if 'title' in a]
        joined = "\n".join(article_texts[:12])

        prompt = (
            f"Summarize how the media is covering the topic '{slug.replace('-', ' ')}'. "
            "Group coverage into left-leaning and right-leaning perspectives where possible. "
            f"Here are some article headlines:\n{joined}"
        )

        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful, unbiased political media analyst."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4
        )

        summary = chat.choices[0].message.content.strip()

        return jsonify({
            "topic": slug.replace("-", " ").title(),
            "ai_summary": summary,
            "comparison": "This is placeholder comparison content.",
            "articles": {
                "left": articles[:3],
                "right": articles[3:6]
            },
            "commentary": {
                "left": [],
                "right": []
            },
            "facts": {
                "summary": "Placeholder for factual context.",
                "sources": ["Wikipedia"]
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
