from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

REQUESTS_FILE = "requests.json"

# Create requests file if missing
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
    "Zameer": {
        "matches": [],
        "lineup": ["Zameer","Jordan","Fernando","Player4","Player5","Player6","Player7","Player8"],
        "temp_lineup": [],
        "confirmed_lineups": [],
        "players": {
            "Zameer": {"goals":0,"assists":0},
            "Jordan": {"goals":0,"assists":0},
            "Fernando": {"goals":0,"assists":0},
            "Player4": {"goals":0,"assists":0},
            "Player5": {"goals":0,"assists":0},
            "Player6": {"goals":0,"assists":0},
            "Player7": {"goals":0,"assists":0},
            "Player8": {"goals":0,"assists":0},
        }
    },
    "Jordan": {
        "matches": [],
        "lineup": ["Player1","Player2","Player3","Player4","Player5","Player6","Player7","Player8"],
        "temp_lineup": [],
        "confirmed_lineups": [],
        "players": {f"Player{i}": {"goals":0,"assists":0} for i in range(1,9)}
    },
    "Fernando": {
        "matches": [],
        "lineup": ["Player1","Player2","Player3","Player4","Player5","Player6","Player7","Player8"],
        "temp_lineup": [],
        "confirmed_lineups": [],
        "players": {f"Player{i}": {"goals":0,"assists":0} for i in range(1,9)}
    }
}

@app.route("/")
def league_table():
    return render_template("teams.html", league=league)

@app.route("/team/<team_name>")
def team_page(team_name):
    team = league.get(team_name)
    if not team:
        return "Team not found", 404
    if not team.get("temp_lineup"):
        team["temp_lineup"] = team["lineup"].copy()
    return render_template("teams.html", team=team)

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

    # Save temp lineup
    team["temp_lineup"] = lineup.copy()

    # Save request
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

        # Save request only
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

if __name__=="__main__":
    app.run(debug=True)
