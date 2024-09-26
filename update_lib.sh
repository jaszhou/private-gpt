

#!/bin/bash

# This script updates the Lambda function layers
# Install requirements and create a zip file for the layer


pip install -r requirements.txt -t python/
zip -r layer.zip python


v=$(aws lambda publish-layer-version --no-cli-pager --layer-name lambda-layer --zip-file fileb://layer.zip --region ap-southeast-2 --output json --query LayerVersionArn)

# get latest layer version from the output of the publish-layer-version command

echo $v

# careful not override the custom lib for PIL
# aws lambda update-function-configuration --no-cli-pager --function-name  snapCopyFunction --layers arn:aws:lambda:ap-southeast-2:647207328002:layer:lambda-layer:6
# aws lambda update-function-configuration --no-cli-pager --function-name  snapCopyFunction --layers arn:aws:lambda:ap-southeast-2:647207328002:layer:lambda-layer:7

aws lambda update-function-configuration --no-cli-pager --function-name  snapCopyFunction --layers "$v"


aws lambda update-function-configuration --no-cli-pager --function-name  snapCopyFunction --layers arn:aws:lambda:ap-southeast-2:770693421928:layer:Klayers-p39-pillow:1


# ver=`aws lambda publish-layer-version --no-cli-pager --layer-name test-layer --zip-file fileb://layer.zip --region ap-southeast-2 --output json --query LayerVersionArn`

# echo "version: $ver"

