# Message-Queue

Full-CD Python Microservice for ingesting from SQS into Mysql DB. 

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: 'AWS::Serverless-2016-10-31'
Resources:
  MessageQueue:
    Type: AWS::SQS::Queue
    Properties:
      KmsMasterKeyId: alias/aws/sqs
      QueueName: DatabaseMessageQueue
  QueueDepthAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmDescription: "Alarm if queue depth increases to more than 150 messages"
      Namespace: "AWS/SQS"
      MetricName: "ApproximateNumberOfMessagesVisible"
      Dimensions:
        -
          Name: "QueueName"
          Value:
            Fn::GetAtt:
              - "MessageQueue"
              - "QueueName"
      Statistic: "Sum"
      Period: "300"
      EvaluationPeriods: "1"
      Threshold: "150"
      ComparisonOperator: "GreaterThanThreshold"
      AlarmActions:
        - arn:aws:sns:us-east-1:476889715112:unhealthyHost
      InsufficientDataActions:
        - arn:aws:sns:us-east-1:476889715112:unhealthyHost
Outputs:
  QueueURL:
    Description: "URL of new Amazon SQS Queue"
    Value:
      Ref: "MessageQueue"
  QueueARN:
    Description: "ARN of new AmazonSQS Queue"
    Value:
      Fn::GetAtt:
        - "MessageQueue"
        - "Arn"
  QueueName:
    Description: "Name of new Amazon SQS Queue"
    Value:
      Fn::GetAtt:
        - "MessageQueue"
        - "QueueName"
```

Deployed Via Jenkins

```groovy
#! groovy

currentBuild.displayName = "Message Queue [$currentBuild.number]"

FUNC_NAME="message-queue"
String commitHash = ""

try {
    if (ISSUE_NUMBER)
        echo "Building from pull request..."
} catch (Exception ignored) {
    ISSUE_NUMBER = false
    echo "Building from jenkins job..."
}

pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr:'10'))
        disableConcurrentBuilds()
        quietPeriod(1)
    }
    parameters {
        booleanParam(name: 'DeleteExisting', defaultValue: false, description: 'Delete existing stack?')
        booleanParam(name: 'Deploy', defaultValue: true, description: 'Deploy latest artifact')
    }
    stages {

        stage("Checkout") {
            steps {
                script {
                    prTools.checkoutBranch(ISSUE_NUMBER, "vizzyy-org/$FUNC_NAME")
                    commitHash = env.GIT_COMMIT.substring(0,7)
                }
            }
        }

        stage("Delete Stack") {
            when {
                expression {
                    return env.DeleteExisting == "true"
                }
            }
            steps {
                script {
                    sh("aws cloudformation delete-stack --stack-name $FUNC_NAME")
                    sh("aws cloudformation wait stack-delete-complete --stack-name $FUNC_NAME")
                }
            }
        }

        stage("Package") {
            steps {
                script {
                    sh("/usr/local/bin/sam package --s3-bucket vizzyy-packaging --output-template-file packaged.yml")
                }
            }
        }

        stage("Deploy") {
            when {
                expression {
                    return env.Deploy == "true"
                }
            }
            steps {
                script {
                    try {
                        sh("/usr/local/bin/sam deploy --template-file packaged.yml --stack-name $FUNC_NAME --capabilities CAPABILITY_IAM")
                    } catch (Exception e) {
                        echo "Could not SAM deploy -- empty changeset?"
                    }

                    sh("ssh pi@four.local 'cd /home/pi/message-queue; git pull origin master; sudo systemctl restart queue; sudo systemctl status queue;'")
                }
            }
        }

    }
    post {
        success {
            script {
                sh "echo '${env.GIT_COMMIT}' > ~/userContent/$FUNC_NAME-last-success-hash.txt"
                echo "SUCCESS"
            }
        }
        failure {
            script {
                echo "FAILURE"
            }
        }
        cleanup { // Cleanup post-flow always executes last
            deleteDir()
        }
    }
}
```
