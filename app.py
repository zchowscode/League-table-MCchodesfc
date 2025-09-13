from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

DATA_FILE = 'teams.json'

# Load teams from JSON
def load_teams():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return []

# Save teams to JSON
def save_teams(teams):
    with open(DATA_FILE, 'w') as f:
        json.dump(teams, f, indent=4)

# Home page - League Table
@app.route('/')
def league_table():
    teams = load_teams()
    for team in teams:
        team['goal_difference'] = team['goals_for'] - team['goals_against']
        team['points'] = team['wins']*3 + team['draws']
    teams = sorted(teams, key=lambda x: (x['points'], x['goal_difference']), reverse=True)

    # Compute top scorer / top assister
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

        if 'confirm' in request.form and lineup_date:
            # Confirm lineup with actual player objects
            if 'confirmed_lineups' not in team:
                team['confirmed_lineups'] = []
            lineup_objects = [next(p for p in team['players'] if p['name'] == n) for n in temp_lineup_names if n]
            team['confirmed_lineups'].append({
                'date': lineup_date,
                'lineup': lineup_objects
            })
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
        player['goals'] = int(request.form.get('goals', player['goals']))
        player['assists'] = int(request.form.get('assists', player['assists']))
        save_teams(teams)
        return redirect(url_for('player_page', team_name=team_name, player_name=player_name))

    return render_template('player.html', team=team, player=player)

if __name__ == '__main__':
    app.run(debug=True)
