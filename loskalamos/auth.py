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
    error  = None


    if not username:
        error = 'Username is required.'
    elif not password:
        error = 'Password is required.'
    elif db.execute('SELECT id FROM user WHERE username = ?',(username, )).fetchone() is not None:
        error = 'User {} is already registered.'.format(username)
    elif not type:
        error = 'Type is required.'

    if error is None:
        db.execute('INSERT INTO user (username, password, type) VALUES (?, ?, ?)',(username, generate_password_hash(password), type))
        db.commit()
        flash('Successful registration.')

    if error is not  None:
        flash(error)
    return redirect(url_for('reports.entries'))





@bp.route('/', methods=('GET','POST'))
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('reports.entries'))

        flash(error)

    return render_template('auth/index.html')

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
