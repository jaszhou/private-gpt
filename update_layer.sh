
# @REM c:\users\zhouj21\aws_login_np.bat 

# @REM mkdir python

# @REM conda activate py39 

# @REM zappashell.bat 

# python -m pip config set global.index-url https://zhouj21:AP734SrTNB2L6zUUWfWSxBH2piN@artifactory.internal.cba/artifactory/api/pypi/pypi/simple


pip install -r requirements.txt -t python/
zip -r layer.zip python

# tar -a -c -f layer.zip python8

aws s3 cp layer.zip s3://cba-nonprod-beacon/data/cba-nonprod/tmp/layer.zip


# aws lambda publish-layer-version --layer-name lambda-layer --zip-file fileb://layer.zip --compatible-runtimes python3.9 --region ap-southeast-2

aws lambda publish-layer-version --layer-name lambda-layer --content S3Bucket=cba-nonprod-beacon,S3Key='data/cba-nonprod/tmp/layer.zip' --compatible-architectures x86_64 --compatible-runtimes python3.9 --region ap-southeast-2

aws lambda update-function-configuration --function-name  API_SailPoint --layers arn:aws:lambda:ap-southeast-2:247580911166:layer:lambda-layer:11

