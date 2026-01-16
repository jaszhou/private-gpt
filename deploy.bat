@echo off
REM AWS Lambda Deployment Script for News Function (Windows)
REM Usage: deploy.bat [function-name] [aws-region] [account-id]

setlocal enabledelayedexpansion

REM Configuration
set FUNCTION_NAME=%1
if "%FUNCTION_NAME%"=="" set FUNCTION_NAME=news-scraper-function

set AWS_REGION=%2
if "%AWS_REGION%"=="" set AWS_REGION=us-east-1

set ACCOUNT_ID=%3
set ROLE_NAME=NewsLambdaRole
set DEPLOY_DIR=lambda-deploy

echo Deploying Lambda function: %FUNCTION_NAME%
echo AWS Region: %AWS_REGION%

REM Clean and create deployment directory
if exist "%DEPLOY_DIR%" (
    echo Cleaning existing deployment directory...
    rmdir /s /q "%DEPLOY_DIR%"
)

mkdir "%DEPLOY_DIR%"
cd "%DEPLOY_DIR%"

echo Copying Lambda function code...
copy "..\news_lambda_function.py" "lambda_function.py" >nul

echo Installing Python dependencies...
pip install requests beautifulsoup4 boto3 urllib3 --target . >nul

echo Creating deployment package...
powershell -command "Compress-Archive -Path *.* -DestinationPath ..\news-lambda-function.zip -Force"

cd ..

REM Check if AWS CLI is configured
where aws >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Error: AWS CLI not found. Please install and configure AWS CLI.
    exit /b 1
)

REM Get account ID if not provided
if "%ACCOUNT_ID%"=="" (
    echo Getting AWS account ID...
    for /f "tokens=*" %%i in ('aws sts get-caller-identity --query Account --output text') do set ACCOUNT_ID=%%i
    echo Account ID: !ACCOUNT_ID!
)

set ROLE_ARN=arn:aws:iam::!ACCOUNT_ID!:role/!ROLE_NAME!

REM Check if role exists, create if not
echo Checking IAM role...
aws iam get-role --role-name "%ROLE_NAME%" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Creating IAM role: %ROLE_NAME%

    echo { > trust-policy.json
    echo   "Version": "2012-10-17", >> trust-policy.json
    echo   "Statement": [ >> trust-policy.json
    echo     { >> trust-policy.json
    echo       "Effect": "Allow", >> trust-policy.json
    echo       "Principal": { >> trust-policy.json
    echo         "Service": "lambda.amazonaws.com" >> trust-policy.json
    echo       }, >> trust-policy.json
    echo       "Action": "sts:AssumeRole" >> trust-policy.json
    echo     } >> trust-policy.json
    echo   ] >> trust-policy.json
    echo } >> trust-policy.json

    aws iam create-role --role-name "%ROLE_NAME%" --assume-role-policy-document file://trust-policy.json

    echo Attaching policies to role...
    aws iam attach-role-policy --role-name "%ROLE_NAME%" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name "%ROLE_NAME%" --policy-arn arn:aws:iam::aws:policy/AmazonPollyFullAccess

    del trust-policy.json

    echo Waiting for role to be ready...
    timeout /t 10 /nobreak >nul
) else (
    echo IAM role already exists: %ROLE_NAME%
)

REM Check if function exists
echo Checking if Lambda function exists...
aws lambda get-function --function-name "%FUNCTION_NAME%" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo Updating existing function...
    aws lambda update-function-code --function-name "%FUNCTION_NAME%" --zip-file fileb://news-lambda-function.zip

    echo Updating function configuration...
    aws lambda update-function-configuration --function-name "%FUNCTION_NAME%" --timeout 300 --memory-size 512 --environment Variables="{\"AWS_REGION\":\"%AWS_REGION%\",\"VOICE_ID\":\"Zhiyu\"}"
) else (
    echo Creating new Lambda function...
    aws lambda create-function --function-name "%FUNCTION_NAME%" --runtime python3.9 --role "%ROLE_ARN%" --handler lambda_function.lambda_handler --zip-file fileb://news-lambda-function.zip --timeout 300 --memory-size 512 --environment Variables="{\"AWS_REGION\":\"%AWS_REGION%\",\"VOICE_ID\":\"Zhiyu\"}" --region "%AWS_REGION%"
)

echo Deployment completed successfully!
echo Function ARN: arn:aws:lambda:!AWS_REGION!:!ACCOUNT_ID!:function:!FUNCTION_NAME!

REM Clean up
rmdir /s /q "%DEPLOY_DIR%"
del news-lambda-function.zip

echo.
echo To test the function, run:
echo aws lambda invoke --function-name %FUNCTION_NAME% --payload "{}" response.json
echo.
echo To add Telegram credentials, update environment variables:
echo aws lambda update-function-configuration --function-name %FUNCTION_NAME% --environment Variables="{\"AWS_REGION\":\"%AWS_REGION%\",\"VOICE_ID\":\"Zhiyu\",\"TELEGRAM_TOKEN\":\"your_token\",\"CHAT_ID\":\"your_chat_id\"}"

endlocal