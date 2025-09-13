from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app = Flask(__name__)

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
    return render_template('index.html', teams=teams)

# Team page
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST':
        # Update lineup
        lineup = request.form.getlist('lineup')
        team['lineup'] = lineup

        # Update matches
        for i, match in enumerate(team.get('matches', [])):
            match['goals'] = int(request.form.get(f'goals_{i}', match['goals']))
            match['assists'] = int(request.form.get(f'assists_{i}', match['assists']))

        # Recalculate team stats
        team['wins'] = team.get('wins', 0)
        team['draws'] = team.get('draws', 0)
        team['losses'] = team.get('losses', 0)
        team['goals_for'] = sum(m['goals'] for m in team.get('matches', []))
        team['goals_against'] = sum(m.get('opponent_goals', 0) for m in team.get('matches', []))

        save_teams(teams)
        return redirect(url_for('team_page', team_name=team_name))

    return render_template('team.html', team=team)

if __name__ == '__main__':
    app.run(debug=True)
