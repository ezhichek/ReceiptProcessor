import json
import boto3
import base64
import os

s3 = boto3.client('s3')
bucket_name = os.environ['BUCKET_NAME']

DEFAULT_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}
def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        file_content = base64.b64decode(body['file'])
        file_name = body['fileName']

        s3.put_object(Bucket=bucket_name, Key=file_name, Body=file_content)

        return {
            'statusCode': 200,
            'headers': DEFAULT_HEADERS,
            'body': json.dumps({'message': 'File uploaded successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': DEFAULT_HEADERS,
            'body': json.dumps('Error uploading file: ' + str(e))
        }
