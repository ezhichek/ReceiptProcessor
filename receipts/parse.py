import boto3
from langchain_aws import ChatBedrock
from langchain_community.document_loaders import AmazonTextractPDFLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

textract = boto3.client('textract')
bedrock = boto3.client("bedrock-runtime")


def parse(file_path):

    loader = AmazonTextractPDFLoader(file_path, client=textract)

    document = loader.load()

    page_content = document[0].page_content

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Given a receipt or invoice, please extract Merchant, Currency, Amount, VAT Rate and invoice number as JSON from that receipt or invoice"),
            ("human", "Please extract the following receipt: {receipt_text}"),
        ]
    )

    model_kwargs = {
        "max_tokens": 2048,
        "temperature": 0.0,
        # "top_k": 250,
        # "top_p": 1,
        # "stop_sequences": ["\n\nHuman"],
    }

    bedrock_llm = ChatBedrock(
        client=bedrock,
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        model_kwargs=model_kwargs
    )

    llm_chain = prompt | bedrock_llm | StrOutputParser()
    content = llm_chain.invoke({"receipt_text": page_content})

    return content
