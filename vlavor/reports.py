from flask import Blueprint, flash, g, redirect, render_template, request, url_for, Response, session, send_file, current_app

from werkzeug.exceptions import abort
#inside nojs branch
from vlavor.db import get_db
from vlavor.req import send,TokenParser
import psycopg2.extras
import json
import time
import xlsxwriter
import os
import redis
import random

bp = Blueprint('reports',__name__)

#auxiliary functions
def getKey(item):#function to return key to sort tuples
    return item[1]
def isValidPhoneNumber(num):
    return (num >= 6900000000 and num <=6999999999)

@bp.route('/vlavor/<int:src>/report', methods = ('POST', ))#src == 0 return to tech else return to civil
def report(src):
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
    elif contact_phone != "" and not isValidPhoneNumber(int(contact_phone)): #if given invalid number
        error = 'Μη εγκυρος αριθμος τηλεφώνου'
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
        if contact_phone != "" : #if given phone number
            parser = TokenParser()
            send(parser,os.environ['WEB2SMS_USR'],os.environ['WEB2SMS_PSW'],contact_phone,'Η αναφορά σας με Α/Α:{0} καταχωρήθηκε.'.format(id))
    if error is not  None:
        flash(error)
    cur.close()
    if src == 0:
        return redirect(url_for('auth.index'))
    else:
        return redirect(url_for('auth.civil_index'))

@bp.route('/vlavor/entries')
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
        #get posts from user(all if he is the admin)
        if g.user['username'] == "admin":
            cur.execute('SELECT * FROM board')
            posts = cur.fetchall()
        else:
            cur.execute('SELECT * FROM board WHERE doneby = %s',(g.user['id'],))
            posts = cur.fetchall()
    else:
        cur.execute('SELECT p.id, p.type, area, p.region, address, description, takenby, username, created, p.contact_name FROM report p JOIN technician u ON p.takenby = u.id  WHERE p.type = %s AND p.region = %s AND p.takenby = %s AND done = %s ORDER BY id DESC ',(g.user['type'], g.user['region'], g.user['id'], False))
        poststaken = cur.fetchall()
        cur.execute('SELECT id, type, area, region, address, description, created, contact_name FROM report WHERE takenby IS NULL AND type = %s AND region = %s AND done = %s ORDER BY id DESC',(g.user['type'], g.user['region'], False))
        postsnottaken = cur.fetchall()
        postscompleted = []
        posts = []
    cur.close()
    return render_template('reports/entries.html',poststaken = poststaken, postsnottaken = postsnottaken ,regions=sorted(regions,key=getKey) ,postscompleted = postscompleted,posts = posts)


def get_report(id):
    cur = get_db().cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM report WHERE id = %s',(id,))
    report = cur.fetchone()

    if report is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    cur.close()
    return report

def get_post(id):
    cur = get_db().cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM board WHERE id = %s',(id,))
    post = cur.fetchone()
    cur.close()
    return post

@bp.route('/vlavor/<int:id>/take', methods = ('POST',))
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

@bp.route('/vlavor/<int:id>/done', methods = ('POST',))
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
    contact_phone = report['contact_phone']
    id = report['id']
    if contact_phone != "" : #if given phone number
        parser = TokenParser()
        send(parser,os.environ['WEB2SMS_USR'],os.environ['WEB2SMS_PSW'],contact_phone,'Η αναφοράς σας με Α/Α:{0} διεκπεραιώθηκε.Ευχαριστουμε.'.format(id))
    return redirect(url_for('reports.entries'))

@bp.route('/vlavor/<int:id>/undo', methods = ('POST',))
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

@bp.route('/vlavor/<int:id>/delete', methods = ('POST',))
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

@bp.route('/vlavor/<int:id>/update',methods = ('POST','GET'))
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

@bp.route('/vlavor/downloads')
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


@bp.route('/vlavor/post/<int:doneby>',methods = ("POST",))
def post(doneby):
    if g.user['type'] != "admin":
        abort(403,"action denied")
    error = None
    db = get_db()
    cursor = db.cursor()
    title = request.form['title']
    description = request.form['description']
    if title is None or title == "":
        error = "Το πεδίο τίτλος είναι υποχρεωτικό"
    if description is None or description == "":
        error = "Το πεδίο περιγραφή είναι υποχρεωτικό"
    if error is not None:
        flash(error)
        return redirect(url_for('reports.entries'))
    cursor.execute("INSERT INTO board(title,description,doneby) values(%s,%s,%s)",(title,description,doneby))
    db.commit()
    cursor.close()
    flash("Επιτυχής ανάρτηση ανακοίνωσης")
    return redirect(url_for('reports.entries'))


@bp.route('/vlavor/post/<int:post_id>/delete',methods = ("POST",))
def del_post(post_id):
    if g.user['type'] != "admin":
        abort(403,"action denied")
    db = get_db()
    cursor = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM board WHERE id = %s",(post_id,))
    post = cursor.fetchone()
    if post is None:
        flash("Μη υπαρκτή ανακοίνωση")
        return redirect(url_for('reports.entries'))
    if g.user['username'] == "admin":
        cursor.execute("DELETE FROM board WHERE id = %s",(post_id,))
        cursor.close()
        db.commit()
        flash("Επιτυχής διαγραφή ανακοίνωσης")
        return redirect(url_for('reports.entries'))

    else:
        print(post)
        if post['doneby'] != g.user['id']:
            abort(403,"action denied")
        cursor.execute("DELETE FROM board WHERE id = %s",(post_id,))
        cursor.close()
        db.commit()
        flash("Επιτυχής διαγραφή ανακοίνωσης")
        return redirect(url_for('reports.entries'))


@bp.route('/vlavor/post/<int:post_id>/update',methods=("GET","POST"))
def update_post(post_id):
    if g.user['type'] != "admin":
        abort(403,"action denied")
    post = get_post(post_id)
    if post is None:
        flash("Μη υπαρκτή ανακοίνωση")
        return redirect(url_for('reports.entries'))
    if request.method == "GET":
        return render_template('reports/post_update.html',post=post)
    else:
        newtitle = request.form['title']
        newdesc = request.form['description']
        if newtitle is None or newtitle == '':
            flash("Ο τίτλος δεν μπορεί να είναι κενός.")
            return redirect(url_for('reports.update_post',post_id=post_id))
        if newdesc is None or newdesc == '':
            flash("Η περιγραφή δεν μπορεί να είναι κενή.")
            return redirect(url_for('reports.update_post',post_id=post_id))
        db = get_db()
        cursor =  db.cursor(cursor_factory = psycopg2.extras.DictCursor)
        cursor.execute("UPDATE board SET title = %s, description = %s WHERE id = %s",(newtitle,newdesc,post_id))
        cursor.close()
        db.commit()
        flash("Επιτυχής ενημέρωση ανακοίνωσης")
        return redirect(url_for('reports.update_post',post_id=post_id))



@bp.route('/vlavor/update')
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
