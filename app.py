from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import os
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
DB_FILE = 'league.db'

# -------------------- Database Helpers -------------------- #
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # Teams table
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0
        )
    ''')

    # Players table
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            team_id INTEGER,
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            clean_sheets INTEGER DEFAULT 0,
            goal_line_clearances INTEGER DEFAULT 0,
            FOREIGN KEY(team_id) REFERENCES teams(id)
        )
    ''')

    # Requests table
    c.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            team_id INTEGER,
            type TEXT,
            player_id INTEGER,
            lineup TEXT,
            date TEXT,
            goals INTEGER,
            assists INTEGER,
            clean_sheets INTEGER,
            goal_line_clearances INTEGER,
            stat TEXT,
            increment INTEGER,
            FOREIGN KEY(team_id) REFERENCES teams(id),
            FOREIGN KEY(player_id) REFERENCES players(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

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
    conn = get_db()
    c = conn.cursor()

    # Fetch teams with players
    c.execute('SELECT * FROM teams ORDER BY points DESC, wins DESC')
    teams = c.fetchall()
    team_list = []

    top_scorer = top_assister = top_ga = None
    max_goals = max_assists = max_ga = -1

    for t in teams:
        c.execute('SELECT * FROM players WHERE team_id=?', (t['id'],))
        players = c.fetchall()
        team_dict = dict(t)
        team_dict['players'] = [dict(p) for p in players]
        team_list.append(team_dict)

        # Compute leaders
        for p in players:
            if p['goals'] > max_goals:
                max_goals = p['goals']
                top_scorer = p['name']
            if p['assists'] > max_assists:
                max_assists = p['assists']
                top_assister = p['name']
            ga = p['goals'] + p['assists']
            if ga > max_ga:
                max_ga = ga
                top_ga = p['name']

    conn.close()
    return render_template('index.html',
                           teams=team_list,
                           top_scorer=top_scorer,
                           top_assister=top_assister,
                           top_ga=top_ga)

# -------------------- Team Page -------------------- #
@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_page(team_name):
    team_name = team_name.replace('_', ' ')
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM teams WHERE name=?', (team_name,))
    team = c.fetchone()
    if not team:
        return f"Team {team_name} not found!", 404

    c.execute('SELECT * FROM players WHERE team_id=?', (team['id'],))
    players = [dict(p) for p in c.fetchall()]

    if request.method == 'POST':
        req_type = request.form.get('request_type')
        user_name = request.form.get('user_name')
        if not user_name:
            flash("You must enter your name to submit a request.")
            return redirect(url_for('team_page', team_name=team_name.replace(' ', '_')))

        player_id = None
        lineup_text = None
        date_text = None
        goals = assists = clean_sheets = clearances = None
        stat = None
        increment = None

        if req_type == 'lineup':
            lineup = [n.strip() for n in request.form.getlist('lineup') if n.strip()]
            lineup_text = ','.join(lineup)
            date_text = request.form.get('lineup_date')

        elif req_type == 'player':
            player_name = request.form.get('player_name')
            c.execute('SELECT id FROM players WHERE name=? AND team_id=?', (player_name, team['id']))
            p = c.fetchone()
            if p:
                player_id = p['id']
            goals = int(request.form.get('goals', 0) or 0)
            assists = int(request.form.get('assists', 0) or 0)
            clean_sheets = int(request.form.get('clean_sheets', 0) or 0)
            clearances = int(request.form.get('goal_line_clearances', 0) or 0)

        elif req_type == 'update_stat':
            stat = request.form.get('stat')
            increment = int(request.form.get('increment', 0) or 0)

        c.execute('''
            INSERT INTO requests (user, team_id, type, player_id, lineup, date, goals, assists, clean_sheets, goal_line_clearances, stat, increment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, team['id'], req_type, player_id, lineup_text, date_text, goals, assists, clean_sheets, clearances, stat, increment))
        conn.commit()
        flash("Request sent for admin approval!")
        return redirect(url_for('team_page', team_name=team_name.replace(' ', '_')))

    conn.close()
    return render_template('team.html', team=dict(team), players=players)

# -------------------- Player Page -------------------- #
@app.route('/team/<team_name>/player/<player_name>', methods=['GET', 'POST'])
def player_page(team_name, player_name):
    team_name = team_name.replace('_', ' ')
    player_name = player_name.replace('_', ' ')

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM teams WHERE name=?', (team_name,))
    team = c.fetchone()
    if not team:
        return f"Team {team_name} not found!", 404

    c.execute('SELECT * FROM players WHERE name=? AND team_id=?', (player_name, team['id']))
    player = c.fetchone()
    if not player:
        return f"Player {player_name} not found in {team_name}!", 404

    if request.method == 'POST':
        user_name = request.form.get('user_name')
        goals = int(request.form.get('goals', player['goals']) or player['goals'])
        assists = int(request.form.get('assists', player['assists']) or player['assists'])
        clean_sheets = int(request.form.get('clean_sheets', player['clean_sheets']) or player['clean_sheets'])
        clearances = int(request.form.get('goal_line_clearances', player['goal_line_clearances']) or player['goal_line_clearances'])

        c.execute('''
            INSERT INTO requests (user, team_id, type, player_id, goals, assists, clean_sheets, goal_line_clearances)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, team['id'], 'player', player['id'], goals, assists, clean_sheets, clearances))
        conn.commit()
        flash("Player stats request sent for admin approval!")
        return redirect(url_for('player_page', team_name=team_name.replace(' ', '_'), player_name=player_name.replace(' ', '_')))

    conn.close()
    return render_template('player.html', team=dict(team), player=dict(player))

# -------------------- Admin -------------------- #
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            flash("Logged in as admin!")
            return redirect(url_for('admin_requests'))
        else:
            flash("Incorrect password!")
    return render_template('admin_login.html')

@app.route('/admin/requests')
@login_required
def admin_requests():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT r.*, t.name AS team_name, p.name AS player_name FROM requests r '
              'LEFT JOIN teams t ON r.team_id=t.id '
              'LEFT JOIN players p ON r.player_id=p.id')
    requests_data = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template('admin_requests.html', requests=requests_data)

@app.route('/admin/requests/approve/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id=?', (request_id,))
    req = c.fetchone()
    if not req:
        flash("Request not found.")
        return redirect(url_for('admin_requests'))

    if req['type'] == 'lineup':
        # For simplicity, store lineups as text; you can extend to a separate table if needed
        pass

    elif req['type'] == 'player':
        c.execute('SELECT * FROM players WHERE id=?', (req['player_id'],))
        player = c.fetchone()
        if player:
            c.execute('''
                UPDATE players
                SET goals=?, assists=?, clean_sheets=?, goal_line_clearances=?
                WHERE id=?
            ''', (req['goals'], req['assists'], req['clean_sheets'], req['goal_line_clearances'], req['player_id']))

    elif req['type'] == 'update_stat':
        stat = req['stat']
        increment = req['increment'] or 0
        if stat in ['played', 'wins', 'draws', 'losses']:
            c.execute(f'''
                UPDATE teams SET {stat}={stat}+?, points=(wins*3 + draws) WHERE id=?
            ''', (increment, req['team_id']))

    # Delete request after approval
    c.execute('DELETE FROM requests WHERE id=?', (request_id,))
    conn.commit()
    conn.close()
    flash("Request approved and applied!")
    return redirect(url_for('admin_requests'))

@app.route('/admin/requests/deny/<int:request_id>', methods=['POST'])
@login_required
def deny_request(request_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM requests WHERE id=?', (request_id,))
    conn.commit()
    conn.close()
   
