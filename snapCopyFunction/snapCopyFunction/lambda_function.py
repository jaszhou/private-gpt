"""
  This is the entry of Lambda function, it'll setup the routes and capture the request from API Gateway
  
"""
import logging
import os
import boto3
import hashlib
import secrets
import mimetypes
from flask import Flask, request, render_template, redirect, url_for, g, make_response, session
from flask_restful import Resource, Api, reqparse
import urllib3
from snapCopyFunction.utils import *
from snapCopyFunction.db import *
import awsgi
from flask import jsonify
from snapCopyFunction.bedrock import *

# Configuration from environment variables
AWS_REGION = os.environ.get('AWS_REGION', 'ap-southeast-2')
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')

# File upload settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


urllib3.disable_warnings()
        
app = Flask(__name__,
            # static_url_path='/static', 
            static_folder='web/static',
            template_folder='web/templates')
app.secret_key = FLASK_SECRET_KEY
# Ensure session cookie works across refreshes
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# SESSION_COOKIE_PATH will be set dynamically in before_request
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
# Limit upload size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def get_stage_from_request():
    """Extract API Gateway stage from request path."""
    # Default to 'dev' for local development
    if not request:
        return 'dev'
    # First, try to get stage from API Gateway event via request.environ
    event = request.environ.get('awsgi.event', {})
    stage = event.get('requestContext', {}).get('stage')
    if stage in ['dev', 'prod', 'test', 'staging']:
        return stage
    # Fallback to path extraction
    path = request.path
    parts = path.strip('/').split('/')
    if len(parts) > 0 and parts[0] in ['dev', 'prod', 'test', 'staging']:
        return parts[0]
    # Try to get stage from API Gateway stage variable via request.environ
    stage = request.environ.get('API_GATEWAY_STAGE')
    if stage in ['dev', 'prod', 'test', 'staging']:
        return stage
    # Try X-Stage header (custom header)
    stage = request.headers.get('X-Stage')
    if stage in ['dev', 'prod', 'test', 'staging']:
        return stage
    # Fallback to environment variable or default
    return os.environ.get('API_STAGE', 'dev')

@app.before_request
def before_request():
    """Set dynamic SESSION_COOKIE_PATH based on stage."""
    stage = get_stage_from_request()
    app.config['SESSION_COOKIE_PATH'] = f'/{stage}'

