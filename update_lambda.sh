tar -a -c -f snapcopy.zip snapCopyFunction/*.py snapCopyFunction/*.sql snapCopyFunction/web

aws lambda update-function-code --no-cli-pager --function-name  snapCopyFunction  --zip-file fileb://snapcopy.zip
