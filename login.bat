c:\users\zhouj21\aws_login_jz.bat

rm Env:AWS_DEFAULT_PROFILE

$env:AWS_PROFILE = "jz"
$env:AWS_PROFILE

aws s3 ls 

@REM tar -a -c -f snapcopy.zip snapCopyFunction/*.py snapCopyFunction/*.sql snapCopyFunction/web

@REM aws lambda update-function-code --function-name  snapCopyFunction  --zip-file fileb://snapcopy.zip --no-paginate