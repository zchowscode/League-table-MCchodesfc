from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')

DATA_FILE = 'teams.json'
REQUEST_FILE = 'pending_requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')  # replace with secure password

# --------------------------
# Helper functions
# --------------------------
def load_teams():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_teams(teams):
    with open(DATA_FILE, 'w') as f:
        json.dump(teams, f, indent=4)

def load_requests():
    if os.path.exists(REQUEST_FILE):
        with open(REQUEST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_requests(requests):
    with open(REQUEST_FILE, 'w') as f:
        json.dump(requests, f, indent=4)

# --------------------------
# League table
# --------------------------
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins']*3 + team['draws']
    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)

    # Top scorer / assister
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

# --------------------------
# Team page (lineup & matches)
# --------------------------
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST':
        requester = request.form.get('requester')
        temp_lineup = request.form.getlist('lineup')
        lineup_date = request.form.get('lineup_date')

        if not requester:
            flash('Please enter your name to submit a request.', 'error')
            return redirect(url_for('team_page', team_name=team_name))

        # Save request instead of updating immediately
        pending_requests = load_requests()
        pending_requests.append({
            'type': 'lineup',
            'team': team_name,
            'lineup': temp_lineup,
            'date': lineup_date,
            'requester': requester
        })
        save_requests(pending_requests)
        flash('Your lineup request has been sent!', 'success')
        return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# --------------------------
# Player page (stats update requests)
# --------------------------
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
        if not requester:
            flash('Please enter your name to submit a request.', 'error')
            return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

        goals = request.form.get('goals')
        assists = request.form.get('assists')

        # Save request
        pending_requests = load_requests()
        pending_requests.append({
            'type': 'player_stats',
            'team': team_name,
            'player': player_name,
            'goals': goals,
            'assists': assists,
            'requester': requester
        })
        save_requests(pending_requests)
        flash('Your player stats request has been sent!', 'success')
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    return render_template('player.html', team=team, player=player)

# --------------------------
# Admin login
# --------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_requests'))
        else:
            flash('Incorrect password', 'error')
    return render_template('admin_login.html')

# --------------------------
# Admin view pending requests
# --------------------------
@app.route('/admin/requests', methods=['GET', 'POST'])
def admin_requests():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    requests_list = load_requests()

    # Approve or deny
    if request.method == 'POST':
        action = request.form.get('action')
        index = int(request.form.get('index'))

        teams = load_teams()

        req = requests_list.pop(index)
        if action == 'approve':
            if req['type'] == 'lineup':
                team = next((t for t in teams if t['name'] == req['team']), None)
                if team:
                    lineup_objects = [next(p for p in team['players'] if p['name'] == n) for n in req['lineup'] if n]
                    if 'confirmed_lineups' not in team:
                        team['confirmed_lineups'] = []
                    team['confirmed_lineups'].append({
                        'date': req['date'],
                        'lineup': lineup_objects
                    })
            elif req['type'] == 'player_stats':
                team = next((t for t in teams if t['name'] == req['team']), None)
                if team:
                    player = next((p for p in team.get('players', []) if p['name'] == req['player']), None)
                    if player:
                        player['goals'] = int(req['goals'])
                        player['assists'] = int(req['assists'])

            save_teams(teams)

        save_requests(requests_list)
        return redirect(url_for('admin_requests'))

    return render_template('admin_requests.html', requests=requests_list)

# --------------------------
# Admin logout
# --------------------------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('league_table'))

# --------------------------
if __name__ == '__main__':
    app.run(debug=True)
