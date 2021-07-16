import psycopg2.extras
import psycopg2
import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
import os


def get_connection():
    conn = None
    print("Connecting to the database.")
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn
def get_db():
    if 'db' not in g:
        g.db = get_connection() #database connection
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        print("Closing the database.")
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    print("Creating table")
    with current_app.open_resource('shema.sql') as f:
        cur.execute(f.read().decode('utf8'))
    cur.close()
    db.commit()


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    password = input('Set admin password: ')
    password  = generate_password_hash(password)
    db = get_db()
    cur = db.cursor()
    cur.execute('INSERT INTO technician (username, password, type, region) VALUES (%s, %s, %s, %s)',('admin', password, 'admin', 'admin'))
    cur.execute('INSERT INTO update_check (username,check_bit,refreshed,logged_in) VALUES (%s, %s, %s, %s)',('admin',1,0,0))
    cur.close()
    db.commit()
    click.echo('Initialized the database and set admin privilages.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
