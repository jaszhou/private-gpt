Error:

[ERROR] Runtime.ImportModuleError: Unable to import module 'snapCopyFunction.lambda_function': No module named 'botocore.docs'
Traceback (most recent call last):

Cause:

Wrong version of Lambda Layer used

Fix:

use this version:  arn:aws:lambda:ap-southeast-2:647207328002:layer:snapCopyDeps:16
not version 11

