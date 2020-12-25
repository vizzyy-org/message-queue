#!/bin/bash

FUNC_NAME="message-queue"

aws cloudformation delete-stack --stack-name $FUNC_NAME # delete stack

sam package --s3-bucket vizzyy-packaging --output-template-file packaged.yml
aws cloudformation wait stack-delete-complete --stack-name $FUNC_NAME
sam deploy --template-file packaged.yml --stack-name $FUNC_NAME --capabilities CAPABILITY_IAM
rm packaged.yml
