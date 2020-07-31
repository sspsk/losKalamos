from flask import Blueprint, flash, g, redirect, render_template, request, url_for, Response, session, send_file, current_app

from werkzeug.exceptions import abort
#inside nojs branch
from loskalamos.db import get_db
import psycopg2.extras
import json
import time
import xlsxwriter
import os
import redis
import random
bp = Blueprint('reports',__name__)


def getKey(item):#function to return key to sort tuples
    return item[1]


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
    r = redis.Redis(db=1)
    error = None

    if not type:
        error = 'Επιλέξτε τύπο βλάβης.'
    elif not area:
        error = 'Επιλέξτε περιοχή στην κοινότητα.'
    elif not description:
        error = 'Προσθέστε περιγραφή της βλάβης'
    elif not region:
        error = 'Επιλέξτε κοινότητα.'
    elif not address:
        error = 'Προσθέστε διεύθυνση.'
    if error is None:
        cur.execute('INSERT INTO report (type, area, region, description, address, contact_name, contact_phone, done) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id', (type, area, region, description, address, contact_name, contact_phone,False))
        id = cur.fetchone()['id']
        keys = r.keys()
        with r.pipeline() as pipe:
            pipe.multi()
            for key in keys:
                pipe.set(key, 1)
            pipe.execute()
        db.commit()
        flash('Επιτυχημένη αναφορά. Id αναφοράς: {1}'.format(contact_name,id))

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
    res = None;
    #if req from search
    if(report_id == ""):
        cur.close()
        return Response(json.dumps([None,g.user['id']],default=str), mimetype='application/json')
    if(report is not None and g.user is None):
        cur.execute('SELECT id, type, area, region, address, description, done, takenby, created, contact_name FROM report WHERE id = %s',(report_id,))
        poststaken = cur.fetchone()
        cur.execute('SELECT id, type, area, region, address, description, done, takenby, created, contact_name FROM report WHERE takenby IS NULL AND id = %s',(report_id,))
        postsnottaken = cur.fetchone()
        if poststaken is None:
            res = postsnottaken
        else:
            res = poststaken
        cur.close()
        return Response(json.dumps([res,1],default=str), mimetype='application/json')
    if g.user['type'] == "admin":
        if g.user['region'] == "admin": #show all in all regions
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username, created, p.contact_name FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s ORDER BY id DESC',(False,))
            poststaken = cur.fetchall()
            cur.execute('SELECT id, type, area, region, address, description, created, contact_name FROM report WHERE takenby IS NULL AND done = %s ORDER BY id DESC',(False,))
            postsnottaken = cur.fetchall()
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username, created, p.contact_name FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s ORDER BY id DESC',(True,))
            postscompleted = cur.fetchall()

        else: #show all in admin's region
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username, created,  p.contact_name  FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s AND p.region = %s ORDER BY id DESC',(False,g.user['region']))
            poststaken = cur.fetchall()
            cur.execute('SELECT id, type, area, region, address, description, created, contact_name FROM report WHERE takenby IS NULL AND done = %s AND region = %s ORDER BY id DESC',(False,g.user['region']))
            postsnottaken = cur.fetchall()
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username, created,  p.contact_name FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s AND p.region = %s ORDER BY id DESC',(True,g.user['region']))
            postscompleted = cur.fetchall()
    else:
        cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username, created, p.contact_name FROM report p JOIN technician u ON p.takenby = u.id  WHERE p.type = %s AND p.region = %s AND p.takenby = %s AND done = %s ORDER BY id DESC ',(g.user['type'], g.user['region'], g.user['id'], False))
        poststaken = cur.fetchall()
        cur.execute('SELECT id, type, area, region, address, description, created, contact_name FROM report WHERE takenby IS NULL AND type = %s AND region = %s AND done = %s ORDER BY id DESC',(g.user['type'], g.user['region'], False))
        postsnottaken = cur.fetchall()
        postscompleted = []
    cur.close()
    return render_template('reports/entries.html',poststaken = poststaken, postsnottaken = postsnottaken ,regions=sorted(regions,key=getKey) ,postscompleted = postscompleted)


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
    if report['type'] != g.user['type'] and g.user['type'] != "admin":
        abort(403,"Not the same type of work")
    cur.execute('UPDATE report SET takenby = %s WHERE id = %s',(g.user['id'],id))
    cur.execute('UPDATE update_check SET check_bit = 1')
    print("EGINE 1 SE OLOUS APO TAKE")
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/done', methods = ('POST',))
def done(id):
    report = get_report(id)
    if report['takenby'] is None or report['takenby'] !=g.user['id']:
        abort(403)
    if report['type'] != g.user['type'] and g.user['type'] != "admin":
        abort(403,"Not the same type of work")
    db = get_db()
    cur = db.cursor()
    cur.execute('UPDATE report SET done = %s WHERE id = %s',(True, id))
    cur.execute('UPDATE update_check SET check_bit = 1')
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/undo', methods = ('POST',))
def undo(id):
    report = get_report(id)
    if report['takenby'] is None or report['takenby'] !=g.user['id']:
        abort(403)
    if report['type'] != g.user['type'] and g.user['type'] != "admin":
        abort(403,"Not the same type of work")
    db = get_db()
    cur = db.cursor()
    cur.execute('UPDATE report SET takenby = NULL WHERE id = %s',(id,))
    cur.execute('UPDATE update_check SET check_bit = 1')
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/delete', methods = ('POST',))
def delete(id):
    if g.user['type'] != "admin":
        abort(403,"action denied")
    db = get_db()
    cur = db.cursor()
    cur.execute('DELETE FROM report WHERE id = %s',(id,))
    cur.execute('UPDATE update_check SET check_bit = 1')
    cur.close()
    db.commit()
    return redirect(url_for('reports.entries'))

