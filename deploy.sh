#!/bin/bash

# AWS Lambda Deployment Script for News Function
# Usage: ./deploy.sh [function-name] [aws-region] [account-id]

set -e

# Configuration
FUNCTION_NAME=${1:-"news-scraper-function"}
AWS_REGION=${2:-"us-east-1"}
ACCOUNT_ID=${3:-""}
ROLE_NAME="NewsLambdaRole"
DEPLOY_DIR="lambda-deploy"

echo "Deploying Lambda function: $FUNCTION_NAME"
echo "AWS Region: $AWS_REGION"

# Clean and create deployment directory
if [ -d "$DEPLOY_DIR" ]; then
    echo "Cleaning existing deployment directory..."
    rm -rf "$DEPLOY_DIR"
fi

mkdir "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

echo "Copying Lambda function code..."
cp ../news_lambda_function.py lambda_function.py

echo "Installing Python dependencies..."
pip3 install requests beautifulsoup4 boto3 urllib3 readability-lxml --target .

echo "Creating deployment package..."
zip -r ../news-lambda-function.zip . -x "*.pyc" "*/__pycache__/*"

cd ..

# Check if AWS CLI is configured
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI not found. Please install and configure AWS CLI."
    exit 1
fi

# Get account ID if not provided
if [ -z "$ACCOUNT_ID" ]; then
    echo "Getting AWS account ID..."
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "Account ID: $ACCOUNT_ID"
fi

ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

# Check if role exists, create if not
echo "Checking IAM role..."
if ! aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo "Creating IAM role: $ROLE_NAME"

    cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document file://trust-policy.json

    echo "Attaching policies to role..."
    aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn arn:aws:iam::aws:policy/AmazonPollyFullAccess



  aws iam attach-role-policy \
      --role-name "NewsLambdaRole" \
      --policy-arn "arn:aws:iam::647207328002:policy/BedrockAccessPolicy"

    rm trust-policy.json

    echo "Waiting for role to be ready..."
    sleep 10
else
    echo "IAM role already exists: $ROLE_NAME"
fi

# Check if function exists
echo "Checking if Lambda function exists..."
if aws lambda get-function --function-name "$FUNCTION_NAME" &> /dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file fileb://news-lambda-function.zip

else
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.12 \
        --role "$ROLE_ARN" \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://news-lambda-function.zip \
        --timeout 300 \
        --memory-size 512 \
        --environment Variables="{\"AWS_REGION\":\"$AWS_REGION\",\"VOICE_ID\":\"Zhiyu\"}" \
        --region "$AWS_REGION"
fi

echo "Deployment completed successfully!"
echo "Function ARN: arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"

# Clean up
rm -rf "$DEPLOY_DIR"
rm news-lambda-function.zip

echo ""
echo "To test the function, run:"
echo "aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' response.json"
echo ""
echo "To add Telegram credentials, update environment variables:"
echo "aws lambda update-function-configuration --function-name $FUNCTION_NAME --environment Variables='{\"AWS_REGION\":\"$AWS_REGION\",\"VOICE_ID\":\"Zhiyu\",\"TELEGRAM_TOKEN\":\"your_token\",\"CHAT_ID\":\"your_chat_id\"}'"