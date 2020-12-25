import json
import time
import boto3
from config import *

sqs = boto3.client('sqs')


def process_queue():
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

    # print(response)
    if "Messages" not in response.keys():
        print("No messages to process.")
        return False

    messages = response['Messages']
    print(f"message count: {len(messages)}")
    message = response['Messages'][0]
    body = json.loads(message['Body'])
    receipt_handle = message['ReceiptHandle']
    message_id = message['MessageId']

    print(f"Received message: {message_id}")
    # print(f"{body}")

    if store_log(body):
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        print(f"Processed & deleted message: {message_id}")
        return True
    else:
        return False


# body = {
#     'action': 'insert',
#     'table': 'canary_metrics',
#     'values': {
#         'path': '/logs',
#         'ms_elapsed': 82.58699999999999,
#         'timestamp': '2020-12-24 14:34:19.940642',
#         'success': True
#     }
# }

def store_log(body):
    try:
        path = body["values"]["path"]
        success = body["values"]["success"]
        timestamp = body["values"]["timestamp"]
        elapsed_ms = body["values"]["ms_elapsed"]

        sql = f"INSERT INTO graphing_data.canary_metrics(path, ms_elapsed, timestamp, error, success) " \
              f"VALUES('{path}', '{elapsed_ms}', '{timestamp}', '{int(not success)}', '{int(success)}')"
        cursor.execute(sql)
        db.commit()
        print(f"{sql}")
        return True
    except Exception as e:
        print(f"Could not store metrics: {e}")
        return False


while True:
    print(f"Checking queue...")
    if not process_queue():
        time.sleep(10)
