from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'

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

def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            flash("Please login as admin first.")
            return redirect(url_for('admin_login'))
        return func(*args, **kwargs)
    return wrapper

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

    # cumulative stats
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

# -------------------- Team Page -------------------- #
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    team_name = team_name.replace('_', ' ')  # convert underscores to spaces
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    team.setdefault('players', [])
    team.setdefault('temp_lineup', [])
    team.setdefault('confirmed_lineups', [])

    if request.method == 'POST':
        req_type = request.form.get('request_type')
        requests_data = load_requests()
        new_request = {
            "id": len(requests_data)+1,
            "user": request.form.get('user_name', 'Anonymous'),
            "team": team_name,
            "type": req_type,
            "lineup": None,
            "player": None,
            "goals": None,
            "assists": None,
            "date": None
        }

        if req_type == 'lineup':
            lineup_date = request.form.get('lineup_date')
            temp_lineup = [n.strip() for n in request.form.getlist('lineup') if n.strip()]
            team['temp_lineup'] = temp_lineup
            new_request.update({"lineup": temp_lineup, "date": lineup_date})

        elif req_type == 'player':
            player_name = request.form.get('player_name')
            try: goals = int(request.form.get('goals', 0))
            except: goals = 0
            try: assists = int(request.form.get('assists', 0))
            except: assists = 0
            new_request.update({"player": player_name, "goals": goals, "assists": assists})

        elif req_type == 'delete_lineup':
            lineup_date = request.form.get('lineup_date')
            new_request.update({"type": "delete_lineup", "date": lineup_date})

        requests_data.append(new_request)
        save_requests(requests_data)
        flash("Request sent!")
        return redirect(url_for('team_page', team_name=team_name.replace(' ', '_')))

    return render_template('team.html', team=team)

# -------------------- Delete Lineup Request -------------------- #
@app.route('/team/<team_name>/delete_lineup', methods=['POST'])
def team_delete_lineup_request(team_name):
    team_name = team_name.replace('_', ' ')  # fix spaces
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    lineup_date = request.form.get('lineup_date')
    requests_data = load_requests()
    new_request = {
        "id": len(requests_data)+1,
        "user": request.form.get('user_name', 'Anonymous'),
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
    return redirect(url_for('team_page', team_name=team_name.replace(' ', '_')))

# -------------------- Player Page -------------------- #
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    team_name = team_name.replace('_', ' ')
    player_name = player_name.replace('_', ' ')
    teams = load_teams()
    team = next((t for t in teams if t['name']==team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name']==player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    player.setdefault('goals',0)
    player.setdefault('assists',0)

    if request.method == 'POST':
        requester = request.form.get('requester','Anonymous')
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
        return redirect(url_for('player_page', team_name=team_name.replace(' ', '_'), player_name=player_name.replace(' ', '_')))

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

# -------------------- Admin Login -------------------- #
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            flash("Logged in as admin!")
            return redirect(url_for('admin_requests'))
        else:
            flash("Incorrect password!")
    return render_template('admin_login.html')

# -------------------- Admin Requests -------------------- #
@app.route('/admin/requests')
@login_required
def admin_requests():
    requests_data = load_requests()
    return render_template('admin_requests.html', requests=requests_data)

@app.route('/admin/requests/approve/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    requests_data = load_requests()
    req = next((r for r in requests_data if r['id']==request_id), None)
    if not req:
        flash("Request not found.")
        return redirect(url_for('admin_requests'))

    teams = load_teams()
    team = next((t for t in teams if t['name']==req['team']), None)
    if team:
        if req['type']=='lineup':
            team.setdefault('confirmed_lineups', []).append({'date': req['date'], 'lineup': req['lineup']})
        elif req['type']=='player':
            player = next((p for p in team.get('players', []) if p['name']==req['player']), None)
            if player:
                player['goals'] = req['goals']
                player['assists'] = req['assists']
        elif req['type']=='delete_lineup':
            team['confirmed_lineups'] = [cl for cl in team.get('confirmed_lineups', []) if cl['date'] != req['date']]

    save_teams(teams)

    requests_data = [r for r in requests_data if r['id'] != request_id]
    save_requests(requests_data)

    flash("Request approved!")
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests/deny/<int:request_id>', methods=['POST'])
@login_required
def deny_request(request_id):
    requests_data = load_requests()
    requests_data = [r for r in requests_data if r['id'] != request_id]
    save_requests(requests_data)
    flash("Request denied!")
    return redirect(url_for('admin_requests'))

if __name__ == '__main__':
    app.run(debug=True)
