from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from werkzeug.exceptions import abort

from loskalamos.db import get_db


bp = Blueprint('reports',__name__)

@bp.route('/report', methods = ('POST', ))
def report():

    type = request.form['type']
    area = request.form['area']
    mulf = request.form['mulf']
    db = get_db()
    error = None

    if not type:
        error = 'Type is required.'
    elif not area:
        error = 'Area is required.'
    elif not mulf:
        error = 'Mulfunction is required'

    if error is None:
        db.execute('INSERT INTO report (type, area, mulf) VALUES (?, ?, ?)', (type, area, mulf))
        db.commit()
        flash('Successful report.')

    if error is not  None:
        flash(error)
    return redirect(url_for('auth.index'))

@bp.route('/entries')
def entries():
    db = get_db()
    if g.user['username'] == "admin":
        poststaken = db.execute('SELECT p.id, p.type, area, mulf, takenby, username FROM report p JOIN user u ON p.takenby = u.id ORDER BY created DESC').fetchall()
        postsnottaken = db.execute('SELECT * FROM report WHERE takenby IS NULL ORDER BY created DESC').fetchall()
    else:
        poststaken =  db.execute('SELECT p.id, p.type, area, mulf, takenby, username FROM report p JOIN user u ON p.takenby = u.id  WHERE p.type = ? AND p.takenby = ? ORDER BY created DESC ',(g.user['type'], g.user['id'])).fetchall()
        postsnottaken = db.execute('SELECT * FROM report WHERE takenby IS NULL AND type = ? ORDER BY created DESC',(g.user['type'], )).fetchall()
    return render_template('reports/entries.html',poststaken = poststaken, postsnottaken = postsnottaken )


def get_report(id):
    report = get_db().execute(
        'SELECT * FROM report WHERE id = ?',
        (id,)
    ).fetchone()

    if report is None:
        abort(404, "Post id {0} doesn't exist.".format(id))



    return report

@bp.route('/<int:id>/take', methods = ('POST',))
def take(id):
    db = get_db()
    report = get_report(id)
    if report['takenby'] is not None:
        abort(403,"Already taken.")
    db.execute('UPDATE report SET takenby = ? WHERE id = ?',(g.user['id'],id))
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/delete', methods = ('POST',))
def delete(id):
    report = get_report(id)
    if report['takenby'] is None or report['takenby'] !=g.user['id']:
        abort(403)
    db = get_db()
    db.execute('DELETE FROM report WHERE id = ?',(id, ))
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/undo', methods = ('POST',))
def undo(id):
    report = get_report(id)
    if report['takenby'] is None or report['takenby'] !=g.user['id']:
        abort(403)
    db = get_db()
    db.execute('UPDATE report SET takenby = NULL WHERE id = ?',(id,))
    db.commit()
    return redirect(url_for('reports.entries'))
