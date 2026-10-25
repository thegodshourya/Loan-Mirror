"""Conservative extraction for supported digital-text layouts; no OCR or inferred units."""
import math
import re
from pathlib import Path
import pymupdf as fitz

MAX_PAGES = 50
MAX_TEXT = 250_000
LABELS = {
    'principal': r'Principal Amount|Sanctioned Loan Amount',
    'annual_nominal_pct': r'Annual Nominal Interest',
    'months': r'Tenure|Loan Tenure',
    'processing_fee': r'Processing Fee',
    'fee_tax': r'Tax on Fee',
}
# Accept ungrouped, Western-grouped and Indian-grouped rupee amounts, in cents.
MONEY = re.compile(r'(?:INR|Rs\.?|₹)?[ \t]*((?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d{1,2})?)', re.I)
RATE = re.compile(r'(\d+(?:\.\d+)?)\s*%')
MONTHS = re.compile(r'(\d+)\s*months?', re.I)


def extract_text(pdf_source):
    doc = fitz.open(str(pdf_source)) if isinstance(pdf_source, (str, Path)) else fitz.open(stream=pdf_source, filetype='pdf')
    with doc:
        if doc.needs_pass or len(doc) > MAX_PAGES:
            raise ValueError('Use an unlocked PDF of at most 50 pages')
        pages, length = [], 0
        for page in doc:
            text = page.get_text(sort=True)
            length += len(text)
            if length > MAX_TEXT:
                raise ValueError('PDF contains too much text')
            pages.append(text)
    return '\n'.join(pages)


def extract_fields(text: str):
    fields, evidence = {}, {}
    for key, labels in LABELS.items():
        matches = list(re.finditer(rf'^[ \t]*(?:{labels})[ \t]*:[ \t]*([^\r\n]*)$', text, re.M | re.I))
        if not matches:
            continue
        # Preserve even unsupported or conflicting lines so users can inspect them.
        evidence[key] = '\n'.join(dict.fromkeys(match.group(0).strip() for match in matches))
        values = []
        pattern = RATE if key == 'annual_nominal_pct' else MONTHS if key == 'months' else MONEY
        for match in matches:
            value_match = pattern.fullmatch(match.group(1).strip())
            if not value_match:
                break
            raw = value_match.group(1).replace(',', '')
            if len(raw) > 32:
                break
            value = float(raw)
            upper = 1000 if key == 'annual_nominal_pct' else 600 if key == 'months' else 1_000_000_000_000
            if not math.isfinite(value) or value > upper or (key in ('principal', 'months') and value <= 0):
                break
            values.append(int(value) if key == 'months' else value)
        # A repeated field with different amounts is ambiguous, never silently take the first.
        if len(values) == len(matches) and len(set(values)) == 1:
            fields[key] = values[0]
    return fields, evidence


def read_pdf(path_or_bytes):
    return extract_fields(extract_text(path_or_bytes))


if __name__ == '__main__':
    # Uploaded files run in a killable process. Unix limits also bound native PDF decoding.
    import json
    import sys
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        except ImportError:  # Windows still gets the parent process wall-time limit.
            pass
        raw = sys.stdin.buffer.read(5_000_001)
        if len(raw) > 5_000_000:
            raise ValueError('PDF too large')
        fields, evidence = read_pdf(raw)
        print(json.dumps([fields, evidence], allow_nan=False))
    except Exception:
        sys.exit(2)
