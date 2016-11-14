# import necessary libraries
import os
import time
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash, url_for

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# set secret_key in order to use session
app.secret_key = 'come on, just a simple project'

# set database URI, connecting to test.db for test
DATABASEURI = "postgresql://zz2406:hdt76@104.196.175.120/postgres"

# create database engine using above URI
engine = create_engine(DATABASEURI)

# global value for the top bar
leagues = []


# start and terminate database connection


@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        print "uh oh, problem connecting to database"
        import traceback;
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
    except Exception as e:
        pass


# web application implementation
# cursor return in tuples


@app.route('/')
def homepage():
    if not leagues:
        cursor = g.conn.execute('''SELECT * FROM leagues''')
        for row in cursor:
            leagues.append(row)
        cursor.close()
    context = {'league': leagues}
    if session.get('logged_in'):
        context['uid'] = session['uid']
        context['username'] = session['username']
    return render_template("homepage.html", **context)


@app.route('/team')
def team():
    cursor1 = g.conn.execute('''SELECT * FROM teams_belong
  WHERE league_name=%s
  ''', request.args['league_name'])
    cursor2 = g.conn.execute('''SELECT * FROM matches_include
  WHERE league_name=%s
''', request.args['league_name'])
    teams = [];
    matches = []
    for row1 in cursor1:
        teams.append(row1)
    cursor1.close()
    for row2 in cursor2:
        matches.append(row2)
    cursor2.close()
    context = {'team': teams, 'match': matches, 'league': leagues}
    return render_template("team.html", league_name=request.args['league_name'], url=request.args['url'], **context)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        cursor = g.conn.execute("SELECT * FROM users WHERE e_mail=%s AND passwd=%s",
                                request.form['email'], request.form['password'])
        if cursor.rowcount == 0:
            error = 'Invalid email and password combination!!'
        else:
            session['logged_in'] = True
            userinfo = cursor.fetchone()
            session['uid'] = userinfo[0]
            session['username'] = userinfo[1]
            session['email'] = userinfo[2]
            return redirect(url_for('homepage'))
    else:
        pass
    context = {'league': leagues}
    return render_template("login.html", error=error, **context)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('uid', None)
    session.pop('username', None)
    session.pop('email', None)
    flash("You were logged out!!")
    return redirect(url_for('homepage'))


@app.route('/favorite')
def favorite():
    if not session.get('uid'):
        return redirect(url_for('login'))
    else:
        cursor = g.conn.execute('''SELECT * FROM favorite WHERE uid=%s''', session['uid'])
        favorite_teams = []
        for row in cursor:
            favorite_teams.append(row['team_name'])
        cursor.close()
        context = {'favorite_team': favorite_teams, 'uid': session['uid'], 'league': leagues}
        return render_template("favorite.html", **context)


@app.route('/add_favorite', methods=['GET', 'POST'])
def add_favorite():
    if request.method == 'POST':
        cursor1 = g.conn.execute('''SELECT * FROM teams_belong WHERE team_name=%s''', request.form['teamname'].title())
        cursor2 = g.conn.execute('''SELECT * FROM favorite WHERE uid=%s AND team_name=%s''', session['uid'],
                                 request.form['teamname'].title())
        if cursor1.rowcount == 0:
            flash("The team you added cannot be found in the database!!")
        elif cursor2.rowcount != 0:
            flash("This team is already in your favorite!!")
        else:
            g.conn.execute('''INSERT INTO favorite(uid, team_name) VALUES (%s, %s)''', session['uid'],
                           request.form['teamname'].title())
            flash("You have successfully added a team to your favorite!!")
        cursor1.close();
        cursor2.close()
    return redirect(url_for('favorite'))


@app.route('/delete_favorite')
def delete_favorite():
    g.conn.execute('''DELETE FROM favorite WHERE uid=%s AND team_name=%s''', session['uid'],
                   request.args['teamname'].title())
    flash("You have successfully deleted the team from your favorite!!")
    return redirect(url_for('favorite'))


@app.route('/comment', methods=['GET', 'POST'])
def comment():
    if request.method == 'POST':
        home_guest = [request.args['home'], request.args['guest']]
        now = time.localtime()
        time_now = "%s/%s/%s %s:%s:%s" % (now[0], now[1], now[2], now[3], now[4], now[5])
        comment_id = str(session['uid'])
        for num in now[0:6]:
            comment_id += str(num)
        if not request.form['text']:
            flash('Please write something!!')
        else:
            g.conn.execute('''INSERT INTO comment VALUES (%s, %s, %s, %s, %s, %s)''', comment_id, home_guest,
                           request.args['schedule'], time_now, request.form['text'], session['uid'])
    else:
        pass

    cursor = g.conn.execute('''SELECT * FROM comment, users WHERE schedule=%s AND comment.uid=users.uid''',
                            request.args['schedule'])
    comments = []
    for row in cursor:
        if row['home_guest'] == [request.args['home'], request.args['guest']]:
            comments.append(row)
    comments = sorted(comments, key=lambda x: x[3], reverse=True)
    context = {'comment': comments, 'home': request.args['home'], 'guest': request.args['guest'],
               'schedule': request.args['schedule'], 'league': leagues}
    cursor.close()
    return render_template("comment.html", **context)


@app.route('/teaminfo')
def teaminfo():
    cursor1 = g.conn.execute('''SELECT * FROM players_join WHERE team_name=%s''', request.args['teamname'])
    cursor2 = g.conn.execute('''SELECT * FROM matches_include''')
    cursor3 = g.conn.execute('''SELECT * FROM performance WHERE team_name=%s''', request.args['teamname'])
    players = [];
    matches = [];
    performances = []
    for row in cursor1:
        players.append(row)
    for row in cursor2:
        if row['home_guest'][0] == request.args['teamname'] or row['home_guest'][1] == request.args['teamname']:
            matches.append(row)
    for row in cursor3:
        performances.append(row)
    context = {'player': players, 'match': matches, 'teamname': request.args['teamname'], 'performance': performances,
               'league': leagues}
    cursor1.close()
    cursor2.close()
    return render_template("teaminfo.html", **context)


# default settings(keep unchanged)
if __name__ == "__main__":
    import click


    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8080, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using
            python server.py
        Show the help text using
            python server.py --help
        """

        HOST, PORT = host, port
        print "running on %s:%d" % (HOST, PORT)
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


    run()
