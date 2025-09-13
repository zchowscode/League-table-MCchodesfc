from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecret')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

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

def save_requests(reqs):
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(reqs, f, indent=4)

# Home page
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins']*3 + team['draws']
    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)
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

# Team page
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST' and 'request' in request.form:
        requester = request.form.get('requester')
        lineup_date = request.form.get('lineup_date')
        lineup_names = request.form.getlist('lineup')

        reqs = load_requests()
        reqs.append({
            'id': str(uuid.uuid4()),
            'type': 'lineup',
            'team': team_name,
            'lineup': lineup_names,
            'date': lineup_date,
            'user': requester
        })
        save_requests(reqs)
        flash('Lineup update request sent!')
        return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# Player page
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == 'POST' and 'request' in request.form:
        requester = request.form.get('requester')
        goals = int(request.form.get('goals', player['goals']))
        assists = int(request.form.get('assists', player['assists']))

        reqs = load_requests()
        reqs.append({
            'id': str(uuid.uuid4()),
            'type': 'player_stats',
            'team': team_name,
            'player': player_name,
            'goals': goals,
            'assists': assists,
            'user': requester
        })
        save_requests(reqs)
        flash('Player stat update request sent!')
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    return render_template('player.html', team=team, player=player)

# Admin view pending requests
@app.route('/admin/requests')
def admin_requests():
    reqs = load_requests()
    return render_template('admin_requests.html', requests=reqs)

# Approve request
@app.route('/admin/approve/<request_id>', methods=['POST'])
def approve_request(request_id):
    password = request.form.get('admin_password')
    if password != ADMIN_PASSWORD:
        flash('Incorrect admin password!')
        return redirect(url_for('admin_requests'))

    reqs = load_requests()
    req_obj = next((r for r in reqs if r['id'] == request_id), None)
    if not req_obj:
        flash('Request not found!')
        return redirect(url_for('admin_requests'))

    teams = load_teams()
    team = next((t for t in teams if t['name'] == req_obj['team']), None)
    if not team:
        flash('Team not found!')
        return redirect(url_for('admin_requests'))

    if req_obj['type'] == 'lineup':
        lineup_objects = [next((p for p in team['players'] if p['name']==n), None) for n in req_obj['lineup']]
        if 'confirmed_lineups' not in team:
            team['confirmed_lineups'] = []
        team['confirmed_lineups'].append({'date': req_obj['date'], 'lineup': lineup_objects})
    elif req_obj['type'] == 'player_stats':
        player = next((p for p in team['players'] if p['name']==req_obj['player']), None)
        if player:
            player['goals'] = req_obj['goals']
            player['assists'] = req_obj['assists']

    save_teams(teams)
    reqs = [r for r in reqs if r['id'] != request_id]
    save_requests(reqs)
    flash('Request approved!')
    return redirect(url_for('admin_requests'))

# Deny request
@app.route('/admin/deny/<request_id>', methods=['POST'])
def deny_request(request_id):
    password = request.form.get('admin_password')
    if password != ADMIN_PASSWORD:
        flash('Incorrect admin password!')
        return redirect(url_for('admin_requests'))

    reqs = load_requests()
    reqs = [r for r in reqs if r['id'] != request_id]
    save_requests(reqs)
    flash('Request denied!')
    return redirect(url_for('admin_requests'))

if __name__ == '__main__':
    app.run(debug=True)
