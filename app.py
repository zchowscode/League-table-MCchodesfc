from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'supersecretkey')  # fallback secret key

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'

ADMIN_PASSWORD = 'admin123'  # Change this to your desired password

# Load JSON helper
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        return []

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# ----------------- League Table -----------------
@app.route('/')
def league_table():
    teams = load_json(DATA_FILE)
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

# ----------------- Team Page -----------------
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_json(DATA_FILE)
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST':
        temp_lineup = request.form.getlist('lineup')
        lineup_date = request.form.get('lineup_date')
        request_type = request.form.get('request_type', 'lineup')  # 'lineup' or 'player_stats'
        requester = request.form.get('requester', 'Anonymous')

        # Save request instead of applying directly
        requests = load_json(REQUESTS_FILE)
        requests.append({
            'team': team_name,
            'type': request_type,
            'lineup_date': lineup_date,
            'lineup': temp_lineup,
            'requester': requester,
            'status': 'pending'
        })
        save_json(REQUESTS_FILE, requests)

        flash('Your request has been submitted for admin approval!')
        return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# ----------------- Player Stats -----------------
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_json(DATA_FILE)
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == 'POST':
        # Save as a request for admin approval
        requests = load_json(REQUESTS_FILE)
        goals = int(request.form.get('goals', player['goals']))
        assists = int(request.form.get('assists', player['assists']))
        requests.append({
            'team': team_name,
            'type': 'player_stats',
            'player': player_name,
            'goals': goals,
            'assists': assists,
            'requester': request.form.get('requester', 'Anonymous'),
            'status': 'pending'
        })
        save_json(REQUESTS_FILE, requests)

        flash('Your player stats update request has been sent for admin approval!')
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    return render_template('player.html', team=team, player=player)

# ----------------- Admin Login -----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_requests'))
        else:
            flash('Incorrect password.')
    return render_template('admin_login.html')

# ----------------- Admin Requests -----------------
@app.route('/admin/requests', methods=['GET', 'POST'])
def admin_requests():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    requests_list = load_json(REQUESTS_FILE)
    if request.method == 'POST':
        action = request.form.get('action')
        index = int(request.form.get('index'))
        requests_list = load_json(REQUESTS_FILE)
        req = requests_list[index]
        teams = load_json(DATA_FILE)

        if action == 'approve':
            team = next(t for t in teams if t['name'] == req['team'])
            if req['type'] == 'lineup':
                lineup_objects = [next(p for p in team['players'] if p['name'] == n) for n in req['lineup'] if n]
                if 'confirmed_lineups' not in team:
                    team['confirmed_lineups'] = []
                team['confirmed_lineups'].append({
                    'date': req['lineup_date'],
                    'lineup': lineup_objects
                })
            elif req['type'] == 'player_stats':
                player = next(p for p in team['players'] if p['name'] == req['player'])
                player['goals'] = req['goals']
                player['assists'] = req['assists']
            req['status'] = 'approved'
            save_json(DATA_FILE, teams)
        elif action == 'deny':
            req['status'] = 'denied'

        save_json(REQUESTS_FILE, requests_list)
        return redirect(url_for('admin_requests'))

    return render_template('admin_requests.html', requests=requests_list)

# ----------------- Logout Admin -----------------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out.')
    return redirect(url_for('league_table'))

if __name__ == '__main__':
    app.run(debug=True)
