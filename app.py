import os
import base64
import requests
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

SCOPES = "user-read-playback-state user-modify-playback-state streaming"


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES
    }

    print("REDIRECT_URI BEING SENT:", REDIRECT_URI)

    return redirect(f"{AUTH_URL}?{urlencode(params)}")



@app.route("/callback")
def callback():
    code = request.args.get("code")

    auth_header = base64.b64encode(
        f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    ).decode()

    response = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
    )

    token_data = response.json()

    session["access_token"] = token_data.get("access_token")
    session["refresh_token"] = token_data.get("refresh_token")

    return redirect("/language")


@app.route("/language")
def language():
    if "access_token" not in session:
        return redirect("/login")

    return render_template("language.html")


@app.route("/set_language", methods=["POST"])
def set_language():
    session["language"] = request.form.get("language")
    return redirect("/mood")


@app.route("/mood")
def mood():
    if "access_token" not in session:
        return redirect("/login")

    return render_template("mood.html")


@app.route("/search", methods=["POST"])
def search_playlist():
    if "access_token" not in session:
        return redirect("/login")

    language = session.get("language")
    mood = request.form.get("mood")

    # Store mood in session too (optional but cleaner)
    session["mood"] = mood

    if not language or not mood:
        return redirect("/language")

    query = f"{language} {mood} playlist"

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    response = requests.get(
        "https://api.spotify.com/v1/search",
        headers=headers,
        params={
            "q": query,
            "type": "playlist",
            "limit": 5
        }
    )

    data = response.json()
    playlists = data.get("playlists", {}).get("items", [])

    if not playlists:
        return "No playlist found"

    main_playlist = playlists[0]
    suggestions = playlists[1:]

    return render_template(
        "player.html",
        selected_language=language,
        selected_mood=mood,
        language=language,
        mood=mood,
        main_playlist=main_playlist,
        suggestions=suggestions
    )


if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
