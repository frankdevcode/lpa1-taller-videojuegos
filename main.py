# programa principal

from flask import Flask, render_template, jsonify, request, send_from_directory
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory('static/assets', path)

if __name__ == '__main__':
    app.run(debug=True)
