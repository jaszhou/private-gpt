import json
import sys
sys.path.insert(0, '.')

from snapCopyFunction.lambda_function import lambda_handler

event = {
    'resource': '/',
    'path': '/',
    'httpMethod': 'GET',
    'headers': {},
    'multiValueHeaders': {},
    'queryStringParameters': None,
    'multiValueQueryStringParameters': None,
    'pathParameters': None,
    'stageVariables': None,
    'requestContext': {
        'resourcePath': '/',
        'httpMethod': 'GET',
        'path': '/dev',
        'stage': 'dev',
        'requestId': 'test',
        'apiId': 'test'
    },
    'body': None,
    'isBase64Encoded': False
}

try:
    result = lambda_handler(event, {})
    print('Result:', result)
    print('Status:', result.get('statusCode'))
    print('Headers:', result.get('headers'))
    if result.get('body'):
        print('Body preview:', result.get('body')[:200])
    else:
        print('No body')
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()