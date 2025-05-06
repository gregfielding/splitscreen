import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from bs4 import BeautifulSoup
from openai import OpenAI

app = Flask(__name__)
CORS(app)

HEADERS = {"User-Agent": "Mozilla/5.0"}
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def scrape_cnn():
    url = "https://www.cnn.com"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("h3.cd__headline a")
    headlines = []
    for link in links[:15]:
        title = link.get_text(strip=True)
        href = link.get("href")
        if href and not href.startswith("http"):
            href = f"https://www.cnn.com{href}"
        headlines.append({"title": title, "url": href, "source": "CNN"})
    print(f"cnn found {len(headlines)} headlines")
    return headlines

def scrape_nyt():
    url = "https://www.nytimes.com"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    articles = soup.select("section[data-block-tracking-id='Top Stories'] h3 a")
    headlines = []
    for article in articles[:15]:
        title = article.get_text(strip=True)
        href = article.get("href")
        if href and not href.startswith("http"):
            href = f"https://www.nytimes.com{href}"
        headlines.append({"title": title, "url": href, "source": "New York Times"})
    print(f"new-york-times found {len(headlines)} headlines")
    return headlines

def scrape_fox():
    url = "https://www.foxnews.com"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    articles = soup.select("main article h2.title a")
    headlines = []
    for article in articles[:15]:
        title = article.get_text(strip=True)
        href = article.get("href")
        if href and not href.startswith("http"):
            href = f"https://www.foxnews.com{href}"
        headlines.append({"title": title, "url": href, "source": "Fox News"})
    print(f"fox-news found {len(headlines)} headlines")
    return headlines

@app.route("/api/topstories")
def top_stories():
    try:
        all_stories = scrape_cnn() + scrape_nyt() + scrape_fox()
        print(f"✅ Total scraped top stories: {len(all_stories)}")
        return jsonify(all_stories)
    except Exception as e:
        print(f"ERROR scraping top stories: {e}")
        return jsonify([])

@app.route("/api/summarize", methods=["POST"])
def summarize():
    try:
        data = request.json
        titles = data.get("titles", [])
        if not titles or not isinstance(titles, list):
            return jsonify({"summary": "No headlines to summarize."})

        prompt = "Summarize the following news headlines:\n" + "\n".join(titles)
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return jsonify({"summary": response.choices[0].message.content.strip()})
    except Exception as e:
        print(f"AI summary error: {e}")
        return jsonify({"summary": "Unable to generate summary at this time."})

if __name__ == "__main__":
    app.run(debug=True)
