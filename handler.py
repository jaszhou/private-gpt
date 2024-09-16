"""
  This is the entry of Lambda function, it'll setup the routes and capture the request from API Gateway
  Author: jason.zhou@cba.com.au
  
"""
import logging
from flask import Flask, request

from flask_restful import Resource, Api, reqparse

import urllib3

urllib3.disable_warnings()

app = Flask(__name__)
api = Api(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = reqparse.RequestParser()

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
    
# Add the resources to the API
api.add_resource(ScimUser, '/scim/v2/ScimUser')

def handler(event, context):
    import awsgi
    return awsgi.response(app, event, context)

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

