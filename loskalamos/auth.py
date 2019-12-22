import functools
import psycopg2.extras
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, Response
import json

from werkzeug.security import check_password_hash, generate_password_hash

from loskalamos.db import get_db

bp = Blueprint('auth', __name__)

def getKey(item):#function to return key to sort tuples
    return item[1]

@bp.route('/addregion', methods=('POST', ))
def addregion():
    db = get_db()
    cur = db.cursor()
    region = request.form['region']##add to upper,remove spaces
    error = None
    cur.execute('SELECT * FROM region WHERE name = %s',(region, ))
    if not region:
        error = "Please fill the form."
    if cur.fetchone()  is not None:
        error = "Region: {} already added.".format(region)
    if error is None:
        cur.execute('INSERT INTO region ( name) VALUES (%s)',(region, ))
        db.commit()
        flash("Επιτυχημενη προσθεση κοινοτητας: {}".format(region))
    if error is not None:
        flash(error)
    cur.close()
    return redirect(url_for('reports.entries'))

@bp.route('/addarea', methods=('POST', ))
def addarea():
    db = get_db()
    cur = db.cursor()
    area = request.form['area']
    region = request.form['region']
    error = None
    cur.execute('SELECT id FROM region WHERE name = %s',(region, ))
    id = cur.fetchone()
    cur.execute('SELECT * FROM area WHERE name = %s AND region_id = %s',(area, id))
    if not area:
        error = "Please fill the form."
    if cur.fetchone()  is not None:
        error = "Area: {} already added in region: {}.".format(area,region)
    if error is None:
        cur.execute('INSERT INTO area (name,region_id) VALUES (%s, %s)',(area, id))
        db.commit()
        flash("Επιτυχημενη προσθεση της περιοχης: {} στην κοινοτητα: {}".format(area,region))
    if error is not None:
        flash(error)
    cur.close()
    return redirect(url_for('reports.entries'))

@bp.route('/getareas',methods = ('GET',))
def getareas():
    region = request.args.get('region')
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM region WHERE name = %s',(region,))
    region_id = cur.fetchone()[0]
    cur.execute('SELECT * FROM area WHERE region_id = %s',(region_id,))
    areas = cur.fetchall()
    return Response(json.dumps(sorted(areas,key=getKey)), mimetype='application/json')       #return sorted the areas of some region

@bp.route('/register', methods=('POST', ))
def register():
    username = request.form['username']
    password = request.form['password']
    type = request.form['type']
    region = request.form['region']
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
    elif not region:
        error = 'Region is required.'

    if error is None:
        cur.execute('INSERT INTO technician (username, password, type, region) VALUES (%s, %s, %s, %s)',(username, generate_password_hash(password), type, region))
        cur.execute('INSERT INTO update_check (username,check_bit,refreshed,logged_in) VALUES (%s, %s, %s, %s)',(username,1,0,0))
        db.commit()
        flash('Επιτυχημενη δημιουργια τεχνικου.')

    if error is not  None:
        flash(error)
    cur.close()
    return redirect(url_for('reports.entries'))





@bp.route('/', methods=('GET','POST'))
def index():
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']


        error = None
        cur.execute('SELECT * FROM technician WHERE username = %s', (username,))
        user = cur.fetchone()


        if user is None:
            error = 'Δεν υπαρχει χρηστης με αυτο το ονομα χρηστη.'
        elif not check_password_hash(user['password'], password):
            error = 'Λανθασμενος κωδικας προσβασης.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            cur.execute('UPDATE update_check SET refreshed = 0 WHERE username = %s',(user['username'],))
            cur.execute('UPDATE update_check SET logged_in = 1 WHERE username = %s',(user['username'],))
            db.commit()
            return redirect(url_for('reports.entries'))

        flash(error)
    cur.execute('SELECT * FROM region')
    regions = cur.fetchall()
    cur.close()
    return render_template('auth/index.html', regions=sorted(regions,key=getKey)) #return sorted the regions

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    cur = get_db().cursor(cursor_factory = psycopg2.extras.DictCursor)
    if user_id is None:
        g.user = None
    else:
        cur.execute('SELECT * FROM technician WHERE id = %s', (user_id,))
        g.user = cur.fetchone()
    print("inside before_app_request")
    cur.close()

@bp.route('/logout')
def logout():
    session.clear()
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('UPDATE update_check SET logged_in = 0 WHERE username = %s',(g.user['username'],))
    db.commit()
    cur.close()
    return redirect(url_for('auth.index'))


@bp.route('/delRegion',methods = ('POST',))
def delRegion():
    region = request.form['region']
    print(region)
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM region WHERE name = %s',(region,))
    res = cur.fetchone()
    cur.execute('DELETE FROM region WHERE name = %s',(region,))
    db.commit()
    cur.execute('DELETE FROM area WHERE region_id = %s ',(res['id'],))
    db.commit()
    cur.close()
    return redirect(url_for('reports.entries'))

@bp.route('/delArea', methods=('POST',))
def delArea():
    area = request.form['area']
    db = get_db()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute('DELETE FROM area WHERE name = %s',(area,))
    db.commit()
    cur.close()
    return redirect(url_for('reports.entries'))
#delete region
#delete area
