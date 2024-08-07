import base64
from io import BytesIO

import boto3
from multipart import parse_form_data

RECEIPTS_BUCKET = 'my-receipts-bucket'

s3 = boto3.client('s3')

DEFAULT_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    try:

        # HTTP headers are case-insensitive
        headers = {k.lower(): v for k, v in event['headers'].items()}

        # AWS API Gateway applies base64 encoding on binary data
        body = base64.b64decode(event['body'])

        # Parse the multipart form data
        form, files = parse_form_data({
            'CONTENT_TYPE': headers['content-type'],
            'REQUEST_METHOD': 'POST',
            'wsgi.input': BytesIO(body)
        })

        for key, file in files.items():
            print(f"Uploading receipt (file name: {file.filename}, size: {file.size})\n")
            s3.put_object(Bucket=RECEIPTS_BUCKET, Key=file.filename, Body=file.raw)

        return {
            'statusCode': 200,
            'headers': DEFAULT_HEADERS,
            'body': 'File uploaded successfully'
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': DEFAULT_HEADERS,
            'body': 'Error uploading file: ' + str(e)
        }
