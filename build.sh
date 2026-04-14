#!/bin/bash
set -e
pip install -r src/requirements.txt -t ./package
cp src/lambda_function.py src/data.py ./package/
cd package && zip -r ../lambda.zip . && cd ..
echo "Built lambda.zip"
