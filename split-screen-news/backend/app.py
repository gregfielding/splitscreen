from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/headlines')
def headlines():
    return jsonify([
        {"title": "Example Left Headline", "url": "https://leftnews.com/example", "bias": "left"},
        {"title": "Example Right Headline", "url": "https://rightnews.com/example", "bias": "right"}
    ])

if __name__ == '__main__':
    app.run()
