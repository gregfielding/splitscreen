import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

SOURCE_MAP = {
    "left": ["the-new-york-times", "huffpost"],
    "right": ["fox-news", "breitbart-news"],
    "center": ["reuters", "associated-press"]
}

@app.route('/api/headlines')
def headlines():
    bias = request.args.get("bias", "left")
    sources = SOURCE_MAP.get(bias, ["reuters"])
    
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": NEWSAPI_KEY,
        "sources": ",".join(sources),
        "pageSize": 10
    }
    
    res = requests.get(url, params=params)
    data = res.json()

    headlines = [
        {"title": article["title"], "url": article["url"]}
        for article in data.get("articles", [])
    ]

    return jsonify(headlines)
