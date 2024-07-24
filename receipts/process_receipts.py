import boto3

from parse import parse_with_textract

s3 = boto3.client('s3')
bucket = 'my-receipts-bucket'


def lambda_handler(event, context):
    query_params = event.get('queryStringParameters', {})

    model = query_params.get('model', 'llama')
    use_ocr = query_params.get('use_ocr', False)

    response = s3.list_objects_v2(Bucket=bucket)

    if 'Contents' not in response:
        print(f"No objects found in bucket {bucket}")
        return

    for obj in response['Contents']:

        file = obj['Key']

        if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
            print(f"File {file} is not a supported image format. Skipping.")
            continue

        try:

            text = parse_with_textract(bucket, file)

            print(text)

        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")