@bp.route('/<int:id>/update',methods = ('POST','GET'))
def report_update(id):
    if g.user['type'] != "admin":#controls who has rights to update a report, maybe needs change
        abort(403,"action denied")
    if request.method == 'GET':
        report = get_report(id)
        return render_template('reports/update.html',report = report)
    else:
        new_desc = request.form['description']
        rep_id = request.form['id']
        if new_desc is None or new_desc == "":
            flash("Η περιγραφή δεν μπορεί να είναι κενή")
            return redirect(url_for('reports.report_update',id = id))
        else:
            db = get_db()
            cur = db.cursor()
            cur.execute("UPDATE report SET description = %s WHERE id = %s",(new_desc,rep_id))
            db.commit()
            cur.close()
            flash("Επιτυχής ενημέρωση αναφοράς")
            return redirect(url_for('reports.report_update',id = rep_id))

#url to download reports

@bp.route('/downloads')
def download():
    db=get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    posts = request.args.get('posts')
    if g.user['type'] == "admin":
        if g.user['region'] == "admin": #show all in all regions
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, username, created, contact_name, contact_phone FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s ORDER BY id DESC',(False,))
            poststaken = cur.fetchall()
            cur.execute('SELECT id, type, area, region, address, description, created, contact_name, contact_phone FROM report WHERE takenby IS NULL AND done = %s ORDER BY id DESC',(False,))
            postsnottaken = cur.fetchall()
            cur.execute('SELECT p.id, p.type, area, p.region, address, description,  username, created, contact_name, contact_phone FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s ORDER BY id DESC',(True,))
            postscompleted = cur.fetchall()

        else:   #show all in admin's region
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, username, created, contact_name, contact_phone FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s AND p.region = %s ORDER BY id DESC',(False,g.user['region']))
            poststaken = cur.fetchall()
            cur.execute('SELECT id, type, area, region, address, description, created, contact_name, contact_phone FROM report WHERE takenby IS NULL AND done = %s  AND region = %s ORDER BY id DESC',(False,g.user['region']))
            postsnottaken = cur.fetchall()
            cur.execute('SELECT p.id, p.type, area, p.region, address, description, username, created, contact_name, contact_phone FROM report p JOIN technician u ON p.takenby = u.id WHERE done = %s AND p.region = %s ORDER BY id DESC',(True,g.user['region']))
            postscompleted = cur.fetchall()
    else:
        cur.execute('SELECT p.id, p.type, area, p.region, address, description, username, created, contact_name, contact_phone FROM report p JOIN technician u ON p.takenby = u.id  WHERE p.type = %s AND p.region = %s AND p.takenby = %s AND done = %s ORDER BY id DESC ',(g.user['type'], g.user['region'], g.user['id'], False))
        poststaken = cur.fetchall()
        cur.execute('SELECT id, type, area, region, address, description, created, contact_name, contact_phone FROM report WHERE takenby IS NULL AND type = %s AND region = %s AND done = %s ORDER BY id DESC',(g.user['type'], g.user['region'], False))
        postsnottaken = cur.fetchall()

    row = 0
    col = 0


    workbook = xlsxwriter.Workbook(os.path.join(current_app.instance_path, 'completedReports.xlsx'))
    worksheet = workbook.add_worksheet()
    if posts == "completed":
        print(type(postscompleted[0]))
        for item in postscompleted:
            for i in range(0,len(item)):
                worksheet.write(row,col + i,str(item[i]))
            worksheet.write(row,col+len(item),"Ολοκληρώθηκε")
            row +=1
    elif posts =="taken":
        for item in poststaken:
            for i in range(0,len(item)):
                worksheet.write(row,col + i,str(item[i]))
            worksheet.write(row,col+len(item),"Υπο αναλαβή")
            row +=1
    else:
        for item in postsnottaken:
            for i in range(0,len(item)):
                worksheet.write(row,col + i,str(item[i]))
            worksheet.write(row,col+len(item),"Διαθέσιμο")
            row +=1
    cur.close()
    workbook.close()
    return send_file(os.path.join(current_app.instance_path, 'completedReports.xlsx'), attachment_filename='completedReports.xlsx')






@bp.route('/update')
def update():
    r = redis.Redis(db=1)
    random.seed()
    mykey = random.randint(1,100)
    while(r.exists(mykey)):
        mykey = random.randint(1,100)
    r.set(mykey,0)
    print("pass")
    hits = 1
    res=0
    while(res == 0):
        time.sleep(1)
        print(hits)
        hits +=1
        res = int(r.get(mykey))
        if hits >= 30:
            r.delete(mykey)
            return Response(json.dumps(None),mimetype='application/json')
    r.delete(mykey)
    return Response(json.dumps([1], default = str),mimetype='application/json')
