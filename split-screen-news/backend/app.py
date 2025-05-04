import os
import json
import re
import requests
import openai
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load API keys from environment variables
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
        # Step 1: Fetch headlines from Mediastack
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

        # Step 2: Use OpenAI to cluster topics
        joined_headlines = "\n".join(f"- {title}" for title in headlines)
        prompt = (
            "You are a political news analyst. Group the following U.S. news headlines into 4-6 topic clusters. "
            "Return a JSON array of lowercase hyphenated topic slugs like ['trump-trial', 'student-loans'].\n"
            f"Headlines:\n{joined_headlines}"
        )

        chat = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs clean JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        raw = chat.choices[0].message.content.strip()

        # Extract list-like content
        match = re.search(r"\[(.*?)\]", raw, re.DOTALL)
        if not match:
            return jsonify({"error": "OpenAI response not parsable", "raw": raw}), 500

        json_string = "[" + match.group(1).strip() + "]"
        topics = json.loads(json_string)

        return jsonify({"topics": topics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/topic/<slug>")
def get_topic_mock(slug):
    return jsonify({
        "topic": slug.replace("-", " ").title(),
        "ai_summary": "This is a placeholder summary explaining how this topic is portrayed across news sources.",
        "comparison": "The left tends to emphasize systemic causes, while the right emphasizes individual responsibility.",
        "articles": {
            "left": [
                {"title": "Progressive Policy Update", "url": "#", "source": "NYT", "snippet": "Liberal take on recent events."},
                {"title": "Rights and Regulation", "url": "#", "source": "CNN", "snippet": "A look at what's at stake from the left."},
                {"title": "Workers and Equity", "url": "#", "source": "MSNBC", "snippet": "Discussion on fairness and equality."}
            ],
            "right": [
                {"title": "Freedom or Control?", "url": "#", "source": "Fox News", "snippet": "A conservative look at the issue."},
                {"title": "Government Overreach", "url": "#", "source": "Daily Wire", "snippet": "Right-leaning perspective on regulation."},
                {"title": "Taxes and Tyranny", "url": "#", "source": "Breitbart", "snippet": "Fears of expanding state power."}
            ]
        },
        "commentary": {
            "left": [
                {"source": "Slate", "type": "op-ed", "quote": "This policy will help everyday Americans."},
                {"source": "Pod Save America", "type": "podcast", "quote": "A bold step in the right direction."}
            ],
            "right": [
                {"source": "Ben Shapiro Show", "type": "podcast", "quote": "A dangerous overreach by the government."},
                {"source": "National Review", "type": "op-ed", "quote": "Another sign of leftist excess."}
            ]
        },
        "facts": {
            "summary": "Congestion pricing was first proposed in 1952, with major adoption in cities like London and Singapore.",
            "sources": ["Wikipedia", "Britannica", "Brookings"]
        }
    })

if __name__ == "__main__":
    app.run(debug=True)
