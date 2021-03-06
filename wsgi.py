from flask import Flask, request, redirect
import json
import requests
from settings import TRANSMISSION_URL
from digitalreleases2 import start_create_release_page

app = Flask(__name__)
PAUSED = False


@app.route("/")
def hello():
    with open("releases.html",'br') as f:
        page = f.read()
    return page

@app.route("/reload/", methods = ['GET'])
def refresh_release():
    load_days = int(request.args.get('load_days',7))
    status_code = start_create_release_page(load_days)
    if status_code:
        return "very bad =("
    return redirect('/')

@app.route("/start/", methods = ['GET'])
def load_torrent():
    torrent_url = request.args.get('torrent_url')
    try:
        transmission_header = get_ttransmission_header()
    except ConnectionError:
        return "not connect to transmission"
    data = {"method": "torrent-add",
            "arguments": {
                "paused": PAUSED,
                "filename": torrent_url,
                }
    }
    res = requests.post(TRANSMISSION_URL, json.dumps(data), headers=transmission_header)
    if res:
        return "ok"
    return "bad"


    
    
def get_ttransmission_header() -> str:
    try:
        response =requests.get(TRANSMISSION_URL)
    except requests.ConnectionError:
        app.logger.info("Not connect to transmission")
        raise ConnectionError
    return {'X-Transmission-Session-Id':response.headers.get('X-Transmission-Session-Id')}

if __name__ == "__main__":
    app.run(debug = True)