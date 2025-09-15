from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

JSON_FILE = "teams.json"

# -------------------- JSON Helpers -------------------- #
def load_data():
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -------------------- Login Decorator -------------------- #
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Please login as admin first.")
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)
    return wrapper

# -------------------- Routes -------------------- #
@app.route("/")
def league_table():
    data = load_data()
    teams = list(data.values())

    # calculate leaders
    top_scorer = top_assister = top_ga = None
    max_goals = max_assists = max_ga = -1

    for t in teams:
        for p in t.get("players", []):
            if p.get("goals", 0) > max_goals:
                max_goals = p["goals"]
                top_scorer = p["name"]
            if p.get("assists", 0) > max_assists:
                max_assists = p["assists"]
                top_assister = p["name"]
            ga = p.get("goals", 0) + p.get("assists", 0)
            if ga > max_ga:
                max_ga = ga
                top_ga = p["name"]

    return render_template(
        "index.html",
        teams=teams,
        top_scorer=top_scorer,
        top_assister=top_assister,
        top_ga=top_ga
    )

@app.route("/team/<team_name>", methods=["GET", "POST"])
def team_page(team_name):
    data = load_data()
    team = data.get(team_name)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == "POST":
        flash("Request system disabled in JSON mode.")  # optional
        return redirect(url_for("team_page", team_name=team_name))

    return render_template("team.html", team=team, players=team.get("players", []))

@app.route("/team/<team_name>/player/<player_name>", methods=["GET", "POST"])
def player_page(team_name, player_name):
    data = load_data()
    team = data.get(team_name)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get("players", []) if p["name"] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == "POST":
        flash("Player requests disabled in JSON mode.")  # optional
        return redirect(url_for("player_page", team_name=team_name, player_name=player_name))

    return render_template("player.html", team=team, player=player)

# -------------------- Admin -------------------- #
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            flash("Logged in as admin!")
            return redirect(url_for("league_table"))
        else:
            flash("Incorrect password!")
    return render_template("admin_login.html")

