import os
import requests
import openai
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MEDIASTACK_KEY = os.getenv("MEDIASTACK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MEDIASTACK_URL = "http://api.mediastack.com/v1/news"
openai.api_key = OPENAI_API_KEY

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
            "Return a JSON array of lowercase hyphenated topic slugs like ['trump-trial', 'student-loans'] based on the content.\n"
            f"Headlines:\n{joined_headlines}"
        )

        chat = openai.ChatCompletion.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs clean JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        result = chat.choices[0].message.content.strip()
        return jsonify({"topics": eval(result)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
