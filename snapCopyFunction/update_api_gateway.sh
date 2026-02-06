#!/bin/bash

# Script to push updated OpenAPI spec to API Gateway
# Usage: ./update_api_gateway.sh [api-id] [--region region] [--deploy]
# If api-id is not provided, it will be extracted from the JSON file
# Use --deploy flag to automatically create a deployment to the 'dev' stage
# Region defaults to ap-southeast-2 (extracted from JSON)

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
API_DIR="${SCRIPT_DIR}/API"

# Find the OpenAPI JSON file (should be only one)
JSON_FILE=$(find "${API_DIR}" -name "*oas30*.json" -type f | head -1)
if [ -z "${JSON_FILE}" ]; then
    echo "Error: No OpenAPI JSON file found in ${API_DIR}"
    exit 1
fi

echo "Using OpenAPI spec: $(basename ${JSON_FILE})"

# Parse arguments
API_ID=""
DO_DEPLOY=false
REGION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --deploy)
            DO_DEPLOY=true
            shift
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [api-id] [--region region] [--deploy]"
            echo "  api-id    - API Gateway ID (optional, will be extracted from JSON if not provided)"
            echo "  --region  - AWS region (optional, defaults to ap-southeast-2)"
            echo "  --deploy  - Create deployment to 'dev' stage after update"
            exit 0
            ;;
        -*)
            echo "Error: Unknown option $1"
            echo "Usage: $0 [api-id] [--region region] [--deploy]"
            exit 1
            ;;
        *)
            if [ -z "${API_ID}" ]; then
                API_ID="$1"
                echo "Using provided API Gateway ID: ${API_ID}"
            else
                echo "Error: Extra argument $1"
                echo "Usage: $0 [api-id] [--region region] [--deploy]"
                exit 1
            fi
            shift
            ;;
    esac
done

# Determine API Gateway ID if not provided
if [ -z "${API_ID}" ]; then
    # Extract API ID from servers URL in JSON file
    API_ID=$(grep -o '"url" : "https://[^.]*\.' "${JSON_FILE}" | head -1 | cut -d'/' -f3 | cut -d'.' -f1)
    if [ -z "${API_ID}" ]; then
        echo "Error: Could not extract API Gateway ID from JSON file"
        echo "Please provide the API Gateway ID as an argument"
        echo "Usage: $0 [api-id] [--deploy]"
        exit 1
    fi
    echo "Extracted API Gateway ID: ${API_ID}"
fi

# Strip any account prefix (e.g., '647207328002:9olim6ft8c' -> '9olim6ft8c')
if [[ "${API_ID}" =~ ^[0-9]+: ]]; then
    echo "Warning: Stripping account prefix from API ID: ${API_ID}"
    API_ID="${API_ID#*:}"
    echo "Using API ID: ${API_ID}"
fi

# Validate API ID format (alphanumeric, no colons)
if ! [[ "${API_ID}" =~ ^[a-zA-Z0-9]+$ ]]; then
    echo "Error: Invalid API Gateway ID format: ${API_ID}"
    echo "API ID must be alphanumeric only (no colons or special characters)"
    exit 1
fi

# Determine stage name (default 'dev')
STAGE_NAME="dev"
# Could extract from JSON variables if needed

# Determine region (default to ap-southeast-2 from JSON)
if [ -z "${REGION}" ]; then
    # Extract region from servers URL in JSON file
    REGION=$(grep -o '"url" : "https://[^.]*\.execute-api\.\([a-z0-9-]*\)\.' "${JSON_FILE}" | head -1 | cut -d'.' -f3)
    if [ -z "${REGION}" ]; then
        REGION="ap-southeast-2"
    fi
fi

# Check AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed or not in PATH"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured or invalid"
    exit 1
fi

echo "Updating API Gateway ${API_ID} in region ${REGION} with OpenAPI spec from ${JSON_FILE}"

# Validate API exists
echo "Validating API Gateway ID..."
if ! aws apigateway get-rest-api --rest-api-id "${API_ID}" --region "${REGION}" &> /dev/null; then
    echo "Error: API Gateway '${API_ID}' not found in region '${REGION}'"
    echo "Please verify the API ID and region"
    echo "You can list all APIs with: aws apigateway get-rest-apis --region ${REGION}"
    exit 1
fi

# Import the OpenAPI spec
aws apigateway put-rest-api \
    --rest-api-id "${API_ID}" \
    --mode overwrite \
    --body "file://${JSON_FILE}" \
    --region "${REGION}"

if [ $? -ne 0 ]; then
    echo "Error: Failed to update API Gateway"
    echo "Check that API ID '${API_ID}' exists in region '${REGION}'"
    echo "You can find the API ID in the AWS Console or via 'aws apigateway get-rest-apis'"
    exit 1
fi

echo "Successfully updated API Gateway ${API_ID} in region ${REGION}"

# Deploy if requested
if [ "${DO_DEPLOY}" = true ]; then
    echo "Creating deployment to stage '${STAGE_NAME}'..."
    aws apigateway create-deployment \
        --rest-api-id "${API_ID}" \
        --stage-name "${STAGE_NAME}" \
        --region "${REGION}"
    
    if [ $? -eq 0 ]; then
        echo "Deployment created successfully"
        echo "Changes are now live at: https://${API_ID}.execute-api.ap-southeast-2.amazonaws.com/${STAGE_NAME}/"
    else
        echo "Warning: Failed to create deployment. You may need to deploy manually."
    fi
else
    echo "Note: Changes are not yet deployed to a stage."
    echo "To deploy, run: aws apigateway create-deployment --rest-api-id ${API_ID} --stage-name ${STAGE_NAME} --region ${REGION}"
fi