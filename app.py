from flask import Flask, render_template, request, redirect, url_for
import json
import os
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')  # change to secure in production

# --- Load and Save Functions ---
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

def save_requests(requests):
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests, f, indent=4)

# --- Home Page ---
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins']*3 + team['draws']
    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)

    # Top Scorer / Assister
    top_scorer = None
    top_assister = None
    max_goals = -1
    max_assists = -1
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
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if 'temp_lineup' not in team:
        team['temp_lineup'] = team.get('lineup', [])

    if request.method == 'POST':
        temp_lineup_names = request.form.getlist('lineup')
        team['temp_lineup'] = temp_lineup_names
        save_teams(teams)
        return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# --- Player Page ---
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    return render_template('player.html', team=team, player=player)

# --- Submit Requests ---
@app.route('/team/<team_name>/request_lineup', methods=['POST'])
def request_lineup(team_name):
    user = request.form.get('user_name')
    lineup = request.form.getlist('lineup')
    date = request.form.get('lineup_date')

    if not user or not lineup or not date:
        return "Please enter your name, lineup, and date!", 400

    requests_list = load_requests()
    requests_list.append({
        'id': str(uuid4()),
        'user': user,
        'type': 'lineup',
        'team': team_name,
        'lineup': lineup,
        'date': date
    })
    save_requests(requests_list)
    return redirect(url_for('team_page', team_name=team_name))

@app.route('/team/<team_name>/player/<player_name>/request_stats', methods=['POST'])
def request_player_stats(team_name, player_name):
    user = request.form.get('user_name')
    goals = request.form.get('goals')
    assists = request.form.get('assists')

    if not user or goals is None or assists is None:
        return "Please enter your name and stats!", 400

    requests_list = load_requests()
    requests_list.append({
        'id': str(uuid4()),
        'user': user,
        'type': 'player_stats',
        'team': team_name,
        'player': player_name,
        'goals': int(goals),
        'assists': int(assists)
    })
    save_requests(requests_list)
    return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

# --- Admin Pages ---
@app.route('/admin/requests')
def admin_requests():
    requests_list = load_requests()
    return render_template('admin_requests.html', requests=requests_list)

@app.route('/admin/approve/<request_id>', methods=['POST'])
def approve_request(request_id):
    password = request.form.get('admin_password')
    if password != ADMIN_PASSWORD:
        return "Wrong password!", 403

    requests_list = load_requests()
    req = next((r for r in requests_list if r['id'] == request_id), None)
    if not req:
        return "Request not found!", 404

    teams = load_teams()
    team = next((t for t in teams if t['name'] == req['team']), None)
    if not team:
        return "Team not found!", 404

    if req['type'] == 'lineup':
        if 'confirmed_lineups' not in team:
            team['confirmed_lineups'] = []
        lineup_objects = [next(p for p in team['players'] if p['name'] == n) for n in req['lineup']]
        team['confirmed_lineups'].append({'date': req['date'], 'lineup': lineup_objects})
    elif req['type'] == 'player_stats':
        player = next((p for p in team.get('players', []) if p['name'] == req['player']), None)
        if player:
            player['goals'] = req['goals']
            player['assists'] = req['assists']

    save_teams(teams)
    requests_list = [r for r in requests_list if r['id'] != request_id]
    save_requests(requests_list)
    return redirect(url_for('admin_requests'))

@app.route('/admin/deny/<request_id>', methods=['POST'])
def deny_request(request_id):
    password = request.form.get('admin_password')
    if password != ADMIN_PASSWORD:
        return "Wrong password!", 403

    requests_list = load_requests()
    requests_list = [r for r in requests_list if r['id'] != request_id]
    save_requests(requests_list)
    return redirect(url_for('admin_requests'))

if __name__ == '__main__':
    app.run(debug=True)
