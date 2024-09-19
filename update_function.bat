@REM c:\users\zhouj21\aws_login_jz.bat

@REM rm Env:AWS_DEFAULT_PROFILE

@REM $env:AWS_PROFILE = "jz"
@REM $env:AWS_PROFILE

@REM aws s3 ls 

tar -a -c -f snapcopy.zip snapCopyFunction/*.py snapCopyFunction/*.sql snapCopyFunction/web

aws lambda update-function-code --no-cli-pager --function-name  snapCopyFunction  --zip-file fileb://snapcopy.zip