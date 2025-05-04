import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
MEDIASTACK_URL = "http://api.mediastack.com/v1/news"

@app.route("/")
def index():
    return "✅ Flask backend is live."

@app.route("/api/headlines/raw")
def fetch_mediastack_headlines():
    if not MEDIASTACK_KEY:
        return jsonify({"error": "MEDIASTACK_API_KEY not set"}), 500

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

# Debug: Show all registered routes in the logs
with app.app_context():
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(rule)

if __name__ == "__main__":
    app.run(debug=True)
