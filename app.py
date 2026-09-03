import os

import spotipy
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from spotipy.oauth2 import SpotifyOAuth


load_dotenv()

app = Flask(__name__)


spotify_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope=(
        "user-read-private "
        "user-read-currently-playing "
        "user-read-recently-played "
        "user-library-read "
        "user-top-read"
    ),
    cache_path=".spotify_cache",
    show_dialog=True
)


def get_spotify_client():
    token_info = spotify_oauth.get_cached_token()

    if not token_info:
        return None

    token_info = spotify_oauth.validate_token(token_info)

    if not token_info:
        return None

    return spotipy.Spotify(auth=token_info["access_token"])


def get_spotify_user():
    spotify = get_spotify_client()

    if not spotify:
        return None

    try:
        profile = spotify.current_user()

        profile_image = None

        if profile.get("images"):
            profile_image = profile["images"][0]["url"]

        return {
            "name": profile.get("display_name") or "Spotify User",
            "image": profile_image
        }

    except spotipy.SpotifyException:
        return None


def get_now_playing():
    spotify = get_spotify_client()

    if not spotify:
        return None

    try:
        current = spotify.current_user_playing_track()

        if not current:
            return None

        if not current.get("is_playing"):
            return None

        track = current.get("item")

        if not track:
            return None

        album_image = None

        if track.get("album") and track["album"].get("images"):
            album_image = track["album"]["images"][0]["url"]

        artists = ", ".join(
            artist["name"]
            for artist in track.get("artists", [])
        )

        return {
            "title": track.get("name") or "N/A",
            "artist": artists or "N/A",
            "image": album_image
        }

    except spotipy.SpotifyException:
        return None


def get_recent_tracks():
    spotify = get_spotify_client()

    if not spotify:
        return []

    try:
        recent = spotify.current_user_recently_played(limit=6)

        tracks = []

        for item in recent.get("items", []):
            track = item.get("track")

            if not track:
                continue

            album_image = None

            if track.get("album") and track["album"].get("images"):
                album_image = track["album"]["images"][0]["url"]

            artists = ", ".join(
                artist["name"]
                for artist in track.get("artists", [])
            )

            tracks.append({
                "title": track.get("name") or "N/A",
                "artist": artists or "N/A",
                "image": album_image
            })

        return tracks

    except spotipy.SpotifyException:
        return []


def get_liked_tracks():
    spotify = get_spotify_client()

    if not spotify:
        return []

    try:
        saved = spotify.current_user_saved_tracks(limit=50)

        tracks = []
        used_artists = set()

        for item in saved.get("items", []):
            track = item.get("track")

            if not track:
                continue

            artists_list = track.get("artists", [])

            if not artists_list:
                continue

            primary_artist = artists_list[0]["name"]

            if primary_artist.lower() in used_artists:
                continue

            used_artists.add(primary_artist.lower())

            album_image = None

            if track.get("album") and track["album"].get("images"):
                album_image = track["album"]["images"][0]["url"]

            artists = ", ".join(
                artist["name"]
                for artist in artists_list
            )

            tracks.append({
                "title": track.get("name") or "N/A",
                "artist": artists or "N/A",
                "image": album_image
            })

            if len(tracks) == 6:
                break

        return tracks

    except spotipy.SpotifyException:
        return []


def get_top_tracks(time_range):
    spotify = get_spotify_client()

    if not spotify:
        return []

    try:
        results = spotify.current_user_top_tracks(
            limit=6,
            time_range=time_range
        )

        tracks = []

        for track in results.get("items", []):
            album_image = None

            if track.get("album") and track["album"].get("images"):
                album_image = track["album"]["images"][0]["url"]

            artists = ", ".join(
                artist["name"]
                for artist in track.get("artists", [])
            )

            tracks.append({
                "title": track.get("name") or "N/A",
                "artist": artists or "N/A",
                "image": album_image
            })

        return tracks

    except spotipy.SpotifyException:
        return []


def get_top_artists(time_range):
    spotify = get_spotify_client()

    if not spotify:
        return []

    try:
        results = spotify.current_user_top_artists(
            limit=6,
            time_range=time_range
        )

        artists = []

        for artist in results.get("items", []):
            artist_image = None

            if artist.get("images"):
                artist_image = artist["images"][0]["url"]

            artists.append({
                "name": artist.get("name") or "N/A",
                "image": artist_image
            })

        return artists

    except spotipy.SpotifyException:
        return []


@app.route("/")
def home():
    user = get_spotify_user()
    now_playing = get_now_playing()
    recent_tracks = get_recent_tracks()
    liked_tracks = get_liked_tracks()

    return render_template(
        "index.html",
        user=user,
        now_playing=now_playing,
        recent_tracks=recent_tracks,
        liked_tracks=liked_tracks
    )


@app.route("/top")
def top_music():
    user = get_spotify_user()

    valid_ranges = {
        "short_term",
        "medium_term",
        "long_term"
    }

    tracks_range = request.args.get("tracks_range", "short_term")
    artists_range = request.args.get("artists_range", "short_term")

    if tracks_range not in valid_ranges:
        tracks_range = "short_term"

    if artists_range not in valid_ranges:
        artists_range = "short_term"

    top_tracks = get_top_tracks(tracks_range)
    top_artists = get_top_artists(artists_range)

    return render_template(
        "top.html",
        user=user,
        top_tracks=top_tracks,
        top_artists=top_artists,
        tracks_range=tracks_range,
        artists_range=artists_range
    )


@app.route("/login")
def login():
    authorization_url = spotify_oauth.get_authorize_url()
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "Spotify authorization failed."

    spotify_oauth.get_access_token(code)

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)