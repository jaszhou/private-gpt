#!/bin/bash

# Activate virtual environment
#source venv/bin/activate

# Install requirements if needed
# pip install -r snapCopyFunction/requirements.txt

# Set environment variables for local debugging
# export AWS_ACCESS_KEY_ID="your_access_key"
# export AWS_SECRET_ACCESS_KEY="your_secret_key"
# export AWS_DEFAULT_REGION="us-east-1"

# Run the Lambda function locally with debug mode
# python -m ptvsd --host 0.0.0.0 --port 5678 --wait -m awslambdaric snapCopyFunction.lambda_function.lambda_handler

#snapCopyFunction/lambda_function.py

# Alternatively, for simple testing without debugger:
python -c "
import json
with open('event.json', 'r') as f:
    # Convert Python dict-like string to valid JSON
    import ast
    content = f.read()
    # Replace single quotes with double quotes and None with null
    # content = content.replace("'", '"')
    # content = content.replace('None', 'null')
    event = json.loads(content)
from snapCopyFunction.lambda_function import lambda_handler
print(lambda_handler(event, {}))
"