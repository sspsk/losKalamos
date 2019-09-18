from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from werkzeug.exceptions import abort

from loskalamos.db import get_db


bp = Blueprint('reports',__name__)

@bp.route('/report', methods = ('POST', ))
def report():

    type = request.form['type']
    area = request.form['area']
    db = get_db()
    error = None

    if not type:
        error = 'Type is required.'
    elif not area:
        error = 'Area is required.'

    if error is None:
        db.execute('INSERT INTO report (type, area) VALUES (?,?)', (type, area))
        db.commit()
        flash('Successful report.')

    if error is not  None:
        flash(error)
    return redirect(url_for('auth.index'))

@bp.route('/entries')
def entries():
    db = get_db()
    if g.user['username'] == "admin":
        posts = db.execute('SELECT type, area FROM report ORDER BY created DESC').fetchall()
    else:
        posts =  db.execute('SELECT type, area FROM report WHERE type = ? ORDER BY created DESC ',(g.user['type'], )).fetchall()
    return render_template('reports/entries.html',posts = posts )
