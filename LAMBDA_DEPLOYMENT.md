# AWS Lambda Deployment Instructions for News Function

This guide explains how to deploy the news scraping and voice generation Lambda function.

## Files

- `news_lambda_function.py` - Main Lambda function
- `requirements.txt` - Python dependencies
- `deploy.sh` - Deployment script (Linux/Mac)
- `deploy.bat` - Deployment script (Windows)

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Python 3.9 or 3.10 (recommended for Lambda)
3. ZIP utility

## Required AWS Permissions

Your AWS user/role needs the following permissions:
- `lambda:CreateFunction`
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `polly:SynthesizeSpeech`

## Environment Variables

Configure these environment variables in Lambda:

```bash
AWS_REGION=us-east-1          # AWS region
VOICE_ID=Zhiyu               # AWS Polly voice (Chinese voice)
TELEGRAM_TOKEN=your_bot_token # Optional: Telegram bot token
CHAT_ID=your_chat_id         # Optional: Telegram chat ID
```

## Deployment Steps

### Method 1: Using AWS CLI (Recommended)

1. **Prepare the deployment package:**
   ```bash
   # Create deployment directory
   mkdir lambda-deploy
   cd lambda-deploy

   # Copy the Lambda function
   cp ../news_lambda_function.py lambda_function.py

   # Install dependencies
   pip install -r ../requirements.txt --target .

   # Create deployment package
   zip -r news-lambda-function.zip .
   ```

2. **Create IAM role for Lambda:**
   ```bash
   aws iam create-role --role-name NewsLambdaRole --assume-role-policy-document '{
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
   }'

   # Attach basic Lambda execution policy
   aws iam attach-role-policy --role-name NewsLambdaRole --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

   # Attach Polly policy
   aws iam attach-role-policy --role-name NewsLambdaRole --policy-arn arn:aws:iam::aws:policy/AmazonPollyFullAccess
   ```

3. **Create Lambda function:**
   ```bash
   aws lambda create-function \
     --function-name news-scraper-function \
     --runtime python3.9 \
     --role arn:aws:iam::647207328002:role/NewsLambdaRole \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://news-lambda-function.zip \
     --timeout 300 \
     --memory-size 512 
   ```

4. **Update function code (for updates):**
   ```bash
   aws lambda update-function-code \
     --function-name news-scraper-function \
     --zip-file fileb://news-lambda-function.zip
   ```

### Method 2: Using AWS Console

1. **Package the function:**
   - Create a folder named `lambda-deploy`
   - Copy `news_lambda_function.py` to `lambda-deploy/lambda_function.py`
   - Install dependencies: `pip install -r requirements.txt --target lambda-deploy/`
   - Zip the entire `lambda-deploy` folder

2. **Create the function in AWS Console:**
   - Go to AWS Lambda console
   - Click "Create function"
   - Choose "Author from scratch"
   - Function name: `news-scraper-function`
   - Runtime: Python 3.9
   - Create new execution role with basic Lambda permissions
   - Add Polly permissions to the role

3. **Upload and configure:**
   - Upload the ZIP file
   - Set handler to `lambda_function.lambda_handler`
   - Configure timeout: 5 minutes
   - Configure memory: 512 MB
   - Add environment variables

## Testing

### Local Testing
```bash
python news_lambda_function.py
```

### Lambda Testing
Create a test event in the Lambda console with an empty JSON object:
```json
{}
```

## Scheduling (Optional)

To run the function automatically, create an EventBridge (CloudWatch Events) rule:

```bash
aws events put-rule \
  --name NewsScrapingSchedule \
  --schedule-expression "rate(6 hours)"

aws lambda add-permission \
  --function-name news-scraper-function \
  --statement-id NewsScrapingSchedulePermission \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:YOUR_ACCOUNT_ID:rule/NewsScrapingSchedule

aws events put-targets \
  --rule NewsScrapingSchedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:news-scraper-function"
```

## Troubleshooting

### Common Issues

1. **Import Errors:**
   - Ensure all dependencies are installed in the deployment package
   - Check that `beautifulsoup4` is included

2. **Timeout Errors:**
   - Increase Lambda timeout (current: 5 minutes)
   - Consider reducing the number of articles scraped

3. **Memory Errors:**
   - Increase Lambda memory allocation
   - Monitor CloudWatch logs for memory usage

4. **Network Errors:**
   - Check VPC configuration if Lambda is in a VPC
   - Ensure Lambda has internet access for web scraping

5. **Polly Errors:**
   - Verify IAM permissions for Polly
   - Check AWS region configuration
   - Ensure text length doesn't exceed Polly limits

### Monitoring

Check CloudWatch logs for function execution details:
```bash
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/news-scraper-function
```

## Cost Considerations

- **Lambda:** ~$0.000017 per GB-second
- **Polly:** ~$4 per 1M characters
- **Data transfer:** Standard AWS rates
- **Storage:** CloudWatch logs retention

Estimated monthly cost for 4 executions per day: ~$5-10 USD

## Security Notes

1. Store sensitive credentials (Telegram tokens) in AWS Secrets Manager or Parameter Store
2. Use least-privilege IAM policies
3. Consider VPC deployment for enhanced security
4. Enable CloudTrail for audit logging

Function URL:  

https://v4kjkzozvkwhwssfmx2nuayzmm0vagpr.lambda-url.ap-southeast-2.on.aws/