api = Api(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = reqparse.RequestParser()

init_db()


@app.route("/<stage>/chat", methods=['POST'])
def chatbot(stage):
    
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

@app.route("/<stage>/db_get/<key_id>", methods=['GET', 'POST'])
def get_all_rows(stage, key_id):
    with app.app_context():
        cur = get_db().cursor()
        result = query_db_all(query='select * from chat where myid = "'+ key_id +'"')
        logger.info(f"Query result: {result}")
    
    all_items = []
    # 2. Read from DynamoDB - include ALL items matching the key
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        messages_table = dynamodb.Table('messages')
        
        response = messages_table.scan(
            FilterExpression="#k = :key_val",
            ExpressionAttributeNames={
                "#k": "key"
            },
            ExpressionAttributeValues={
                ":key_val": key_id
            }
        )
        
        logger.info(f"DynamoDB scan response type: {type(response)}")
        logger.info(f"DynamoDB Items count: {response.get('Count', 0)}")
        
        items = response.get('Items', [])
        logger.info(f"Items type: {type(items)}")
        
        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dictionary item: {item}")
                continue
                
            # Include ALL items regardless of user_email
            all_items.append({
                'id': item.get('id'),
                'key_id': item.get('key'),
                'content': item.get('content'),
                'filename': item.get('filename', ''),  # Include filename (may be empty for non-file messages)
                'timestamp': item.get('timestamp')
            })

        logger.info(all_items)    

        # 4. Format for response
        from datetime import datetime
        formatted_items = []
        for item in all_items:
            timestamp = item.get('timestamp')
            if timestamp:
                try:
                    ts = float(timestamp)
                    dt_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                except (TypeError, ValueError):
                    dt_str = ''
            else:
                dt_str = ''
            formatted_items.append([item['id'], item['key_id'], item['content'], dt_str])
        
        logger.info(formatted_items)
        logger.info(f'formatted_items: {jsonify(formatted_items)}')
        
        # return jsonify(formatted_items)
        return result

    except Exception as e:
        logger.error(f"Error reading from DynamoDB messages table: {e}")
        return result

# create a python function to generate qr code







@app.route("/pages", methods=['GET', 'POST'])
def main_page():
    stage = get_stage_from_request()
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    response = make_response(render_template("main.html", user_email=user_email, user_name=user_name, stage=stage))
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route("/", methods=['GET', 'POST'])
def main():
    stage = get_stage_from_request()
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    response = make_response(render_template("main.html", user_email=user_email, user_name=user_name, stage=stage))
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route("/generate")
def gen_code():
    stage = get_stage_from_request()
    uid, qrcode = generate_qr_code()
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    response = make_response(render_template("main.html", uid=uid, qrcode = qrcode, user_email=user_email, user_name=user_name, stage=stage))
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route("/pages/<key_id>", methods=['GET', 'POST'])
def pages(key_id):
    stage = get_stage_from_request()
    with app.app_context():
        cur = get_db().cursor()
    
    uid, qrcode = generate_qr_code(uid = key_id)
    user_email = session.get('user_email')
    user_name = session.get('user_name')
    response = make_response(render_template("main.html", uid=uid, qrcode = qrcode, user_email=user_email, user_name=user_name, stage=stage))
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route("/login", methods=['GET', 'POST'])
def login():
    stage = get_stage_from_request()
    if request.method == 'POST':
        # For now, mock authentication
        email = request.form.get('email')
        password = request.form.get('password')
        # TODO: integrate with Cognito
        session['user_email'] = email
        session['user_name'] = email.split('@')[0]
        return redirect(f'/{stage}/pages')
    response = make_response(render_template("login.html", stage=stage))
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route("/register", methods=['GET', 'POST'])
def register():
    stage = get_stage_from_request()
    if request.method == 'POST':
        # For now, mock registration
        email = request.form.get('email')
        password = request.form.get('password')
        # TODO: integrate with Cognito
        session['user_email'] = email
        session['user_name'] = email.split('@')[0]
        return redirect(f'/{stage}/pages')
    response = make_response(render_template("register.html", stage=stage))
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route("/logout", methods=['GET'])
def logout():
    stage = get_stage_from_request()
    session.clear()
    return redirect(f'/{stage}/pages')

@app.route("/db_add", methods=['GET', 'POST'])
def add_query():
    stage = get_stage_from_request()
    c = request.form.get('content')
    k = request.form.get('key')
    
    # Always save to DynamoDB for persistence, regardless of login status
    try:
        import time
        import uuid
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        messages_table = dynamodb.Table('messages')
        message_id = str(uuid.uuid4())
        timestamp = int(time.time())
        # For logged-in users, store user_email and user_id; for non-logged-in, store None
        user_email = session.get('user_email')
        user_id = session.get('user_id')
        item = {
            'id': message_id,
            'user_email': user_email,
            'user_id': user_id,
            'content': c,
            'key': k,
            'timestamp': timestamp
        }
        messages_table.put_item(Item=item)
        logger.info(f"Message saved to DynamoDB: {message_id}")
        # Also save to SQLite for backward compatibility (optional)
        if not user_email:
            qry = 'INSERT INTO chat(myid,content,LastModifiedTime) VALUES("'+ k +'", "'+ c +'",CURRENT_TIMESTAMP)'
            print(f'query: {qry}')
            conn = get_db()
            cur = conn.cursor()
            cur.execute(qry)
            conn.commit()
            cur.close()
        # Return success response
        return jsonify({"status": "success", "message": "Message saved to DynamoDB", "message_id": message_id})
    except Exception as e:
        logger.error(f"Error saving to DynamoDB messages table: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/db_upload", methods=['POST'])
def upload_file():
    """Handle file upload to S3, store with key_id as folder, original filename."""
    stage = get_stage_from_request()
    try:
        file = request.files.get('file')
        description = request.form.get('description', '')
        key_id = request.form.get('key')
        
        if not file:
            return jsonify({"status": "error", "message": "No file provided"}), 400
        if not key_id:
            return jsonify({"status": "error", "message": "No key ID provided"}), 400
        
        # Log file info from request
        logger.debug(f"Uploaded file content-type from request: {file.content_type}")
        logger.debug(f"Uploaded file filename: {file.filename}")
        
        # Use default bucket and parent folder
        s3_bucket = 'zappa-m3secjk20'
        parent_folder = 'uploads'
        
        # Sanitize filename
        import os
        filename = file.filename
        filename = os.path.basename(filename)
        import re
        filename = re.sub(r'[^\w\-.]', '_', filename)
        
        # S3 key: uploads/key_id/filename
        s3_key = f"{parent_folder}/{key_id}/{filename}"
        
        # Ensure file pointer at start
        file.seek(0)
        
        # Debug: log first few bytes for PDF verification
        first_bytes = file.read(4)
        file.seek(0)  # reset
        logger.debug(f"First 4 bytes of uploaded file: {first_bytes.hex() if first_bytes else 'empty'}")
        if filename.lower().endswith('.pdf') and first_bytes != b'%PDF':
            logger.warning(f"Uploaded PDF file does not start with PDF magic number; may be corrupted.")
        
        # Compute file size and MD5 hash for integrity verification
        md5_hash = hashlib.md5()
        file_size = 0
        while True:
            chunk = file.read(8192)  # 8KB chunks
            if not chunk:
                break
            md5_hash.update(chunk)
            file_size += len(chunk)
        file_hash = md5_hash.hexdigest()
        
        # Check file size limit
        if file_size > MAX_FILE_SIZE:
            return jsonify({"status": "error", "message": f"File size exceeds limit of {MAX_FILE_SIZE // (1024*1024)} MB"}), 400
        
        # Warn about empty file
        if file_size == 0:
            logger.warning(f"Empty file uploaded: {filename}")
        
        # Seek back to start for upload
        file.seek(0)
        
        # Determine content type
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # Upload to S3 with content type
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        s3_client.upload_fileobj(
            file,
            s3_bucket,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'ContentDisposition': f'attachment; filename="{filename}"'
            }
        )
        
        # Verify upload by checking S3 object metadata
        try:
            head = s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
            logger.info(f"S3 object metadata: ETag={head.get('ETag')}, ContentLength={head.get('ContentLength')}, ContentType={head.get('ContentType')}")
            if head.get('ContentLength') != file_size:
                logger.error(f"Uploaded file size mismatch: local {file_size} vs S3 {head.get('ContentLength')}")
        except Exception as e:
            logger.warning(f"Failed to verify S3 object: {e}")
        
        # Generate presigned URL for secure, time-limited access
        download_url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': s3_bucket, 'Key': s3_key},
            ExpiresIn=3600 * 24 * 30  # 1 hour expiration
        )
        
        # Save download link as content in DynamoDB messages table
        import time
        import uuid
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        messages_table = dynamodb.Table('messages')
        message_id = str(uuid.uuid4())
        timestamp = int(time.time())
        user_email = session.get('user_email')
        user_id = session.get('user_id')
        item = {
            'id': message_id,
            'user_email': user_email,
            'user_id': user_id,
            'content': download_url,  # Store just the download URL
            'description': description,  # Store the file description
            'filename': filename,      # Store the original filename
            'key': key_id,
            'timestamp': timestamp
        }
        messages_table.put_item(Item=item)
        
        logger.info(f"File uploaded to S3: {s3_key}, size: {file_size} bytes, hash: {file_hash}, content-type: {content_type}")
        return jsonify({
            "status": "success",
            "message": "File uploaded successfully",
            "filename": filename,
            "download_url": download_url,
            "size": file_size,
            "hash": file_hash
        })
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/db_delete/<message_id>", methods=['DELETE', 'POST'])
def delete_message(message_id):
    """Delete a message from DynamoDB messages table by message_id"""
    stage = get_stage_from_request()
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        messages_table = dynamodb.Table('messages')
        
        # First, get the item to ensure it exists and belongs to the current user (optional)
        response = messages_table.get_item(Key={'id': message_id})
        if 'Item' not in response:
            return jsonify({"status": "error", "message": "Message not found"}), 404
        
        # Optional: Check if the current user is the owner (if logged in)
        # user_email = session.get('user_email')
        # if user_email and response['Item'].get('user_email') != user_email:
        #     return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
        # Delete the item
        messages_table.delete_item(Key={'id': message_id})
        logger.info(f"Message deleted from DynamoDB: {message_id}")
        
        return jsonify({"status": "success", "message": "Message deleted"})
    except Exception as e:
        logger.error(f"Error deleting from DynamoDB messages table: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/db_messages/<key_id>", methods=['GET'])
