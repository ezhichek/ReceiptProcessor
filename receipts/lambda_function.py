import json
import boto3
from datetime import datetime
from parsing import parse_receipt_text


def lambda_handler(event, context):
    s3 = boto3.client('s3')
    textract = boto3.client('textract')

    bucket = event['Records'][0]['bucket']
    response = s3.list_objects_v2(Bucket=bucket)

    if 'Contents' in response:
        # Iterate over the list of objects and print each object's key (filename)
        for obj in response['Contents']:
            key = obj['Key']
            print(f"key: {key}")

            if not key.lower().endswith(('.jpg', '.jpeg', '.png')):
                print(f"File {key} is not a supported image format. Skipping.")
            else:
                try:
                    response = textract.analyze_document(
                        Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                        FeatureTypes=["FORMS", "TABLES"]
                    )

                    blocks = response['Blocks']
                    extracted_text = []
                    kvs = {}

                    for block in blocks:
                        if block['BlockType'] == 'LINE':
                            if 'Text' in block:
                                extracted_text.append(block['Text'])
                        elif block['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in block['EntityTypes']:
                            key_block = block
                            value_block = None
                            for relationship in key_block.get('Relationships', []):
                                if relationship['Type'] == 'VALUE':
                                    value_block = next((item for item in blocks if item['Id'] == relationship['Ids'][0]), None)
                                    break
                            if value_block:
                                key_text = ' '.join([item['Text'] for item in key_block.get('Relationships', []) if 'Text' in item])
                                value_text = ' '.join([item['Text'] for item in value_block.get('Relationships', []) if 'Text' in item])
                                kvs[key_text] = value_text

                    full_text = '\n'.join(extracted_text)
                    #print("Extracted text: ", full_text)
                    #print("Key-Value Pairs: ", kvs)

                    data = parse_receipt_text(full_text)

                    print("Parsed data: ", data)

                    result_bucket = 'result-receipts'
                    result_key = f'results/{datetime.now().strftime("%Y%m%d%H%M%S")}_{key}.json'
                    s3.put_object(
                        Bucket=result_bucket,
                        Key=result_key,
                        Body=json.dumps(data, indent=4),
                        ContentType='application/json'
                    )
                    '''
                    return {
                        'statusCode': 200,
                        'body': json.dumps('Text extraction and key-value pair analysis completed and data saved to S3!')
                    }
                    '''

                except Exception as e:
                    print(f"Error processing file {key}: {str(e)}")
                '''
                return {
                    'statusCode': 500,
                    'body': json.dumps(f'Error processing file: {str(e)}')
                }
                '''


    else:
        print(f"No objects found in bucket {bucket}")


