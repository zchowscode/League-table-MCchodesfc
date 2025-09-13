from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')

TEAMS_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')

# -------------------- Helper functions --------------------
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

def save_requests(requests):
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests, f, indent=4)

# -------------------- League Table --------------------
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team.get('goals_for', 0) - team.get('goals_against', 0)
        team['points'] = team.get('wins', 0)*3 + team.get('draws', 0)

    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)

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

# -------------------- Team Page --------------------
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST':
        # Lineup request
        requester = request.form.get('requester')
        lineup_date = request.form.get('lineup_date')
        lineup_names = request.form.getlist('lineup')
        if requester and lineup_date:
            requests_list = load_requests()
            requests_list.append({
                'id': str(uuid.uuid4()),
                'type': 'lineup',
                'team': team_name,
                'lineup': lineup_names,
                'date': lineup_date,
                'user': requester
            })
            save_requests(requests_list)
            flash("Lineup update request sent!")
            return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# -------------------- Player Page --------------------
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == 'POST':
        requester = request.form.get('requester')
        if requester:
            goals = int(request.form.get('goals', player['goals']))
            assists = int(request.form.get('assists', player['assists']))
            requests_list = load_requests()
            requests_list.append({
                'id': str(uuid.uuid4()),
                'type': 'player',
                'team': team_name,
                'player': player_name,
                'goals': goals,
                'assists': assists,
                'user': requester
            })
            save_requests(requests_list)
            flash("Player stats update request sent!")
            return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    return render_template('player.html', team=team, player=player)

# -------------------- Admin Login --------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_requests'))
        else:
            flash("Incorrect password!")
    return render_template('admin_login.html')

# -------------------- Admin Pending Requests --------------------
@app.route('/admin/requests')
def admin_requests():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    requests_list = load_requests()
    return render_template('admin_requests.html', requests=requests_list)

@app.route('/admin/approve/<request_id>', methods=['POST'])
def approve_request(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    requests_list = load_requests()
    req = next((r for r in requests_list if r['id'] == request_id), None)
    if req:
        teams = load_teams()
        team = next((t for t in teams if t['name'] == req['team']), None)
        if team:
            if req['type'] == 'lineup':
                if 'confirmed_lineups' not in team:
                    team['confirmed_lineups'] = []
                lineup_objects = [next((p for p in team['players'] if p['name']==n), {'name':n, 'goals':0, 'assists':0}) for n in req['lineup']]
                team['confirmed_lineups'].append({'date': req['date'], 'lineup': lineup_objects})
            elif req['type'] == 'player':
                player = next((p for p in team.get('players', []) if p['name']==req['player']), None)
                if player:
                    player['goals'] = req['goals']
                    player['assists'] = req['assists']
            save_teams(teams)
        # Remove request
        requests_list = [r for r in requests_list if r['id'] != request_id]
        save_requests(requests_list)
    return redirect(url_for('admin_requests'))

@app.route('/admin/deny/<request_id>', methods=['POST'])
def deny_request(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    requests_list = load_requests()
    requests_list = [r for r in requests_list if r['id'] != request_id]
    save_requests(requests_list)
    return redirect(url_for('admin_requests'))

# -------------------- Delete Lineup --------------------
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
