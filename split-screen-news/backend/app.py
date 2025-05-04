from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Mock topic card response for "Congestion Pricing"
@app.route('/api/topic/congestion-pricing')
def congestion_pricing():
    return jsonify({
        "topic": "Congestion Pricing",
        "ai_summary": "Coverage of congestion pricing has broken along familiar ideological lines. Left-leaning sources frame it as a climate and equity solution. Right-leaning outlets criticize it as government overreach and a financial burden on working families.",
        "articles": {
            "left": [
                {"title": "A Climate Necessity", "source": "NYT", "snippet": "Reduced emissions and public health benefits...", "url": "https://example.com/nyt"},
                {"title": "Equity Through Tolls", "source": "Vox", "snippet": "Supports congestion pricing as a progressive policy...", "url": "https://example.com/vox"},
                {"title": "Urban Evolution", "source": "NPR", "snippet": "Public transit and walkable cities...", "url": "https://example.com/npr"}
            ],
            "right": [
                {"title": "War on Drivers", "source": "Fox News", "snippet": "Tolls are elitist policy punishing commuters...", "url": "https://example.com/fox"},
                {"title": "Another City Tax Grab", "source": "Daily Wire", "snippet": "Criticizes officials for using climate as a cover...", "url": "https://example.com/dw"},
                {"title": "Toll Tyranny", "source": "Breitbart", "snippet": "Regulation targeting the middle class...", "url": "https://example.com/breitbart"}
            ]
        },
        "comparison": "Left-leaning media supports pricing as part of a climate and justice framework. Right-leaning outlets focus on cost, class tension, and personal freedom.",
        "commentary": {
            "left": [
                {"source": "Slate", "type": "Op-Ed", "quote": "This is the only sane path forward."},
                {"source": "Pod Save America", "type": "Podcast", "quote": "It’s like charging to pollute — that’s progress."}
            ],
            "right": [
                {"source": "WSJ Editorial", "type": "Op-Ed", "quote": "Tolling the middle class again."},
                {"source": "Ben Shapiro Show", "type": "Podcast", "quote": "This is just another tax, let’s be real."}
            ]
        },
        "facts": {
            "summary": "Congestion pricing was first implemented in Singapore (1975)... Reduces traffic by 15–30% where applied.",
            "sources": ["Transportation Research Board", "London Transit Authority", "NY DOT"]
        }
    })

if __name__ == '__main__':
    app.run(debug=True)
