from flask import Flask
from threading import Thread
import logging

app = Flask('')
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Réduit les logs verbeux

@app.route('/')
def home():
    return "Bot en ligne !"

@app.route('/health')
def health():
    return "OK", 200

def run():
    app.run(host='0.0.0.0', port=8080, debug=False)

def keep_alive():
    t = Thread(target=run)
    t.start()
