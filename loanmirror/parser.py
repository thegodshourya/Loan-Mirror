"""Deterministic extractor for the included demo PDFs, NOT a general OCR engine."""
import re
from pathlib import Path
import pymupdf as fitz

PATTERNS = {
    'principal':r'(?im)^\s*(?:Principal Amount|Sanctioned Loan Amount)\s*:\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
    'annual_nominal_pct':r'(?im)^\s*Annual Nominal Interest\s*:\s*([\d.]+)\s*%',
    'months':r'(?im)^\s*(?:Tenure|Loan Tenure)\s*:\s*(\d+)\s*months?',
    'processing_fee':r'(?im)^\s*Processing Fee\s*:\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
    'fee_tax':r'(?im)^\s*Tax on Fee\s*:\s*(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)',
}

def extract_text(pdf_source):
    if isinstance(pdf_source,(str,Path)):
        doc=fitz.open(str(pdf_source))
    else:
        doc=fitz.open(stream=pdf_source,filetype='pdf')
    with doc:
        if doc.needs_pass or len(doc) > 50:
            raise ValueError("Use an unlocked PDF of at most 50 pages")
        pages=[page.get_text(sort=True) for page in doc]
    return '\n'.join(pages)

def extract_fields(text:str):
    fields={}
    evidence={}
    for key,pattern in PATTERNS.items():
        match=re.search(pattern,text)
        if match:
            val=float(match.group(1).replace(',',''))
            fields[key]=int(val) if key=='months' else val
            evidence[key]=match.group(0).strip()
    return fields,evidence


def read_pdf(path_or_bytes):
    return extract_fields(extract_text(path_or_bytes))
