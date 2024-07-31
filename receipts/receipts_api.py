import json
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('receipts')

DEFAULT_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
}

def lambda_handler(event, context):
    try:
        query_params = event.get('queryStringParameters', {})
        model_id = query_params.get('model', None)

        if model_id is None:
            return {
                'statusCode': 400,
                'headers': DEFAULT_HEADERS,
                'body': json.dumps("Model ID is required")
            }

        response = table.scan(
            FilterExpression=Key('model_id').eq(model_id)
        )
        data = response['Items']

        return {
            'statusCode': 200,
            'headers': DEFAULT_HEADERS,
            'body': json.dumps(data, default=decimal_default)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': DEFAULT_HEADERS,
            'body': json.dumps('Error retrieving data: ' + str(e))
        }


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError