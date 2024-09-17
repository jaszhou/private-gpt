tar -a -c -f snapcopy.zip *.py

aws lambda update-function-code --function-name  snapCopyFunction  --zip-file fileb://snapcopy.zip