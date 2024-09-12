import sqlite3
from flask import Flask, g

DATABASE = 'database.db'

app = Flask(__name__,
            # static_url_path='/static', 
            static_folder='web/static',
            template_folder='web/templates')

def get_db():
    # db = getattr(g, '_database', None)
    # if db is None:
    #     db = g._database = sqlite3.connect(DATABASE)
        
        
    return sqlite3.connect(DATABASE)

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def query_db_all(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    for row in rows:
        print(row)

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        
if __name__ == '__main__':
            # init_db()
        with app.app_context():
            query_db(query='INSERT INTO chat(content) VALUES("Let me try2")')
            print(query_db(query='select * from chat'))