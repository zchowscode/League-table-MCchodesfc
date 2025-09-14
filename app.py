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
        team.setdefault('played', 0)
        team.setdefault('wins', 0)
        team.setdefault('draws', 0)
        team.setdefault('losses', 0)
        team['points'] = team['wins']*3 + team['draws']
    return render_template('index.html', teams=teams)

# -------------------- Team Page -------------------- #
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    team_name = team_name.replace('_', ' ')
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    team.setdefault('players', [])

    if request.method == 'POST':
        req_type = request.form.get('request_type')
        requests_data = load_requests()
        new_request = {
            "id": len(requests_data)+1,
            "user": request.form.get('user_name', 'Anonymous'),
            "team": team_name,
            "type": req_type,
            "stat": None,
            "increment": None
        }

        if req_type == 'update_stat':
            stat = request.form.get('stat')  # 'played', 'wins', 'draws', 'losses'
            try: increment = int(request.form.get('increment', 0))
            except: increment = 0
            new_request.update({"stat": stat, "increment": increment})

        requests_data.append(new_request)
        save_requests(requests_data)
        flash("Request sent!")
        return redirect(url_for('team_page', team_name=team_name.replace(' ', '_')))

    return render_template('team.html', team=team)

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

    if request.method == 'POST':
        requester = request.form.get('requester','Anonymous')
        try: goals = int(request.form.get('goals', player.get('goals',0)))
        except: goals = player.get('goals',0)
        try: assists = int(request.form.get('assists', player.get('assists',0)))
        except: assists = player.get('assists',0)

        requests_data = load_requests()
        new_request = {
            "id": len(requests_data)+1,
            "user": requester,
            "team": team_name,
            "type": "player",
            "player": player_name,
            "goals": goals,
            "assists": assists
        }
        requests_data.append(new_request)
        save_requests(requests_data)
        flash("Player stats request sent!")
        return redirect(url_for('player_page', team_name=team_name.replace(' ', '_'), player_name=player_name.replace(' ', '_')))

    return render_template('player.html', team=team, player=player)

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
    if team and req['type']=='update_stat':
        stat = req['stat']
        increment = req['increment']
        if stat in ['played', 'wins', 'draws', 'losses']:
            team[stat] = team.get(stat,0) + increment
            team['points'] = team.get('wins',0)*3 + team.get('draws',0)

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
