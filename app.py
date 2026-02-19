import os
import base64
import requests
import webbrowser
import time
from flask import Flask, render_template, request, redirect, session, url_for
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
PROFILE_URL = "https://api.spotify.com/v1/me"

SCOPES = "user-read-playback-state user-modify-playback-state streaming"


# -----------------------------
# Helper: Refresh Access Token
# -----------------------------
def refresh_access_token():
    if "refresh_token" not in session:
        return False

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
            "grant_type": "refresh_token",
            "refresh_token": session["refresh_token"]
        }
    )

    if response.status_code != 200:
        return False

    token_data = response.json()
    session["access_token"] = token_data.get("access_token")
    session["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)

    return True


# -----------------------------
# Helper: Get Valid Token
# -----------------------------
def get_valid_token():
    if "access_token" not in session:
        return None

    # If token expired, refresh it
    if "expires_at" in session and time.time() > session["expires_at"]:
        success = refresh_access_token()
        if not success:
            return None

    return session.get("access_token")


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    if "access_token" in session:
        return redirect("/language")
    return render_template("index.html")


@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES
    }

    return redirect(f"{AUTH_URL}?{urlencode(params)}")


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return redirect("/")

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

    if response.status_code != 200:
        return "Authentication failed. Please try again."

    token_data = response.json()

    session["access_token"] = token_data.get("access_token")
    session["refresh_token"] = token_data.get("refresh_token")
    session["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)

    return redirect("/language")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)

    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        session["spotify_user"] = profile_data



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/language")
def language():
    token = get_valid_token()
    if not token:
        return redirect("/login")

    return render_template("language.html")


@app.route("/set_language", methods=["POST"])
def set_language():
    session["language"] = request.form.get("language")
    return redirect("/mood")


@app.route("/mood")
def mood():
    token = get_valid_token()
    if not token:
        return redirect("/login")

    return render_template("mood.html")


@app.route("/search", methods=["POST"])
def search_playlist():
    token = get_valid_token()
    if not token:
        return redirect("/login")

    language = session.get("language")
    mood = request.form.get("mood")
    session["mood"] = mood

    if not language or not mood:
        return redirect("/language")

    query = f"{language} {mood} playlist"

    headers = {
        "Authorization": f"Bearer {token}"
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

    if response.status_code != 200:
        return render_template("player.html", error="Failed to fetch playlists. Please try again.")

    data = response.json()
    playlists = data.get("playlists", {}).get("items", [])

    if not playlists:
        return render_template("player.html", error="No playlist found for this mood.")

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
