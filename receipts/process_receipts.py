import base64
import json
import os
import re
from decimal import Decimal

import boto3
from langchain_aws import ChatBedrock
from langchain_community.document_loaders import AmazonTextractPDFLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

table_name = os.environ['TABLE_NAME']

s3 = boto3.client('s3')
textract = boto3.client('textract', region_name='eu-west-3')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

model_configs = {
    'claude-3-sonnet-vanilla': {
        'model': ChatBedrock(client=bedrock, model_id='anthropic.claude-3-sonnet-20240229-v1:0', model_kwargs={'max_tokens': 2048, 'temperature': 0.0}),
        'use_textract': False
    },
    'claude-3-sonnet-textract': {
        'model': ChatBedrock(client=bedrock, model_id='anthropic.claude-3-sonnet-20240229-v1:0', model_kwargs={'max_tokens': 2048, 'temperature': 0.0}),
        'use_textract': True
    },
    'mistral-large-2402-textract': {
        'model': ChatBedrock(client=bedrock, model_id='mistral.mistral-large-2402-v1:0'),
        'use_textract': True
    },
    'llama3-70b-instruct-textract': {
        'model': ChatBedrock(client=bedrock, model_id='meta.llama3-70b-instruct-v1:0'),
        'use_textract': True
    },
    'titan-text-premier-textract': {
        'model': ChatBedrock(client=bedrock, model_id='amazon.titan-text-premier-v1:0'),
        'use_textract': True
    }
}

def lambda_handler(event, context):

    table = dynamodb.Table(table_name)

    for record in event['Records']:

        bucket = record['s3']['bucket']['name']
        file = record['s3']['object']['key']

        if not file.lower().endswith('.jpg'):
            print(f"File {file} is not a supported image format. Skipping.")
            continue

        for model_id, model_config in model_configs.items():

            model = model_config['model']
            use_textract = model_config['use_textract']

            print(f"Processing receipt (model: {model.model_id}, with_textract: {use_textract}, bucket: {bucket}, file: {file})\n")

            json_chat_response = parse_receipt(bucket, file, model, use_textract)

            if json_chat_response is None:
                continue

            json_chat_response['model_id'] = model_id
            json_chat_response['file_name'] = file
            # convert all floats to Decimal (required by dynamo)
            json_chat_response = json.loads(json.dumps(json_chat_response), parse_float=Decimal)
            response = table.put_item(Item=json_chat_response)


def parse_receipt(bucket, file, model, use_textract):
    try:

        print(f"Parsing receipt (model: {model.model_id}, with_textract: {use_textract}, bucket: {bucket}, file: {file})\n")

        prompt = create_prompt(bucket, file, use_textract)
        llm_chain = prompt | model | StrOutputParser()
        chat_response = llm_chain.invoke({}).replace("\n", "")

        print(chat_response)

        return parse_json_from_chat_response(chat_response)

    except Exception as e:
        print(f"Error parsing receipt (model: {model.model_id}, with_textract: {use_textract}, bucket: {bucket}, file: {file}): {str(e)}")
        return None


def create_prompt(bucket, file, use_textract):

    context_message = """
        Given a receipt or invoice you should extract date, merchant, currency, total amount, vat amount and invoice number into a json structure. 
        The structure should look like this:

        {{
            "merchant": "Some merchant",
            "currency": "EUR",
            "total_amount": 100,
            "vat_amount": 2.00,
            "invoice_number": "12345",
            "date": "2018-02-01"
        }}

        1. Don't extract any line items but just totals! 
        2. If you can't find a currency then take the default currency of the merchant's location!
        3. Currency should be extracted or converted into a 3-digit currency code!
        4. Date should be extracted or converted into ISO format!
        """

    if use_textract:
        file_path = "s3://{bucket}/{file}".format(bucket=bucket, file=file)
        document = AmazonTextractPDFLoader(file_path, client=textract).load()
        receipt_message = [
            {
                "type": "text",
                "text": f"Please extract the following receipt: {document[0].page_content}"
            }
        ]
    else:
        response = s3.get_object(Bucket=bucket, Key=file)
        image_data = response['Body'].read()
        base64_encoded_image = base64.b64encode(image_data).decode('utf-8')
        receipt_message = [
            {
                "type": "text",
                "text": "Please extract the following receipt: "
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_encoded_image}",
                },
            }
        ]

    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=context_message),
            HumanMessage(content=receipt_message)
        ]
    )


def parse_json_from_chat_response(chat_response):
    json_match = re.search(r'\{.*?\}', chat_response, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        json_data = json.loads(json_str)
        return json_data
    else:
        return None
