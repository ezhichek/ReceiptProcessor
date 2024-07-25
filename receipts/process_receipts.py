import json
import re

import boto3
from langchain_aws import ChatBedrock
from langchain_community.document_loaders import AmazonTextractPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

s3 = boto3.client('s3')
textract = boto3.client('textract')
bedrock = boto3.client("bedrock-runtime")

receipts_bucket = 'my-receipts-bucket'
results_bucket = 'result-receipts'

def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})

    model = query_params.get('model', 'llama')
    use_ocr = query_params.get('use_ocr', False)

    response = s3.list_objects_v2(Bucket=receipts_bucket)

    if 'Contents' not in response:
        print(f"No objects found in bucket {receipts_bucket}")
        return

    json_responses = []

    for obj in response['Contents']:

        file = obj['Key']
        if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
            print(f"File {file} is not a supported image format. Skipping.")
            continue

        try:
            file_path = "s3://{bucket}/{file}".format(bucket=receipts_bucket, file=file)
            print(f"loading {file_path}\n")

            chat_response = parse(file_path).replace("\n", "")

            print(chat_response)

            json_chat_response = parse_json_from_chat_response(chat_response)
            if json_chat_response is not None:
                json_responses.append(json_chat_response)

        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")

    json_str = json.dumps(json_responses)
    store_results('claude-3-results.json', json_str)


def parse(file_path):
    loader = AmazonTextractPDFLoader(file_path, client=textract)

    document = loader.load()

    page_content = document[0].page_content

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """
                Given a receipt or invoice you should extract date, merchant, currency, total amount, vat amount and invoice number into a json structure. The structure should look like this:

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
                """),

            ("human", "Please extract the following receipt: {receipt_text}"),
        ]
    )

    model_kwargs = {
        "max_tokens": 2048,
        "temperature": 0.0,
    }

    bedrock_llm = ChatBedrock(
        client=bedrock,
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs=model_kwargs
    )

    llm_chain = prompt | bedrock_llm | StrOutputParser()
    response = llm_chain.invoke({"receipt_text": page_content})

    return response


def parse_json_from_chat_response(chat_response):
    json_match = re.search(r'\{.*?\}', chat_response, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        json_data = json.loads(json_str)
        return json_data
    else:
        return None

def store_results(file_name, json_content):
    try:
        # Write the JSON data to the S3 bucket
        s3.put_object(
            Bucket=results_bucket,
            Key=file_name,
            Body=json_content,
            ContentType='application/json'
        )
        print(f'Successfully wrote data to {results_bucket}/{file_name}')

    except Exception as e:
        print(f'Error writing data to S3: {e}')