def db_messages(key_id):
    """Return DynamoDB messages for a given key_id in JSON format expected by frontend."""
    stage = get_stage_from_request()
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        messages_table = dynamodb.Table('messages')
        
        # If key_id is 'all' or empty, return all messages without filtering
        if key_id == 'all' or not key_id or key_id == 'undefined':
            response = messages_table.scan()
        else:
            response = messages_table.scan(
                FilterExpression="#k = :key_val",
                ExpressionAttributeNames={
                    "#k": "key"
                },
                ExpressionAttributeValues={
                    ":key_val": key_id
                }
            )
        
        items = response.get('Items', [])
        # Sort items by timestamp descending
        items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        # Format items as expected
        formatted_items = []
        for item in items:
            timestamp = item.get('timestamp')
            if timestamp:
                try:
                    ts = float(timestamp)
                    from datetime import datetime
                    dt_str = datetime.fromtimestamp(ts).isoformat() + 'Z'
                except (TypeError, ValueError):
                    dt_str = ''
            else:
                dt_str = ''
            formatted_items.append({
                'id': item.get('id'),
                'content': item.get('content'),
                'description': item.get('description', ''),  # Include description
                'filename': item.get('filename', ''),      # Include filename
                'timestamp': dt_str
            })
        
        return jsonify({
            'total_count': len(items),
            'table_name': 'messages',
            'region': AWS_REGION,
            'items': formatted_items
        })
    except Exception as e:
        logger.error(f"Error reading from DynamoDB messages table: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
            
# Handle Lambda events


def lambda_handler(event, context):
    
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    logger.info(event)
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++")
       
    return awsgi.response(app, event, context)


    
if __name__ == '__main__':
    app.run(debug=True)