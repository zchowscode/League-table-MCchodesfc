# Team Page
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    if request.method == 'POST' and 'request' in request.form:
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
        flash("Lineup update request sent successfully!")  # <-- added flash

    if 'temp_lineup' not in team:
        team['temp_lineup'] = []

    return render_template('team.html', team=team)


# Player Page
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    teams = load_teams()
    team = next((t for t in teams if t['name'] == team_name), None)
    if not team:
        return f"Team {team_name} not found!", 404

    player = next((p for p in team.get('players', []) if p['name'] == player_name), None)
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == 'POST' and 'request' in request.form:
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
        flash("Player stat update request sent successfully!")  # <-- added flash

    return render_template('player.html', team=team, player=player)
