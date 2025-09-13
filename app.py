from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

ADMIN_PASSWORD = "your_admin_password"
REQUESTS_FILE = "requests.json"

# Load requests
if not os.path.exists(REQUESTS_FILE):
    with open(REQUESTS_FILE, "w") as f:
        json.dump([], f)

def load_requests():
    with open(REQUESTS_FILE, "r") as f:
        return json.load(f)

def save_requests(data):
    with open(REQUESTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Example in-memory league data
league = {
    "Team A": {
        "matches": [],
        "lineup": ["Player1","Player2","Player3","Player4","Player5","Player6","Player7","Player8"],
        "temp_lineup": [],
        "confirmed_lineups": [],
        "players": {
            "Player1": {"goals":0,"assists":0},
            "Player2": {"goals":0,"assists":0},
            "Player3": {"goals":0,"assists":0},
            "Player4": {"goals":0,"assists":0},
            "Player5": {"goals":0,"assists":0},
            "Player6": {"goals":0,"assists":0},
            "Player7": {"goals":0,"assists":0},
            "Player8": {"goals":0,"assists":0},
        }
    }
}

# ------------------- ROUTES -------------------

@app.route("/")
def league_table():
    """Main page showing all teams"""
    return render_template("teams.html", league=league)  # Revert to your original template

@app.route("/team/<team_name>")
def team_page(team_name):
    team = league.get(team_name)
    if not team:
        return "Team not found", 404
    if not team.get("temp_lineup"):
        team["temp_lineup"] = team["lineup"].copy()
    return render_template("team.html", team=team)

@app.route("/team/<team_name>/request_lineup", methods=["POST"])
def request_lineup(team_name):
    team = league.get(team_name)
    if not team:
        return "Team not found", 404

    user_name = request.form.get("user_name")
    lineup_date = request.form.get("lineup_date")
    lineup = request.form.getlist("lineup")

    if not lineup or not lineup_date or not user_name:
        flash("Please fill out all fields")
        return redirect(url_for("team_page", team_name=team_name))

    team["temp_lineup"] = lineup.copy()

    requests = load_requests()
    requests.append({
        "id": len(requests)+1,
        "user": user_name,
        "type": "lineup",
        "team": team_name,
        "lineup": lineup,
        "date": lineup_date
    })
    save_requests(requests)
    flash("Lineup update request sent!")
    return redirect(url_for("team_page", team_name=team_name))

@app.route("/team/<team_name>/player/<player_name>", methods=["GET","POST"])
def player_page(team_name, player_name):
    team = league.get(team_name)
    if not team or player_name not in team["players"]:
        return "Player not found", 404

    player = team["players"][player_name]

    if request.method == "POST":
        user_name = request.form.get("requester")
        goals = request.form.get("goals")
        assists = request.form.get("assists")
        if not user_name or goals is None or assists is None:
            flash("Please fill out all fields")
            return redirect(url_for("player_page", team_name=team_name, player_name=player_name))

        requests = load_requests()
        requests.append({
            "id": len(requests)+1,
            "user": user_name,
            "type": "player_stats",
            "team": team_name,
            "player": player_name,
            "goals": int(goals),
            "assists": int(assists)
        })
        save_requests(requests)
        flash("Player stats update request sent!")
        return redirect(url_for("player_page", team_name=team_name, player_name=player_name))

    return render_template("player.html", team=team, player=player)

# ------------------- ADMIN -------------------

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_requests"))
        else:
            flash("Incorrect password")
            return redirect(url_for("admin_login"))
    return render_template("admin-login.html")

@app.route("/admin/requests")
def admin_requests():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    requests = load_requests()
    return render_template("admin-requests.html", requests=requests)

@app.route("/admin/requests/approve/<int:request_id>", methods=["POST"])
def approve_request(request_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    requests = load_requests()
    req = next((r for r in requests if r["id"]==request_id), None)
    if not req:
        flash("Request not found")
        return redirect(url_for("admin_requests"))

    team = league[req["team"]]
    if req["type"]=="lineup":
        team["confirmed_lineups"].append({
            "date": req["date"],
            "lineup": req["lineup"]
        })
        team["lineup"] = req["lineup"].copy()
    elif req["type"]=="player_stats":
        player_name = req["player"]
        team["players"][player_name]["goals"] = req["goals"]
        team["players"][player_name]["assists"] = req["assists"]

    requests = [r for r in requests if r["id"]!=request_id]
    save_requests(requests)
    flash("Request approved!")
    return redirect(url_for("admin_requests"))

@app.route("/admin/requests/deny/<int:request_id>", methods=["POST"])
def deny_request(request_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    requests = load_requests()
    requests = [r for r in requests if r["id"]!=request_id]
    save_requests(requests)
    flash("Request denied")
    return redirect(url_for("admin_requests"))

if __name__=="__main__":
    app.run(debug=True)
