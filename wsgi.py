from flask import Flask, request
import json
import requests
from settings import TRANSMISSION_URL

app = Flask(__name__)
PAUSED = False


@app.route("/")
def hello():
    with open("releases.html",'br') as f:
        page = f.read()
    return page

@app.route("/start/", methods = ['GET'])
def load_torrent():
    torrent_url = request.args.get('torrent_url')
    transmission_header = get_ttransmission_header()
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
    response =requests.get(TRANSMISSION_URL)
    return {'X-Transmission-Session-Id':response.headers.get('X-Transmission-Session-Id')}

if __name__ == "__main__":
    app.run(debug = True)