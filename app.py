from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
TEAM_FILE = 'teams.json'
REQUEST_FILE = 'requests.json'

# -------------------- Helpers -------------------- #
def load_teams():
    try:
        with open(TEAM_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_teams(teams):
    with open(TEAM_FILE, 'w') as f:
        json.dump(teams, f, indent=2)

def load_requests():
    try:
        with open(REQUEST_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_requests(requests):
    with open(REQUEST_FILE, 'w') as f:
        json.dump(requests, f, indent=2)

def login_required(func):
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
    top_scorer = top_assister = top_ga_player = None
    top_scorer_goals = top_assister_assists = top_ga_total = None
    max_goals = max_assists = max_ga = -1

    for team in teams:
        # Calculate points and played
        team['points'] = team.get('wins', 0)*3 + team.get('draws', 0)
        team['played'] = team.get('wins', 0) + team.get('draws', 0) + team.get('losses', 0)
        # Calculate goals_for and goals_against from players
        team['goals_for'] = sum(p.get('goals',0) for p in team.get('players', []))
        team['goals_against'] = sum(p.get('goal_line_clearances',0) for p in team.get('players', []))  # Or adjust as needed

        for p in team.get('players', []):
            if p.get('goals',0) > max_goals:
                max_goals = p['goals']
                top_scorer = p['name']
                top_scorer_goals = p['goals']
            if p.get('assists',0) > max_assists:
                max_assists = p['assists']
                top_assister = p['name']
                top_assister_assists = p['assists']
            ga = p.get('goals',0) + p.get('assists',0)
            if ga > max_ga:
                max_ga = ga
                top_ga_player = p['name']
                top_ga_total = ga

    teams_sorted = sorted(teams, key=lambda x: (-x.get('points',0), -x.get('wins',0)))

    return render_template('index.html', teams=teams_sorted,
                           top_scorer=top_scorer,
                           top_scorer_goals=top_scorer_goals,
                           top_assister=top_assister,
                           top_assister_assists=top_assister_assists,
                           top_ga=top_ga_player,
                           top_ga_total=top_ga_total)

# -------------------- Team Page -------------------- #
@app.route('/team/<team_name>', methods=['GET','POST'])
def team_page(team_name):
    team_name = team_name.replace('_', ' ')
    teams = load_teams()
    team = next((t for t in teams if t['name']==team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method=='POST':
        req_type = request.form.get('request_type')
        user_name = request.form.get('user_name')
        if not user_name:
            flash("You must enter your name to submit a request.")
            return redirect(url_for('team_page', team_name=team_name.replace(' ','_')))

        requests = load_requests()
        new_request = {'id': len(requests)+1, 'user': user_name, 'team_name': team_name, 'type': req_type}

        if req_type=='lineup':
            lineup = [n.strip() for n in request.form.getlist('lineup') if n.strip()]
            new_request['lineup'] = lineup
            new_request['date'] = request.form.get('lineup_date')
        elif req_type=='player':
            player_name = request.form.get('player_name')
            player = next((p for p in team.get('players',[]) if p['name']==player_name), None)
            if player:
                new_request.update({
                    'player_name': player_name,
                    'goals': int(request.form.get('goals',0) or 0),
                    'assists': int(request.form.get('assists',0) or 0),
                    'clean_sheets': int(request.form.get('clean_sheets',0) or 0),
                    'goal_line_clearances': int(request.form.get('goal_line_clearances',0) or 0)
                })
        elif req_type=='update_stat':
            new_request['stat'] = request.form.get('stat')
            new_request['increment'] = int(request.form.get('increment',0) or 0)

        requests.append(new_request)
        save_requests(requests)
        flash("Request sent for admin approval!")
        return redirect(url_for('team_page', team_name=team_name.replace(' ','_')))

    return render_template('team.html', team=team, players=team.get('players', []))

# -------------------- Player Page -------------------- #
@app.route('/team/<team_name>/player/<player_name>', methods=['GET','POST'])
def player_page(team_name, player_name):
    team_name = team_name.replace('_', ' ')
    player_name = player_name.replace('_',' ')
    teams = load_teams()
    team = next((t for t in teams if t['name']==team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404
    player = next((p for p in team.get('players',[]) if p['name']==player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method=='POST':
        user_name = request.form.get('user_name')
        requests = load_requests()
        new_request = {
            'id': len(requests)+1,
            'user': user_name,
            'team_name': team_name,
            'type': 'player',
            'player_name': player_name,
            'goals': int(request.form.get('goals', player.get('goals',0)) or player.get('goals',0)),
            'assists': int(request.form.get('assists', player.get('assists',0)) or player.get('assists',0)),
            'clean_sheets': int(request.form.get('clean_sheets', player.get('clean_sheets',0)) or player.get('clean_sheets',0)),
            'goal_line_clearances': int(request.form.get('goal_line_clearances', player.get('goal_line_clearances',0)) or player.get('goal_line_clearances',0))
        }
        requests.append(new_request)
        save_requests(requests)
        flash("Player stats request sent for admin approval!")
        return redirect(url_for('player_page', team_name=team_name.replace(' ','_'), player_name=player_name.replace(' ','_')))

    return render_template('player.html', team=team, player=player)

# -------------------- Admin -------------------- #
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        if request.form.get('password')==ADMIN_PASSWORD:
            session['admin']=True
            flash("Logged in as admin!")
            return redirect(url_for('admin_requests'))
        else:
            flash("Incorrect password!")
    return render_template('admin_login.html')

@app.route('/admin/requests')
@login_required
def admin_requests():
    requests = load_requests()
    return render_template('admin_requests.html', requests=requests)

@app.route('/admin/requests/approve/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    teams = load_teams()
    requests = load_requests()
    req = next((r for r in requests if r['id']==request_id), None)
    if not req:
        flash("Request not found.")
        return redirect(url_for('admin_requests'))

    team = next((t for t in teams if t['name']==req['team_name']), None)
    if not team:
        flash("Team not found.")
        return redirect(url_for('admin_requests'))

    if req['type']=='lineup':
        team['lineup'] = req.get('lineup', [])
    elif req['type']=='player':
        player = next((p for p in team.get('players',[]) if p['name']==req['player_name']), None)
        if player:
            player.update({
                'goals': req.get('goals', player.get('goals',0)),
                'assists': req.get('assists', player.get('assists',0)),
                'clean_sheets': req.get('clean_sheets', player.get('clean_sheets',0)),
                'goal_line_clearances': req.get('goal_line_clearances', player.get('goal_line_clearances',0))
            })
    elif req['type']=='update_stat':
        stat = req.get('stat')
        increment = req.get('increment',0)
        if stat in ['played','wins','draws','losses']:
            team[stat] = team.get(stat,0) + increment
            team['points'] = team.get('wins',0)*3 + team.get('draws',0)

    requests = [r for r in requests if r['id'] != request_id]
    save_teams(teams)
    save_requests(requests)
    flash("Request approved and applied!")
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests/deny/<int:request_id>', methods=['POST'])
@login_required
def deny_request(request_id):
    requests = load_requests()
    requests = [r for r in requests if r['id'] != request_id]
    save_requests(requests)
    flash("Request denied!")
    return redirect(url_for('admin_requests'))

if __name__=="__main__":
    app.run(debug=True)
