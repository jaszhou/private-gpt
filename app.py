"""
  This is the entry of Lambda function, it'll setup the routes and capture the request from API Gateway
  Author: jason.zhou@cba.com.au
  
"""
import logging
from flask import Flask, request, render_template, redirect, url_for, g

from flask_restful import Resource, Api, reqparse

import urllib3
from utils import *
from db import *

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

class ScimUser(Resource):
    def put(self):
        
        print("this is the put method")
        
        print(request.get_json())
        
        # Parse request arguments
        args = parser.parse_args()
       
        # Access parsed arguments
        name = args['userName']
        id = args['id']
       
        # Do something with parsed arguments
        # return {'name': name, 'id': id}
        return {
        "statusCode": 200,
        "body": {'name': name, 'id': id},
        }
        
    def get(self):
        import base64
        print("this is the get method")
        
        print(request)
        
        # Parse request arguments
        with open('qr_code.png', 'rb') as image_file:
            base64_bytes = base64.b64encode(image_file.read())
            #print(base64_bytes)

            base64_string = base64_bytes.decode()
            print(base64_string) # For insert into the img tag.
            
            img = f'<img src=" \
                    data:image/png; \
                    data:image/png;base64,${base64_string} \
                    " alt="qr_code.png" />'
    
        # return {
        #     "statusCode": 200,
        #     # "body": {'status': 'OK'},
        #     'body': '<img src="./qr_code.png" />',
        #     'isBase64Encoded': True,
        #     'headers': {
        #         'Content-Type': 'image/png'
        # }
    
        image_path = 'qr_code.png' # point to your image location
        encoded_img = get_response_image(image_path)
        return {
            'Status' : 'Success', 'ImageBytes': encoded_img
        }
    
# Add the resources to the API
# api.add_resource(ScimUser, '/scim/v2/ScimUser')
# api.add_resource(ScimUser, '/')

# create a python function to generate qr code
@app.route("/generate")
def gen_code():
    uid = generate_qr_code()
    return render_template("main.html", uid=uid)

@app.route("/pages/<key_id>", methods=['GET', 'POST'])
def pages(key_id):
    with app.app_context():
        cur = get_db().cursor()
    return render_template("main.html", uid=key_id)


@app.route("/pages", methods=['GET', 'POST'])
def main_page():
    return render_template("main.html")

@app.route("/", methods=['GET', 'POST'])
def main():
    return render_template("main.html")


@app.route("/db", methods=['GET', 'POST'])
def query():
    with app.app_context():
            print(query_db_all(query='select * from chat'))
            return query_db(query='select * from chat')

@app.route("/db_add", methods=['GET', 'POST'])
def add_query():
    c = request.form.get('content')
    k = request.form.get('key')
    qry = 'INSERT INTO chat(myid,content) VALUES(\"'+ k +'\", \"'+ c +'\")'
    with app.app_context():
            print(f'query: {qry}')
            query_db(query=qry)
            print(query_db_all(query='select * from chat'))
            return query_db(query='select * from chat')
            
# Handle Lambda events
def lambda_handler(event, context):
    
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    logger.info(event)
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    
    # Extract the HTTP method and path from the Lambda event
    http_method = event['httpMethod']

    path = event['path']    

    # Route the request to the appropriate Flask endpoint
    with app.test_request_context(path, method=http_method, json=event):
        print(request)
        logger.info(request)
        
        response = app.full_dispatch_request()

    # Return the Flask response as a JSON object
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.json
    }

    
if __name__ == '__main__':
    app.run(debug=True)

