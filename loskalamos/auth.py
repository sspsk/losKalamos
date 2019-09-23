import functools

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from werkzeug.security import check_password_hash, generate_password_hash

from loskalamos.db import get_db

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=('POST', ))
def register():
    username = request.form['username']
    password = request.form['password']
    type = request.form['type']
    db = get_db()
    cur = db.cursor()
    error  = None

    cur.execute('SELECT id FROM technician WHERE username = %s',(username, ))
    if not username:
        error = 'Username is required.'
    elif not password:
        error = 'Password is required.'
    elif cur.fetchone() is not None:
        error = 'User {} is already registered.'.format(username)
    elif not type:
        error = 'Type is required.'

    if error is None:
        cur.execute('INSERT INTO technician (username, password, type) VALUES (%s, %s, %s)',(username, generate_password_hash(password), type))
        db.commit()
        flash('Successful registration.')

    if error is not  None:
        flash(error)
    cur.close()
    return redirect(url_for('reports.entries'))





@bp.route('/', methods=('GET','POST'))
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cur = db.cursor()
        error = None
        cur.execute('SELECT * FROM technician WHERE username = %s', (username,))
        user = cur.fetchone()
        cur.close()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user[2], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user[0]
            return redirect(url_for('reports.entries'))

        flash(error)

    return render_template('auth/index.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    cur = get_db().cursor()
    if user_id is None:
        g.user = None
    else:
        cur.execute('SELECT * FROM technician WHERE id = %s', (user_id,))
        g.user = cur.fetchone()
    cur.close()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
