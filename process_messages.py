import json
import time
import boto3
from config import *
import mysql.connector

sqs = boto3.client('sqs')
db = None
cursor = None


def attempt_db_connection():
    global db, cursor
    try:
        db = mysql.connector.connect(**SSL_CONFIG)
        print("Connected to DB!")
        return True
    except Exception as e:
        print(e)
        return False


def process_queue():
    global db, cursor

    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )

    if "Messages" not in response.keys():
        print("No messages to process.")
        return False

    message = response['Messages'][0]
    body = json.loads(message['Body'])
    receipt_handle = message['ReceiptHandle']
    message_id = message['MessageId']

    print(f"Received message: {message_id}")

    if body["table"] == "spork_metrics":
        if db and store_spork_log(body):
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            print(f"Processed & deleted spork_metrics message: {message_id}")
            return True
        else:
            return False

    if db and store_canary_log(body):
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        print(f"Processed & deleted message: {message_id}")
        return True
    else:
        return False


def store_canary_log(body):
    global db, cursor
    try:
        db.ping(True)  # Assert connection valid, otherwise attempt to reconnect (True)

        path = body["values"]["path"]
        success = body["values"]["success"]
        timestamp = body["values"]["timestamp"]
        elapsed_ms = body["values"]["ms_elapsed"]
        params = (path, elapsed_ms, timestamp, int(not success), int(success))

        cursor = db.cursor()  # Cursor init is very cheap, so we do not reuse it
        sql = f"INSERT INTO graphing_data.canary_metrics(path, ms_elapsed, timestamp, error, success) " \
              f"VALUES(%s, %s, %s, %s, %s)"
        cursor.execute(sql, params)
        db.commit()
        cursor.close()
        print(f"inserted canary_metrics: {params}")
        return True
    except Exception as e:
        print(e)
        return False


def store_spork_log(body):
    global db, cursor
    try:
        db.ping(True)  # Assert connection valid, otherwise attempt to reconnect (True)

        user = body["values"]["user"]
        service = body["values"]["service"]
        message = body["values"]["message"]
        success = body["values"]["success"]
        timestamp = body["values"]["timestamp"]
        params = (service, user, message, timestamp, int(not success), int(success))

        cursor = db.cursor()  # Cursor init is very cheap, so we do not reuse it
        sql = f"INSERT INTO graphing_data.spork_metrics(service, user, message, timestamp, error, success) " \
              f"VALUES(%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, params)
        db.commit()
        cursor.close()
        print(f"inserted spork_metrics: {params}")
        return True
    except Exception as e:
        print(e)
        return False


while True:
    if not db:
        attempt_db_connection()

    print(f"Checking queue...")
    if not process_queue():
        time.sleep(10)
