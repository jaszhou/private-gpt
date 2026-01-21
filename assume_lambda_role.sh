#!/bin/bash

# Script to assume the NewsLambdaRole and set temporary credentials

ROLE_ARN="arn:aws:iam::647207328002:role/NewsLambdaRole"
SESSION_NAME="lambda-assume-session"

# Assume the role
CREDENTIALS=$(aws sts assume-role \
    --role-arn "$ROLE_ARN" \
    --role-session-name "$SESSION_NAME" \
    --query 'Credentials' \
    --output json)

# Check if assume-role was successful
if [ $? -ne 0 ]; then
    echo "Failed to assume role $ROLE_ARN"
    exit 1
fi

# Extract credentials
ACCESS_KEY_ID=$(echo "$CREDENTIALS" | jq -r '.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$CREDENTIALS" | jq -r '.SecretAccessKey')
SESSION_TOKEN=$(echo "$CREDENTIALS" | jq -r '.SessionToken')

# Export credentials as environment variables
export AWS_ACCESS_KEY_ID="$ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$SECRET_ACCESS_KEY"
export AWS_SESSION_TOKEN="$SESSION_TOKEN"

echo "Successfully assumed role $ROLE_ARN"
echo "Temporary credentials set as environment variables"

# Optional: Verify the assumed role identity
aws sts get-caller-identity