import base64
import json
import re
import boto3
from langchain_aws import ChatBedrock
from langchain_community.document_loaders import AmazonTextractPDFLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

RECEIPTS_BUCKET = 'my-receipts-bucket'
RESULTS_BUCKET = 'result-receipts'

s3 = boto3.client('s3')
textract = boto3.client('textract')
bedrock = boto3.client("bedrock-runtime")


def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})

    model_id = query_params.get('model_id', 'claude-3')
    with_textract = query_params.get('with_textract', False)

    model = create_model(model_id)

    response = s3.list_objects_v2(Bucket=RECEIPTS_BUCKET)

    if 'Contents' not in response:
        print(f"No objects found in bucket {RECEIPTS_BUCKET}")
        return

    json_responses = []

    for obj in response['Contents']:

        file = obj['Key']
        if not file.lower().endswith('.jpg'):
            print(f"File {file} is not a supported image format. Skipping.")
            continue

        try:
            print(f"Parsing receipt (model: {model_id}, with_textract: {with_textract}, bucket: {RECEIPTS_BUCKET}, file: {file}\n")

            json_chat_response = parse_receipt(RECEIPTS_BUCKET, file, model, with_textract)
            if json_chat_response is not None:
                json_responses.append(json_chat_response)

        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")

    json_str = json.dumps(json_responses)

    if with_textract:
        write_json_file_to_bucket(RESULTS_BUCKET, f"results-{model_id}-textract.json", json_str)
    else:
        write_json_file_to_bucket(RESULTS_BUCKET, f"results-{model_id}.json", json_str)


def parse_receipt(bucket, file, model, with_textract):

    prompt = create_prompt(bucket, file, with_textract)
    llm_chain = prompt | model | StrOutputParser()
    chat_response = llm_chain.invoke({}).replace("\n", "")

    print(chat_response)

    json_chat_response = parse_json_from_chat_response(chat_response)

    return json_chat_response


def create_prompt(bucket, file, with_textract):

    context_message = """
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
        """

    if with_textract:
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


def create_model(model):
    if model == 'claude-3':
        return ChatBedrock(
            client=bedrock,
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            model_kwargs={"max_tokens": 2048, "temperature": 0.0}
        )

    raise Exception(f"Unsupported model: {model}")


def parse_json_from_chat_response(chat_response):
    json_match = re.search(r'\{.*?\}', chat_response, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        json_data = json.loads(json_str)
        return json_data
    else:
        return None


def write_json_file_to_bucket(bucket, file_name, json_content):
    try:
        # Write the JSON data to the S3 bucket
        s3.put_object(
            Bucket=bucket,
            Key=file_name,
            Body=json_content,
            ContentType='application/json'
        )
        print(f'Successfully wrote data to {bucket}/{file_name}')

    except Exception as e:
        print(f'Error writing data to S3: {e}')
