del zappa.zip

tar -a -c -f ..\zappa.zip django_scim sailpoint *.py *.txt *.json

aws s3 cp layer.zip s3://cba-nonprod-beacon/data/cba-nonprod/tmp/layer.zip
aws s3 cp task.zip s3://cba-nonprod-beacon/data/cba-nonprod/tmp/task.zip

@REM aws lambda update-function-code --function-name BeaconUserAPI --zip-file fileb://BeaconUserAPI.zip --region ap-southeast-2


@REM sam local invoke --invoke-image hub.docker.internal.cba/sam/emulation-python3.9

@REM # Invoke a function locally in debug mode on port 5858
@REM sam local invoke -d 5858 <function logical id>

@REM # Start local API Gateway in debug mode on port 5858
@REM sam local start-api -d 5858

@REM sam local start-lambda 

@REM sam build --use-container --build-image python-docker

@REM sam local generate-event apigateway http-api-proxy | clip

@REM sam local invoke "HelloWorldFunction" -e sailpoint\events\event.json --invoke-image hub.docker.internal.cba/sam/emulation-python3.9 

sam local invoke "SailPointFunction" -e events\event.json --invoke-image hub.docker.internal.cba/sam/emulation-python3.9 

cd c:\dev\jason\zappa\zappa
sam local invoke "SailPointFunction" -e events\event.json --invoke-image lambda

@REM sam local invoke -d 5858 "HelloWorldFunction" -e events\event.json --invoke-image hub.docker.internal.cba/sam/emulation-python3.9 

docker login hub.docker.internal.cba

docker pull hub.docker.internal.cba/mlupin/docker-lambda:python3.9-build

docker tag <> lambda_local


@REM sam local start-api --invoke-image hub.docker.internal.cba/sam/emulation-python3.9
@REM sam local start-api --invoke-image sam/emulation-python3.9:rapid-1.42.0-x86_64

sam local start-api --invoke-image flask_local

@REM docker build -t sam/emulation-python3.9 .

docker build -t lambda . 

@REM sam build --use-container --build-image sam/emulation-python3.9:rapid-1.42.0-x86_64

update layer:

mkdir python
pip install -r requirements.txt -t python/
zip -r layer.zip python

tar -a -c -f layer.zip python
aws lambda publish-layer-version --layer-name lambda-layer --zip-file fileb://layer.zip --compatible-runtimes python3.9 --region ap-southeast-2

aws lambda update-function-configuration --function-name  API_SailPoint --layers arn:aws:lambda:ap-southeast-2:247580911166:layer:lambda-layer:3

aws s3 cp layer.zip s3://cba-nonprod-beacon/data/cba-nonprod/tmp/layer.zip

tar -a -c -f zappa.zip django_scim sailpoint *.py *.txt *.json

aws lambda update-function-code --function-name  API_SailPoint  --zip-file fileb://zappa.zip


debug lambda from docker:

cd c:\dev\jason\zappa 
zappashell.bat 
cd zappa 
source ve/bin/activate
python manage.py runserver 

open another bash of the docker and run:


https://docs.aws.amazon.com/lambda/latest/dg/images-test.html
docker build -t lambda_local -f Dockerfile_build .


docker run -p 9000:8080  myfunction:latest 
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d @test/api_gateway.json --header "Content-Type: application/json"

curl -vX POST http://server/api/v1/places.json -d @testplace.json \
--header "Content-Type: application/json"

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"payload":"hello world!"}'


@REM Build docker image 
docker build -t flask_local .

docker run -p 9000:8080 flask_local:latest

curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d "{"""msg""":"""hello"""}"


Debug a flask application:


flask --app app.py --debug run

