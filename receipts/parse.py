import re
from datetime import datetime

import boto3

textract = boto3.client('textract')

merchant_regex = re.compile(r'', re.IGNORECASE)
country_regex = re.compile(r'(Germany|Deutschland|France)', re.IGNORECASE)
invoice_number_regex = re.compile(r'(?:invoice number|rechnungsnummer|número de factura|Bestellnummer|Beleg-Nr\.|Facture|Reçu)\s*[:.]*\s*(\d+)', re.IGNORECASE)
date_regex = re.compile(r'(?:date|datum|fecha|Datum|Date)\s*[:.]*\s*(\d{2}[./-]\d{2}[./-]\d{4})', re.IGNORECASE)
currency_regex = re.compile(r'(EUR|USD|Eur)', re.IGNORECASE)
total_amount_regex = re.compile(r'(?:Gesamtsumme|Betrag|Montant Total|Total|Prix Nets en Euros|TOTAL)\s*(\d+[.,]\d{2})', re.IGNORECASE)
vat_0_regex = re.compile(r'0%\s*MwSt\s*:\s*(\d+[.,]\d{2})', re.IGNORECASE)
vat_7_regex = re.compile(r'7%\s*MwSt\s*:\s*(\d+[.,]\d{2})', re.IGNORECASE)
vat_10_regex = re.compile(r'10%\s*MwSt\s*:\s*(\d+[.,]\d{2})', re.IGNORECASE)
vat_19_regex = re.compile(r'19%\s*MwSt\s*:\s*(\d+[.,]\d{2})', re.IGNORECASE)
vat_21_regex = re.compile(r'21%\s*MwSt\s*:\s*(\d+[.,]\d{2})', re.IGNORECASE)
other_fees_regex = re.compile(r'(?:other fees|andere gebühren|otros cargos|Extra)\s*[:.]*\s*(\d+[.,]\d{2})', re.IGNORECASE)
category_regex = re.compile(r'Fast Food|Taxes et Service Compris', re.IGNORECASE)


def parse_with_textract(bucket, file):
    response = textract.analyze_document(
        Document={'S3Object': {'Bucket': bucket, 'Name': file}},
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

    receipt_text = '\n'.join(extracted_text)

    return parse_fields(receipt_text)


def parse_fields(text):
    merchant = merchant_regex.search(text)
    country = country_regex.search(text)
    invoice_number = invoice_number_regex.search(text)
    date = date_regex.search(text)
    currency = currency_regex.search(text)
    total_amount = total_amount_regex.search(text)
    vat_19 = vat_19_regex.search(text)
    vat_7 = vat_7_regex.search(text)
    vat_10 = vat_10_regex.search(text)
    vat_0 = vat_0_regex.search(text)
    vat_21 = vat_21_regex.search(text)
    other_fees = other_fees_regex.search(text)
    category = category_regex.search(text)

    # Log results of regex searches for debugging
    # print("store_name:", store_name.group(0) if store_name else "Not found")
    # print("country:", country.group(0) if country else "Not found")
    # print("invoice_number:", invoice_number.group(1) if invoice_number else "Not found")
    # print("date:", date.group(1) if date else "Not found")
    # print("currency:", currency.group(0) if currency else "Not found")
    # print("total_amount:", total_amount.group(1) if total_amount else "Not found")
    # print("vat_19:", vat_19.group(1) if vat_19 else "Not found")
    # print("vat_7:", vat_7.group(1) if vat_7 else "Not found")
    # print("vat_10:", vat_10.group(1) if vat_10 else "Not found")
    # print("vat_0:", vat_0.group(1) if vat_0 else "Not found")
    # print("vat_21:", vat_21.group(1) if vat_21 else "Not found")
    # print("other_fees:", other_fees.group(1) if other_fees else "Not found")
    # print("category:", category.group(0) if category else "Not found")

    data = {
        "merchant": merchant.group(0).strip() if merchant else "Unknown",
        "country": country.group(0).strip() if country else "Unknown",
        "invoice_number": invoice_number.group(1).strip() if invoice_number else "Unknown",
        "date": datetime.strptime(date.group(1), '%d.%m.%Y').strftime('%Y-%m-%d') if date else "Unknown",
        "currency": currency.group(0).strip() if currency else "Unknown",
        "total_amount": total_amount.group(1).replace(',', '.').strip() if total_amount else 0,
        "vat_0": vat_0.group(1).replace(',', '.').strip() if vat_0 else 0,
        "vat_7": vat_7.group(1).replace(',', '.').strip() if vat_7 else 0,
        "vat_10": vat_10.group(1).replace(',', '.').strip() if vat_10 else 0,
        "vat_19": vat_19.group(1).replace(',', '.').strip() if vat_19 else 0,
        "vat_21": vat_21.group(1).replace(',', '.').strip() if vat_21 else 0,
        "other_fees": other_fees.group(1).replace(',', '.').strip() if other_fees else 0,
        "category": "Fast Food" if category else "Unknown"
    }

    return data
