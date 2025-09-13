from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')

TEAMS_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'

# --- Load and Save Functions ---
def load_teams():
    if os.path.exists(TEAMS_FILE):
        with open(TEAMS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_teams(teams):
    with open(TEAMS_FILE, 'w') as f:
        json.dump(teams, f, indent=4)

def load_requests():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_requests(requests_data):
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests_data, f, indent=4)

# --- Home Page ---
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins']*3 + team['draws']

    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)

    # Top scorer / assister
    top_scorer = top_assister = None
    max_goals = max_assists = -1
    for team in teams:
        for player in team.get('players', []):
            if player['goals'] > max_goals:
                max_goals = player['goals']
                top_scorer = player['name']
            if player['assists'] > max_assists:
                max_assists = player['assists']
                top_assister = player['name']

    return render_template('index.html', teams=teams, top_scorer=top_scorer, top_assister=top_assister)

# --- Team Page ---
@app.route('/team/<team_name>', methods=['GET'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404
    return render_template('team.html', team=team)

# --- Submit Lineup Request ---
@app.route('/team/<team_name>/request_lineup', methods=['POST'])
def request_lineup(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    requester = request.form.get('requester')
    lineup_date = request.form.get('lineup_date')
    lineup_names = request.form.getlist('lineup')

    if not requester or not lineup_date or not lineup_names:
        flash("Please fill all fields.")
        return redirect(url_for('team_page', team_name=team_name))

    requests_data = load_requests()
    new_request = {
        "id": len(requests_data) + 1,
        "type": "lineup",
        "team": team_name,
        "lineup": lineup_names,
        "date": lineup_date,
        "user": requester
    }
    requests_data.append(new_request)
    save_requests(requests_data)
    flash("Lineup request sent!")
    return redirect(url_for('team_page', team_name=team_name))

# --- Submit Player Stats Request ---
@app.route('/team/<team_name>/player/<player_name>/request_stats', methods=['POST'])
def request_stats(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404
    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found!", 404

    requester = request.form.get('requester')
    goals = request.form.get('goals')
    assists = request.form.get('assists')

    if not requester or goals is None or assists is None:
        flash("Please fill all fields.")
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    requests_data = load_requests()
    new_request = {
        "id": len(requests_data) + 1,
        "type": "player_stats",
        "team": team_name,
        "player": player_name,
        "goals": int(goals),
        "assists": int(assists),
        "user": requester
    }
    requests_data.append(new_request)
    save_requests(requests_data)
    flash("Stat update request sent!")
    return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

# --- Player Page ---
@app.route('/team/<team_name>/player/<player_name>')
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404
    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found!", 404
    return render_template('player.html', team=team, player=player)

# --- Delete Confirmed Lineup ---
@app.route('/team/<team_name>/lineup/delete/<lineup_date>', methods=['POST'])
def delete_lineup(team_name, lineup_date):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if team and 'confirmed_lineups' in team:
        team['confirmed_lineups'] = [cl for cl in team['confirmed_lineups'] if cl['date'] != lineup_date]
        save_teams(teams)
    return redirect(url_for('team_page', team_name=team_name))

if __name__ == '__main__':
    app.run(debug=True)
