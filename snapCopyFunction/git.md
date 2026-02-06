git remote set-url origin https://jaszhou:<pat>@github.com/jaszhou/SnapCopy.git
git branch -M main
git push -u origin main


echo "# SnapCopy" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/jaszhou/SnapCopy.git
git push -u origin main

Steps:

Run ubuntu 22.04 WSL
Go to /mnt/e/github/SnapCopy
run code .

https://zappa-m3secjk20.s3.amazonaws.com/about.html

use deploy_lambda.sh to deploy new code 

