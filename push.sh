#!/bin/bash
set -e

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 727646507402.dkr.ecr.us-east-1.amazonaws.com

docker build -t damelo-db .

docker tag damelo-db:latest 727646507402.dkr.ecr.us-east-1.amazonaws.com/damelo-db:latest

docker push 727646507402.dkr.ecr.us-east-1.amazonaws.com/damelo-db:latest