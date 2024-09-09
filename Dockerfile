#FROM hub.docker.internal.cba/mlupin/docker-lambda:python3.9-build
#FROM public.ecr.aws/lambda/python:3.9
#FROM hub.docker.internal.cba/lambda/python:3.9
FROM lambda_local

#docker login hub.docker.internal.cba
#docker pull hub.docker.internal.cba/lambda/python:3.9

WORKDIR /var/task
ADD requirements.txt /var/task/


RUN python -m pip config set global.index-url https://artifactory.internal.cba/artifactory/api/pypi/pypi/simple


#COPY requirements.txt  .
RUN  pip install -r requirements.txt

# Copy function code
COPY *.py /var/task/


# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "handler.lambda_handler" ]

