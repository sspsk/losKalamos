from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from werkzeug.exceptions import abort

from loskalamos.db import get_db
import psycopg2.extras

bp = Blueprint('reports',__name__)

@bp.route('/report', methods = ('POST', ))
def report():

    type = request.form['type']
    area = request.form['area']
    mulf = request.form['mulf']
    db = get_db()
    cur = db.cursor()
    error = None

    if not type:
        error = 'Type is required.'
    elif not area:
        error = 'Area is required.'
    elif not mulf:
        error = 'Mulfunction is required'

    if error is None:
        cur.execute('INSERT INTO report (type, area, mulf) VALUES (%s, %s, %s)', (type, area, mulf))
        db.commit()
        flash('Successful report.')

    if error is not  None:
        flash(error)
    cur.close()
    return redirect(url_for('auth.index'))

@bp.route('/entries')
def entries():
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    if g.user['type'] == "admin":
        cur.execute('SELECT p.id, p.type, area, mulf, takenby, username FROM report p JOIN technician u ON p.takenby = u.id ORDER BY created DESC')
        poststaken = cur.fetchall()
        cur.execute('SELECT * FROM report WHERE takenby IS NULL ORDER BY created DESC')
        postsnottaken = cur.fetchall()
    else:
        cur.execute('SELECT p.id, p.type, area, mulf, takenby, username FROM report p JOIN technician u ON p.takenby = u.id  WHERE p.type = %s AND p.takenby = %s ORDER BY created DESC ',(g.user['type'], g.user['id']))
        poststaken = cur.fetchall()
        cur.execute('SELECT * FROM report WHERE takenby IS NULL AND type = %s ORDER BY created DESC',(g.user['type'], ))
        postsnottaken = cur.fetchall()
    cur.close()
    return render_template('reports/entries.html',poststaken = poststaken, postsnottaken = postsnottaken )


def get_report(id):
    cur = get_db().cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM report WHERE id = %s',(id,))
    report = cur.fetchone()

    if report is None:
        abort(404, "Post id {0} doesn't exist.".format(id))


    cur.close()
    return report

@bp.route('/<int:id>/take', methods = ('POST',))
def take(id):
    db = get_db()
    cur = db.cursor()
    report = get_report(id)
    if report['takenby'] is not None:
        abort(403,"Already taken.")
    cur.execute('UPDATE report SET takenby = %s WHERE id = %s',(g.user['id'],id))
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/delete', methods = ('POST',))
def delete(id):
    report = get_report(id)
    if report['takenby'] is None or report['takenby'] !=g.user['id']:
        abort(403)
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM report WHERE id = %s',(id, ))
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/undo', methods = ('POST',))
def undo(id):
    report = get_report(id)
    if report['takenby'] is None or report['takenby'] !=g.user['id']:
        abort(403)
    db = get_db()
    cur = db.cursor()
    print("pass")
    cur.execute('UPDATE report SET takenby = NULL WHERE id = %s',(id,))
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))
