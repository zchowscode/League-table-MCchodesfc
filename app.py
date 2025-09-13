from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')


# -------------------- Data Helpers -------------------- #
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


# -------------------- League Table -------------------- #
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins'] * 3 + team['draws']

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


# -------------------- Team Page -------------------- #
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if 'temp_lineup' not in team:
        team['temp_lineup'] = []

    if request.method == 'POST' and request.form.get('request_type') == 'lineup':
        user_name = request.form.get('user_name')
        lineup_date = request.form.get('lineup_date')
        temp_lineup_names = request.form.getlist('lineup')

        team['temp_lineup'] = temp_lineup_names

        requests_data = load_requests()
        new_request = {
            "id": len(requests_data) + 1,
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


# -------------------- Player Page -------------------- #
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == 'POST' and request.form.get('request_type') == 'player':
        requester = request.form.get('requester')
        goals = int(request.form.get('goals', player['goals']))
        assists = int(request.form.get('assists', player['assists']))

        requests_data = load_requests()
        new_request = {
            "id": len(requests_data) + 1,
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

    return render_template('player.html', team=team, player=player)


# -------------------- Admin Login -------------------- #
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_requests'))
        else:
            flash("Wrong password!")
    return render_template('admin_login.html')


# -------------------- Admin Requests -------------------- #
@app.route('/admin/requests')
def admin_requests():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    requests_data = load_requests()
    return render_template('admin_requests.html', requests=requests_data)


@app.route('/admin/requests/approve/<int:request_id>', methods=['POST'])
def approve_request(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    admin_password = request.form.get('admin_password')
    if admin_password != ADMIN_PASSWORD:
        flash("Wrong admin password!")
        return redirect(url_for('admin_requests'))

    requests_data = load_requests()
    req = next((r for r in requests_data if r['id'] == request_id), None)
    if req:
        teams = load_teams()
        team = next((t for t in teams if t['name'] == req['team']), None)
        if req['type'] == 'lineup' and team:
            if 'confirmed_lineups' not in team:
                team['confirmed_lineups'] = []
            lineup_objs = [next(p for p in team['players'] if p['name'] == n) for n in req['lineup'] if n]
            team['confirmed_lineups'].append({'date': req['date'], 'lineup': lineup_objs})
        elif req['type'] == 'player' and team:
            player = next((p for p in team['players'] if p['name'] == req['player']), None)
            if player:
                player['goals'] = req['goals']
                player['assists'] = req['assists']

        requests_data = [r for r in requests_data if r['id'] != request_id]
        save_requests(requests_data)
        save_teams(teams)

    flash("Request approved!")
    return redirect(url_for('admin_requests'))


@app.route('/admin/requests/deny/<int:request_id>', methods=['POST'])
def deny_request(request_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    admin_password = request.form.get('admin_password')
    if admin_password != ADMIN_PASSWORD:
        flash("Wrong admin password!")
        return redirect(url_for('admin_requests'))

    requests_data = load_requests()
    requests_data = [r for r in requests_data if r['id'] != request_id]
    save_requests(requests_data)

    flash("Request denied!")
    return redirect(url_for('admin_requests'))


# -------------------- Delete Lineup -------------------- #
@app.route('/team/<team_name>/lineup/delete/<lineup_date>', methods=['POST'])
def delete_lineup(team_name, lineup_date):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if team and 'confirmed_lineups' in team:
        team['confirmed_lineups'] = [cl for cl in team['confirmed_lineups'] if cl['date'] != lineup_date]
        save_teams(teams)
    flash("Confirmed lineup deleted!")
    return redirect(url_for('team_page', team_name=team_name))


if __name__ == '__main__':
    app.run(debug=True)
