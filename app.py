from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# -------------------- Helpers -------------------- #
def load_teams():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_teams(teams):
    with open(DATA_FILE, 'w') as f:
        json.dump(teams, f, indent=4)

def load_requests():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_requests(requests_data):
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests_data, f, indent=4)

# -------------------- Routes -------------------- #
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team.setdefault('players', [])
        team.setdefault('wins', 0)
        team.setdefault('draws', 0)
        team.setdefault('goals_for', 0)
        team.setdefault('goals_against', 0)
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins'] * 3 + team['draws']

    # cumulative stats across all teams
    player_totals = {}
    for team in teams:
        for player in team.get('players', []):
            name = player['name']
            player_totals.setdefault(name, {'goals':0, 'assists':0, 'teams':{}})
            player_totals[name]['goals'] += player.get('goals', 0)
            player_totals[name]['assists'] += player.get('assists', 0)
            player_totals[name]['teams'][team['name']] = {'goals': player.get('goals',0), 'assists': player.get('assists',0)}

    top_scorer = max(player_totals.items(), key=lambda x: x[1]['goals'], default=(None, None))[0]
    top_assister = max(player_totals.items(), key=lambda x: x[1]['assists'], default=(None, None))[0]

    return render_template('index.html', teams=teams, top_scorer=top_scorer,
                           top_assister=top_assister, player_totals=player_totals)

@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    team.setdefault('temp_lineup', [])
    team.setdefault('confirmed_lineups', [])
    team.setdefault('players', [])

    if request.method == 'POST' and request.form.get('request_type') == 'lineup':
        user_name = request.form.get('user_name') or "Anonymous"
        lineup_date = request.form.get('lineup_date') or ""
        temp_lineup_names = [n.strip() for n in request.form.getlist('lineup') if n.strip()]
        team['temp_lineup'] = temp_lineup_names

        requests_data = load_requests()
        new_request = {
            "id": len(requests_data)+1,
            "user": user_name,
            "team": team_name,
            "type": "lineup",
            "lineup": temp_lineup_names,
            "player": None,
            "goals": None,
            "assists": None,
            "date": lineup_date
        }
        requests_data.append(new_request)
        save_requests(requests_data)

        flash("Lineup request sent!")
        return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name']==team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name']==player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    player.setdefault('goals', 0)
    player.setdefault('assists', 0)

    if request.method == 'POST' and request.form.get('request_type') == 'player':
        requester = request.form.get('requester') or "Anonymous"
        try: goals = int(request.form.get('goals', player['goals']))
        except: goals = player['goals']
        try: assists = int(request.form.get('assists', player['assists']))
        except: assists = player['assists']

        requests_data = load_requests()
        new_request = {
            "id": len(requests_data)+1,
            "user": requester,
            "team": team_name,
            "type": "player",
            "lineup": None,
            "player": player_name,
            "goals": goals,
            "assists": assists,
            "date": None
        }
        requests_data.append(new_request)
        save_requests(requests_data)
        flash("Player stats request sent!")
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    cumulative_goals = 0
    cumulative_assists = 0
    per_team_stats = {}
    for t in teams:
        for p in t.get('players', []):
            if p['name'] == player_name:
                cumulative_goals += p.get('goals',0)
                cumulative_assists += p.get('assists',0)
                per_team_stats[t['name']] = {'goals': p.get('goals',0), 'assists': p.get('assists',0)}

    return render_template('player.html', team=team, player=player,
                           cumulative_goals=cumulative_goals,
                           cumulative_assists=cumulative_assists,
                           per_team_stats=per_team_stats)

# ---------------- Delete Lineup Request ---------------- #
@app.route('/team/<team_name>/lineup/delete', methods=['POST'])
def team_delete_lineup_request(team_name):
    lineup_date = request.form.get('lineup_date')
    requests_data = load_requests()
    new_request = {
        "id": len(requests_data) + 1,
        "user": "Anonymous",
        "team": team_name,
        "type": "delete_lineup",
        "lineup": None,
        "player": None,
        "goals": None,
        "assists": None,
        "date": lineup_date
    }
    requests_data.append(new_request)
    save_requests(requests_data)
    flash("Delete lineup request sent!")
    return redirect(url_for('team_page', team_name=team_name))

if __name__ == '__main__':
    app.run(debug=True)
