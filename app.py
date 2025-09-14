from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')

DATA_FILE = 'teams.json'
REQUESTS_FILE = 'requests.json'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'goathavertz')

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

# -------------------- Routes -------------------- #
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team.setdefault('goals_for', 0)
        team.setdefault('goals_against', 0)
        team.setdefault('wins', 0)
        team.setdefault('draws', 0)
        team.setdefault('players', [])
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins'] * 3 + team['draws']

    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)

    top_scorer = None
    top_assister = None
    max_goals = -1
    max_assists = -1

    for team in teams:
        for player in team.get('players', []):
            player.setdefault('goals', 0)
            player.setdefault('assists', 0)
            if player['goals'] > max_goals:
                max_goals = player['goals']
                top_scorer = player.get('name')
            if player['assists'] > max_assists:
                max_assists = player['assists']
                top_assister = player.get('name')

    return render_template('index.html', teams=teams, top_scorer=top_scorer, top_assister=top_assister)

# -------------------- Team Page -------------------- #
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t.get('name') == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    team.setdefault('temp_lineup', [])
    team.setdefault('confirmed_lineups', [])
    team.setdefault('players', [])

    if request.method == 'POST':
        request_type = request.form.get('request_type')

        # Lineup update request
        if request_type == 'lineup':
            user_name = request.form.get('user_name') or "Anonymous"
            lineup_date = request.form.get('lineup_date') or ""
            temp_lineup_names = [n.strip() for n in request.form.getlist('lineup') if n.strip()]
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

        # Delete lineup request
        elif request_type == 'delete_lineup':
            user_name = request.form.get('user_name') or "Anonymous"
            lineup_date = request.form.get('lineup_date')
            requests_data = load_requests()
            new_request = {
                "id": len(requests_data) + 1,
                "user": user_name,
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
            flash("Lineup deletion request sent!")
            return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

# -------------------- Player Page -------------------- #
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t.get('name') == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p.get('name') == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    player.setdefault('goals', 0)
    player.setdefault('assists', 0)

    if request.method == 'POST' and request.form.get('request_type') == 'player':
        requester = request.form.get('requester') or "Anonymous"
        try:
            goals = int(request.form.get('goals', player.get('goals', 0)))
        except (ValueError, TypeError):
            goals = player.get('goals', 0)
        try:
            assists = int(request.form.get('assists', player.get('assists', 0)))
        except (ValueError, TypeError):
            assists = player.get('assists', 0)

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

# -------------------- Admin -------------------- #
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
    req = next((r for r in requests_data if r.get('id') == request_id), None)
    if req:
        teams = load_teams()
        team = next((t for t in teams if t.get('name') == req.get('team')), None)

        if team:
            if req.get('type') == 'lineup':
                team.setdefault('confirmed_lineups', [])
                lineup_objs = [p for p in team.get('players', []) if p.get('name') in req.get('lineup', [])]
                team['confirmed_lineups'].append({'date': req.get('date'), 'lineup': lineup_objs})

            elif req.get('type') == 'player':
                player = next((p for p in team.get('players', []) if p.get('name') == req.get('player')), None)
                if player:
                    player['goals'] = req.get('goals', player['goals'])
                    player['assists'] = req.get('assists', player['assists'])

            elif req.get('type') == 'delete_lineup':
                team['confirmed_lineups'] = [cl for cl in team.get('confirmed_lineups', []) if cl.get('date') != req.get('date')]

        requests_data = [r for r in requests_data if r.get('id') != request_id]
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
    requests_data = [r for r in requests_data if r.get('id') != request_id]
    save_requests(requests_data)
    flash("Request denied!")
    return redirect(url_for('admin_requests'))

if __name__ == '__main__':
    app.run(debug=True)
