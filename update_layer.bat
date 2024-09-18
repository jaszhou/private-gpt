
@REM c:\users\zhouj21\aws_login_np.bat 

@REM mkdir python

@REM conda activate py39 

@REM zappashell.bat 

python -m pip config set global.index-url https://artifactory.internal.cba/artifactory/api/pypi/pypi/simple


python -m pip install -r requirements.txt -t python/

@REM python -m pip install -r requirements.txt -t python

@REM zip -r layer.zip python

del layer.zip

@REM rm -rf python

tar -a -c -f layer.zip python

@REM aws lambda publish-layer-version --layer-name lambda-layer --zip-file fileb://layer.zip --compatible-runtimes python3.9 --compatible-architectures x86_64 --region ap-southeast-2

@REM aws lambda update-function-configuration --function-name  API_SailPoint --layers arn:aws:lambda:ap-southeast-2:247580911166:layer:lambda-layer:6

