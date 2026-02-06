import boto3
import sys
import json
import os
import time

stage = sys.argv[1]

lambda_client = boto3.client("lambda")
apigateway_client = boto3.client("apigateway")

FUNCTION_NAME = "snapCopyFunction"
ALIAS_NAME = stage
API_ID = "f8do9lswp5"  # From API Gateway URL


# ---------------------------
# 1 Publish new version and setup alias
# ---------------------------
print(f"Setting up alias '{ALIAS_NAME}' for Lambda function {FUNCTION_NAME}...")

# First, publish a new version of the function
print("Publishing new function version...")
try:
    version_response = lambda_client.publish_version(FunctionName=FUNCTION_NAME)
    new_version = version_response["Version"]
    print(f"New version published: {new_version}")
except Exception as e:
    print(f"Error publishing new version: {e}")
    print("Trying to get latest version instead...")
    
    # Fallback: get the latest published version
    versions = lambda_client.list_versions_by_function(FunctionName=FUNCTION_NAME)
    if not versions['Versions']:
        print(f"Error: No versions found for function {FUNCTION_NAME}")
        sys.exit(1)
    
    # Find the latest version (excluding $LATEST)
    latest_version = None
    for version in versions['Versions']:
        if version['Version'] != '$LATEST':
            if latest_version is None or int(version['Version']) > int(latest_version['Version']):
                latest_version = version
    
    if latest_version is None:
        print(f"Error: Could not find a published version for function {FUNCTION_NAME}")
        sys.exit(1)
    
    new_version = latest_version['Version']
    print(f"Using latest published version: {new_version}")

# Note: Environment variables and function configuration are handled by deploy_lambda.sh
# This script only manages aliases

# ---------------------------
# 2 Create or update alias
# ---------------------------
try:
    lambda_client.get_alias(
        FunctionName=FUNCTION_NAME,
        Name=ALIAS_NAME
    )

    print("Updating alias...")
    lambda_client.update_alias(
        FunctionName=FUNCTION_NAME,
        Name=ALIAS_NAME,
        FunctionVersion=new_version
    )

except lambda_client.exceptions.ResourceNotFoundException:
    print("Creating alias...")
    lambda_client.create_alias(
        FunctionName=FUNCTION_NAME,
        Name=ALIAS_NAME,
        FunctionVersion=new_version
    )

print(f"Deployment complete! Alias '{ALIAS_NAME}' now points to version {new_version}.")

# Optional: Update API Gateway if needed
# Uncomment the following lines if you want to automatically update API Gateway
# print("Updating API Gateway integration...")
# try:
#     # Get the root resource ID (path '/')
#     resources = apigateway_client.get_resources(restApiId=API_ID)
#     root_resource_id = None
#     for resource in resources['items']:
#         if resource['path'] == '/':
#             root_resource_id = resource['id']
#             break
    
#     if root_resource_id is None:
#         # Fallback to the first resource
#         if resources['items']:
#             root_resource_id = resources['items'][0]['id']
#         else:
#             raise Exception("No resources found in API Gateway")
    
#     print(f"Using resource ID: {root_resource_id}")
    
#     # Update the API Gateway to use the new alias
#     apigateway_client.update_integration(
#         restApiId=API_ID,
#         resourceId=root_resource_id,
#         httpMethod='ANY',
#         patchOperations=[
#             {
#                 'op': 'replace',
#                 'path': '/uri',
#                 'value': f'arn:aws:apigateway:ap-southeast-2:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-southeast-2:647207328002:function:{FUNCTION_NAME}:{ALIAS_NAME}/invocations'
#             }
#         ]
#     )
#     print("API Gateway updated to use new alias.")
# except Exception as e:
#     print(f"Note: API Gateway update skipped or failed: {e}")
#     print("You can update API Gateway manually using update_api_gateway.sh")