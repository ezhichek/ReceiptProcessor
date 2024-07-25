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
