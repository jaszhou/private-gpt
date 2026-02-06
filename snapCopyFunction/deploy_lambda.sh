#!/bin/bash

# Package the Lambda function with minimal footprint
cd /mnt/e/github/SnapCopy/snapCopyFunction
mkdir -p deployment_package

# Copy only essential Python files, exclude __pycache__, .git, etc.
find snapCopyFunction -type f -name "*.*" \
     ! -path "*/__pycache__/*" \
     ! -path "*/.git/*" \
     ! -path "*/tests/*" \
     -exec cp --parents {} deployment_package/ \;

# Copy templates and static files if needed
cp -r snapCopyFunction/web/templates deployment_package/snapCopyFunction/web/ 2>/dev/null || true
cp -r snapCopyFunction/web/static deployment_package/snapCopyFunction/web/ 2>/dev/null || true

# Install only required dependencies (excluding boto3 and Pillow) with size optimization
pip install --no-compile --no-deps -r requirements.txt -t deployment_package/

# Remove unnecessary files to reduce size
find deployment_package -type f -name "*.pyc" -delete
find deployment_package -type f -name "*.so" -exec strip {} \; 2>/dev/null || true
find deployment_package -type d -name "*.dist-info" -exec rm -rf {} \; 2>/dev/null || true
find deployment_package -type d -name "*.egg-info" -exec rm -rf {} \; 2>/dev/null || true
find deployment_package -type d -name "__pycache__" -exec rm -rf {} \; 2>/dev/null || true
find deployment_package -type f -name "*.py[co]" -delete

# Remove tests and documentation from installed packages
find deployment_package -type d -name "tests" -exec rm -rf {} \; 2>/dev/null || true
find deployment_package -type d -name "docs" -exec rm -rf {} \; 2>/dev/null || true
find deployment_package -type f -name "*.txt" -exec rm -f {} \; 2>/dev/null || true
find deployment_package -type f -name "*.md" -exec rm -f {} \; 2>/dev/null || true

# Create compressed zip
cd deployment_package
zip -r9q ../function.zip .
cd ..

# Check package size
PACKAGE_SIZE=$(du -sh function.zip | cut -f1)
PACKAGE_BYTES=$(du -b function.zip | cut -f1)
echo "Package size: $PACKAGE_SIZE"

# Read layer ARN from file (if exists) or set manually
LAYER_ARN_FILE="layer_arn.txt"
if [ -f "$LAYER_ARN_FILE" ]; then
    LAYER_ARN=$(cat "$LAYER_ARN_FILE")
else
    echo "Warning: layer_arn.txt not found. Set LAYER_ARN manually or run deploy_layer.sh first."
    echo "Example: LAYER_ARN='arn:aws:lambda:region:account:layer:snapCopyDeps:1'"
    exit 1
fi

# Pillow layer ARN - adjust based on Python version
# For Python 3.9: arn:aws:lambda:ap-southeast-2:770693421928:layer:Klayers-p39-pillow:1
# For Python 3.10: Check if Klayers-p310-pillow exists
# For Python 3.12: May need to create custom layer or use alternative
# PILLOW_LAYER_ARN="arn:aws:lambda:ap-southeast-2:770693421928:layer:Klayers-p39-pillow:1"

# Uncomment and set the correct Pillow layer ARN for your Python version
# PILLOW_LAYER_ARN="arn:aws:lambda:ap-southeast-2:770693421928:layer:Klayers-p310-pillow:1"  # Python 3.10
PILLOW_LAYER_ARN=""  # No Pillow layer if creating custom layer with Pillow included

# # Attach S3 policy to Lambda role
# ROLE_NAME="snapCopyFunction-role-nkkiffxa"
# POLICY_NAME="snapCopyFunction-s3-upload-policy"
# POLICY_FILE="s3-policy.json"

# # Create policy if not exists
# echo "Creating/updating IAM policy $POLICY_NAME..."
# aws iam create-policy --policy-name "$POLICY_NAME" --policy-document file://"$POLICY_FILE" 2>/dev/null || \
# aws iam create-policy-version --policy-arn "arn:aws:iam::647207328002:policy/$POLICY_NAME" --policy-document file://"$POLICY_FILE" --set-as-default 2>/dev/null || \
# echo "Policy $POLICY_NAME already exists, updating if needed."

# # Attach policy to role
# echo "Attaching policy $POLICY_NAME to role $ROLE_NAME..."
# aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "arn:aws:iam::647207328002:policy/$POLICY_NAME"


# Update Lambda function with layer
if [ $PACKAGE_BYTES -lt 50000000 ]; then
    if [ -n "$PILLOW_LAYER_ARN" ]; then
        aws lambda update-function-configuration \
            --function-name snapCopyFunction \
            --layers "$LAYER_ARN" "$PILLOW_LAYER_ARN"
    else
        aws lambda update-function-configuration \
            --function-name snapCopyFunction \
            --layers "$LAYER_ARN"
    fi
    aws lambda update-function-code \
        --function-name snapCopyFunction \
        --zip-file fileb://function.zip
    if [ -n "$PILLOW_LAYER_ARN" ]; then
        echo "Deployment complete with layers: $LAYER_ARN and $PILLOW_LAYER_ARN"
    else
        echo "Deployment complete with layer: $LAYER_ARN"
    fi
else
    echo "Error: Package size $PACKAGE_SIZE exceeds 50MB limit"
    echo "Consider further optimization or using AWS Lambda container images"
fi

# Clean up
rm -rf deployment_package function.zip