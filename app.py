from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'

ADMIN_PASSWORD = "admin123"  # change this to whatever password you want

# Load teams from JSON
def load_teams():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

# Save teams to JSON
def save_teams(teams):
    with open(DATA_FILE, 'w') as f:
        json.dump(teams, f, indent=4)

# Load requests from JSON
def load_requests():
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'r') as f:
            return json.load(f)
    return []

# Save requests to JSON
def save_requests(requests):
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(requests, f, indent=4)

# Home page - League Table
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins']*3 + team['draws']
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

# Team page - manage lineup & matches
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST':
        temp_lineup_names = request.form.getlist('lineup')
        lineup_date = request.form.get('lineup_date')

        if 'request' in request.form and lineup_date:
            # Add a request instead of confirming directly
            requests = load_requests()
            requests.append({
                'team_name': team_name,
                'type': 'lineup',
                'date': lineup_date,
                'lineup': temp_lineup_names
            })
            save_requests(requests)
            return redirect(url_for('team_page', team_name=team_name))

        else:
            # Update temporary lineup
            team['lineup'] = temp_lineup_names
            save_teams(teams)
            return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# Delete a confirmed lineup by date
@app.route('/team/<team_name>/lineup/delete/<lineup_date>', methods=['POST'])
def delete_lineup(team_name, lineup_date):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if team and 'confirmed_lineups' in team:
        team['confirmed_lineups'] = [
            cl for cl in team['confirmed_lineups'] if cl['date'] != lineup_date
        ]
        save_teams(teams)
    return redirect(url_for('team_page', team_name=team_name))

# Player stats page
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
        # Player stats update requests
        requests = load_requests()
        requests.append({
            'team_name': team_name,
            'type': 'player_stats',
            'player_name': player_name,
            'goals': int(request.form.get('goals', player['goals'])),
            'assists': int(request.form.get('assists', player['assists']))
        })
        save_requests(requests)
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    return render_template('player.html', team=team, player=player)

# Admin view to confirm/deny requests
@app.route('/admin/requests', methods=['GET', 'POST'])
def admin_requests():
    requests_list = load_requests()
    if request.method == 'POST':
        password = request.form.get('password')
        action = request.form.get('action')
        index = int(request.form.get('index'))

        if password != ADMIN_PASSWORD:
            return "Incorrect password!", 403

        teams = load_teams()

        if action == 'confirm':
            req = requests_list.pop(index)
            team = next((t for t in teams if t['name'] == req['team_name']), None)
            if not team:
                return f"Team {req['team_name']} not found!", 404

            if req['type'] == 'lineup':
                lineup_objects = [next(p for p in team['players'] if p['name'] == n) for n in req['lineup'] if n]
                if 'confirmed_lineups' not in team:
                    team['confirmed_lineups'] = []
                team['confirmed_lineups'].append({
                    'date': req['date'],
                    'lineup': lineup_objects
                })
            elif req['type'] == 'player_stats':
                player = next((p for p in team['players'] if p['name'] == req['player_name']), None)
                if player:
                    player['goals'] = req['goals']
                    player['assists'] = req['assists']

        elif action == 'deny':
            requests_list.pop(index)

        save_requests(requests_list)
        save_teams(teams)
        return redirect(url_for('admin_requests'))

    return render_template('admin_requests.html', requests=requests_list)

if __name__ == '__main__':
    app.run(debug=True)
