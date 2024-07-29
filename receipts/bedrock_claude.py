# def parse_receipt(bucket, file, model, with_textract):
#
#     chat_response = (parse_with_claude(bucket, file, with_textract))
#                      #.replace("\n", ""))
#     #llm_chain = prompt | model | StrOutputParser()
#     ##chat_response = llm_chain.invoke({})
#
#     # print(chat_response)
#
#     #response_body = json.loads(chat_response.get('body').read())
#     print(chat_response['content'][0]['text'].replace("\n", ""))
#
#     json_chat_response = parse_json_from_chat_response(chat_response)
#
#     return json_chat_response
#
#
# def parse_with_claude(bucket, file, with_textract):
#
#     content = [
#         {
#             "type": "text",
#             "text": prompt_context
#         }
#     ]
#
#     if with_textract:
#         file_path = "s3://{bucket}/{file}".format(bucket=bucket, file=file)
#         document = AmazonTextractPDFLoader(file_path, client=textract).load()
#         content.append(
#             {
#                 "type": "text",
#                 "text": f"Please extract the following receipt: {document[0].page_content}"
#             }
#         )
#     else:
#         response = s3.get_object(Bucket=bucket, Key=file)
#         image_data = response['Body'].read()
#         base64_encoded_image = base64.b64encode(image_data).decode('utf-8')
#         content.append(
#             {
#                 "type": "text",
#                 "text": "Please extract the following receipt: "
#             }
#         )
#         content.append(
#             # {
#             #     "type": "image_url",
#             #     "image_url": {
#             #         "url": f"data:image/jpeg;base64,{base64_encoded_image}",
#             #     },
#             # }
#             {
#                 "type": "image",
#                 "source": {
#                     "type": "base64",
#                     "media_type": "image/jpeg",
#                     "data": base64_encoded_image
#                 }
#             }
#         )
#
#     model_input = {
#         "anthropic_version": "bedrock-2023-05-31",
#         "max_tokens": 2048,
#         "messages": [
#             {
#                 "role": "user",
#                 "content": content
#             }
#         ]
#     }
#
#     # Body
#     body = json.dumps(model_input)
#
#     response = bedrock.invoke_model(
#         modelId='anthropic.claude-3-sonnet-20240229-v1:0',
#         contentType='application/json',
#         accept='application/json',
#         body=body
#     )
#
#     # Print response
#     return json.loads(response.get('body').read())
#     #print(response_body['content'][0]['text'])