
pip install -r requirements.txt -t python/
zip -r layer.zip python

aws lambda publish-layer-version --no-cli-pager --layer-name lambda-layer --zip-file fileb://layer.zip --region ap-southeast-2

# careful not override the custom lib for PIL
# aws lambda update-function-configuration --no-cli-pager --function-name  snapCopyFunction --layers arn:aws:lambda:ap-southeast-2:647207328002:layer:lambda-layer:6
