#!/bin/bash

# Deploy Lambda layer for boto3 and Pillow
cd /mnt/e/github/SnapCopy/snapCopyFunction

# Create temporary directory for layer
mkdir -p layer_package/python

# Install dependencies into layer directory (using Python 3.12)
pip3.12 install --no-compile --no-deps -r requirements-layer.txt -t layer_package/python/

# Remove unnecessary files to reduce size
find layer_package -type f -name "*.pyc" -delete
find layer_package -type d -name "*.dist-info" -exec rm -rf {} \; 2>/dev/null || true
find layer_package -type d -name "*.egg-info" -exec rm -rf {} \; 2>/dev/null || true
find layer_package -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null || true
find layer_package -type f -name "*.py[co]" -delete
find layer_package -type d -name "tests" -exec rm -rf {} \; 2>/dev/null || true
find layer_package -type f -name "*.txt" -exec rm -f {} \; 2>/dev/null || true
find layer_package -type f -name "*.md" -exec rm -f {} \; 2>/dev/null || true

# Create layer zip
cd layer_package
zip -r9q ../layer.zip .
cd ..

# Publish Lambda layer
LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name snapCopyDeps \
    --description "boto3 and Pillow for SnapCopy (Python 3.12)" \
    --zip-file fileb://layer.zip \
    --query 'LayerVersionArn' \
    --output text)

echo "Layer ARN: $LAYER_ARN"

# Save layer ARN to file for reference
echo "$LAYER_ARN" > layer_arn.txt

# Clean up
rm -rf layer_package layer.zip

echo "Layer deployment complete. Update your Lambda function to use layer: $LAYER_ARN"