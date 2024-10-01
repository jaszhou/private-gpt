"""
  This is the entry of Lambda function, it'll setup the routes and capture the request from API Gateway
  
"""
import logging
from flask import Flask, request, render_template, redirect, url_for, g

from flask_restful import Resource, Api, reqparse

import urllib3
from snapCopyFunction.utils import *
from snapCopyFunction.db import *
import awsgi, jsonify
from snapCopyFunction.bedrock import *


urllib3.disable_warnings()
        
app = Flask(__name__,
            # static_url_path='/static', 
            static_folder='web/static',
            template_folder='web/templates')

api = Api(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = reqparse.RequestParser()

init_db()


@app.route("/chat", methods=['POST'])
def chatbot():
    
    c = request.form.get('content')
    k = request.form.get('key')



    # result = chat_mock(c)
    result = talk_bedrock(c)

    resp = {
        "model": "llama3.2",
        "created_at": "2023-08-04T19:22:45.499127Z",
        "response": result,
        "done": True,
        "context": [1, 2, 3],
        "total_duration": 5043500667,
        "load_duration": 5025959,
        "prompt_eval_count": 26,
        "prompt_eval_duration": 325953000,
        "eval_count": 290,
        "eval_duration": 4709213000
    }
    
    return resp

# create a python function to generate qr code
@app.route("/generate")
def gen_code():

    uid, qrcode = generate_qr_code()
    
    return render_template("main.html", uid=uid, qrcode = qrcode)
    # return uid

@app.route("/pages/<key_id>", methods=['GET', 'POST'])
def pages(key_id):
    with app.app_context():
        cur = get_db().cursor()
    
    # new_url = f"https://f8do9lswp5.execute-api.ap-southeast-2.amazonaws.com/dev/pages/{key_id}"
    # new_url = f"/pages/{key_id}"
    uid, qrcode = generate_qr_code(uid = key_id)
    
    return render_template("main.html", uid=uid, qrcode = qrcode)

@app.route("/db_get/<key_id>", methods=['GET', 'POST'])
def get_all_rows(key_id):
    with app.app_context():
        cur = get_db().cursor()
        result = query_db_all(query='select * from chat where myid = \"'+ key_id +'\"')
        # print(result)
    return result

@app.route("/pages", methods=['GET', 'POST'])
def main_page():
    return render_template("main.html")

@app.route("/", methods=['GET', 'POST'])
def main():
    # return render_template("main.html")

    content = render_template("body.html")
    response = {
        "statusCode": 200,
        "body": content,
        "headers": {
            "Content-Type": "text/html"
        }
    }

    return response


@app.route("/db", methods=['GET', 'POST'])
def query():
    with app.app_context():
            print(query_db_all(query='select * from chat'))
            return query_db(query='select * from chat')

@app.route("/db_add", methods=['GET', 'POST'])
def add_query():
    c = request.form.get('content')
    k = request.form.get('key')
    qry = 'INSERT INTO chat(myid,content,LastModifiedTime) VALUES(\"'+ k +'\", \"'+ c +'\",CURRENT_TIMESTAMP)'
    # with app.app_context():
    print(f'query: {qry}')
    conn = get_db()
    cur = conn.cursor()
    cur.execute(qry)
    conn.commit()
    # rv = cur.fetchall()
    cur.close()
    # query_db(query=qry)
    print(query_db_all(query='select * from chat'))
    return query_db_all(query='select * from chat')
            
# Handle Lambda events
def lambda_handler(event, context):
    
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    logger.info(event)
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
       
    return awsgi.response(app, event, context)


    
if __name__ == '__main__':
    app.run(debug=True)

