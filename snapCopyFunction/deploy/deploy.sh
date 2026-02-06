#!/bin/bash

STAGE=$1

source /mnt/e/github/SnapCopy/snapCopyFunction/venv/bin/activate

if [ -z "$STAGE" ]; then
  echo "Usage: ./deploy.sh dev|prod"
  exit 1
fi

echo "Deploying to $STAGE stage..."

# package lambda function with all dependencies
cd ..
echo "Running deploy_lambda.sh to package and update Lambda function..."
if ! ./deploy_lambda.sh; then
    echo "Error: deploy_lambda.sh failed"
    exit 1
fi
cd deploy

echo "Setting up alias and version management..."
if ! python deploy.py $STAGE; then
    echo "Error: deploy.py failed"
    exit 1
fi

echo "Deployment to $STAGE completed successfully!"