from flask import Blueprint, flash, g, redirect, render_template, request, url_for, Response

from werkzeug.exceptions import abort

from loskalamos.db import get_db
import psycopg2.extras
import json

bp = Blueprint('reports',__name__)

@bp.route('/getareas',methods = ('GET',))
def getareas():
    region = request.args.get('region')
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM region WHERE name = %s',(region,))
    region_id = cur.fetchone()[0]
    cur.execute('SELECT * FROM area WHERE region_id = %s',(region_id,))
    areas = cur.fetchall()
    return Response(json.dumps(areas), mimetype='application/json')



@bp.route('/report', methods = ('POST', ))
def report():

    type = request.form['type']
    area = request.form['area']
    description = request.form['description']
    region = request.form['region']
    address = request.form['address']
    contact_name = request.form['contact_name']
    contact_phone = request.form['contact_phone']
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    error = None

    if not type:
        error = 'Type is required.'
    elif not area:
        error = 'Area is required.'
    elif not description:
        error = 'Description is required'
    elif not region:
        error = 'Region is required.'
    elif not address:
        error = 'Address is required.'
    if error is None:
        cur.execute('INSERT INTO report (type, area, region, description, address, contact_name, contact_phone) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id', (type, area, region, description, address, contact_name, contact_phone))
        id = cur.fetchone()['id']
        db.commit()
        flash('Thank you {0}. Successful report. Id of report: {1}'.format(contact_name,id))

    if error is not  None:
        flash(error)
    cur.close()
    return redirect(url_for('auth.index'))

@bp.route('/entries')
def entries():
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM region')
    regions = cur.fetchall()
    report_id = request.args.get('report_id')
    if g.user['type'] == "admin":
        if report_id is None:
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username FROM report p JOIN technician u ON p.takenby = u.id ORDER BY created DESC')
            poststaken = cur.fetchall()
            cur.execute('SELECT * FROM report WHERE takenby IS NULL ORDER BY created DESC')
            postsnottaken = cur.fetchall()
        else:
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username FROM report p JOIN technician u ON p.takenby = u.id WHERE p.id = %s',(report_id,))
            poststaken = cur.fetchall()
            cur.execute('SELECT * FROM report WHERE takenby IS NULL AND id = %s',(report_id,))
            postsnottaken = cur.fetchall()
    else:
        cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username FROM report p JOIN technician u ON p.takenby = u.id  WHERE p.type = %s AND p.region = %s AND p.takenby = %s ORDER BY created DESC ',(g.user['type'], g.user['region'], g.user['id']))
        poststaken = cur.fetchall()
        cur.execute('SELECT * FROM report WHERE takenby IS NULL AND type = %s AND region = %s ORDER BY created DESC',(g.user['type'], g.user['region']))
        postsnottaken = cur.fetchall()
    cur.execute('SELECT id FROM report ORDER BY id DESC LIMIT 1')
    latest_id = cur.fetchone()
    cur.close()
    return render_template('reports/entries.html',poststaken = poststaken, postsnottaken = postsnottaken ,regions=regions,latest_id = latest_id)


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

@bp.route('/entriesUpdate')
def entriesUpdate():
    last = request.args.get('last')
    db= get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT id FROM report ORDER BY id DESC LIMIT 1')
    latest_id = cur.fetchone()[0]
    while(int(latest_id) <= int(last)):
        cur.execute('SELECT id FROM report ORDER BY id DESC LIMIT 1')
        latest_id = cur.fetchone()[0]
    cur.execute('SELECT id, type, region, area, address, description FROM report WHERE id > %s ORDER BY id DESC',(last, ))
    res = cur.fetchall()
    return  Response(json.dumps(res), mimetype='application/json')
