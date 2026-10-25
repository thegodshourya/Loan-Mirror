"""LoanMirror API. Run with: python -m uvicorn server:app --port 8000."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from loanmirror.engine import LoanTerms, loan_math, evaluate_claims
from loanmirror.parser import read_pdf

ROOT = Path(__file__).parent
SAMPLE_ROOT = ROOT / 'samples'
SAMPLES = {case['id']: case for case in json.loads((SAMPLE_ROOT / 'manifest.json').read_text())}
MAX_REQUEST_BYTES = 10_500_000  # Two 5 MB PDFs plus form/multipart overhead.
PDF_TIMEOUT = 12
PDF_SLOTS = asyncio.Semaphore(1)  # One bounded worker per web process.
PDF_ERROR = 'Unable to read this PDF. Use an unlocked digital-text PDF of at most 50 pages.'


class RequestSizeLimit:
    """Bound the body before form parsing, including requests without Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        declared = headers.get(b'content-length', b'')
        if declared.isdigit() and int(declared) > MAX_REQUEST_BYTES:
            return await JSONResponse({'detail': 'Upload request is too large. Use PDFs up to 5 MB each.'}, status_code=413)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                return await JSONResponse({'detail': 'Upload request is too large. Use PDFs up to 5 MB each.'}, status_code=413)(scope, receive, send)
            body.extend(chunk)
            if not message.get('more_body', False):
                break
        delivered = False

        async def limited_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()

        await self.app(scope, limited_receive, send)


app = FastAPI(title='LoanMirror', version='1.1.0', docs_url=None, redoc_url=None)
app.add_middleware(RequestSizeLimit)


@app.middleware('http')
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith('/api/') or request.url.path in ('/', '/compare', '/app.js', '/i18n.js'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/healthz')
def health():
    return {'status': 'ok', 'service': 'LoanMirror'}


def render_page(filename):
    html = (ROOT / filename).read_text(encoding='utf8')
    for filename in ('i18n.js', 'app.js'):
        version = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()[:12]
        html = html.replace(f'src="/{filename}"', f'src="/{filename}?v={version}"')
    return html


@app.get('/', response_class=HTMLResponse)
def home():
    return render_page('welcome.html')


@app.get('/compare', response_class=HTMLResponse)
def compare():
    return render_page('index.html')


@app.get('/app.js')
def javascript():
    return FileResponse(ROOT / 'app.js', media_type='text/javascript')


@app.get('/i18n.js')
def translations():
    return FileResponse(ROOT / 'i18n.js', media_type='text/javascript')


@app.get('/api/scenarios')
def scenarios():
    return [{'id': name, 'label': name.replace('_', ' ').title()} for name in SAMPLES]


@app.get('/api/sample/{case_id}/{kind}')
def sample(case_id: str, kind: str):
    if case_id not in SAMPLES or kind not in ('advertisement', 'kfs'):
        raise HTTPException(404, 'Scenario not found')
    path = SAMPLE_ROOT / f'{case_id}_{kind}.pdf'
    return FileResponse(path, filename=path.name, media_type='application/pdf')


async def uploaded_pdf(upload: UploadFile):
    raw = await upload.read(5_000_001)
    if b'%PDF-' not in raw[:1024] or len(raw) > 5_000_000:
        raise HTTPException(400, 'Upload must be a PDF smaller than 5 MB')
    process = await asyncio.create_subprocess_exec(
        sys.executable, '-m', 'loanmirror.parser', cwd=ROOT,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        try:
            output, _ = await asyncio.wait_for(process.communicate(raw), timeout=PDF_TIMEOUT)
        except asyncio.TimeoutError:
            raise HTTPException(422, 'PDF processing took too long. Try a simpler digital-text PDF.')
        if process.returncode:
            raise HTTPException(422, PDF_ERROR)
        try:
            return json.loads(output)
        except (ValueError, UnicodeError):
            raise HTTPException(422, PDF_ERROR)
    finally:
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()


async def read_docs(case_id: str, advertisement: UploadFile | None, kfs: UploadFile | None):
    if case_id not in SAMPLES:
        raise HTTPException(404, 'Scenario not found')
    if (advertisement is None) != (kfs is None):
        raise HTTPException(400, 'Upload both documents together, or use a sample pair')
    if advertisement is None:
        ad, ad_ev = read_pdf(SAMPLE_ROOT / f'{case_id}_advertisement.pdf')
        terms, terms_ev = read_pdf(SAMPLE_ROOT / f'{case_id}_kfs.pdf')
    else:
        if PDF_SLOTS.locked():
            raise HTTPException(503, 'Document processing is busy. Please try again shortly.')
        async with PDF_SLOTS:
            ad, ad_ev = await uploaded_pdf(advertisement)
            terms, terms_ev = await uploaded_pdf(kfs)
    return ad, ad_ev, terms, terms_ev


@app.post('/api/extract')
async def extract(case_id: str = Form(...), advertisement: UploadFile | None = File(None), kfs: UploadFile | None = File(None)):
    ad, ad_ev, terms, terms_ev = await read_docs(case_id, advertisement, kfs)
    return {'advertisement': ad, 'ad_evidence': ad_ev, 'terms': terms, 'term_evidence': terms_ev}


@app.post('/api/analyze')
async def analyze(case_id: str = Form(...), principal: float = Form(...), annual_nominal_pct: float = Form(...), months: int = Form(...), processing_fee: float = Form(...), fee_tax: float = Form(...), advertisement: UploadFile | None = File(None), kfs: UploadFile | None = File(None)):
    effective = dict(principal=principal, annual_nominal_pct=annual_nominal_pct, months=months, processing_fee=processing_fee, fee_tax=fee_tax)
    try:
        result = loan_math(LoanTerms(**effective))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except OverflowError:
        raise HTTPException(400, 'Amounts exceed supported calculation range')
    ad, ad_ev, extracted, terms_ev = await read_docs(case_id, advertisement, kfs)
    return {
        'verified': effective, 'advertisement': ad,
        'derived': {'emi': round(result.scheduled_emi, 2), 'total_repayment': round(result.total_repayments, 2),
                    'net_disbursed': round(result.net_proceeds, 2), 'borrowing_cost': round(result.borrowing_cost, 2)},
        'findings': evaluate_claims(ad, extracted), 'input_comparison': evaluate_claims(ad, effective),
        'extracted': extracted, 'overrides': {key: value for key, value in effective.items() if extracted.get(key) != value},
        'ad_evidence': ad_ev, 'kfs_evidence': terms_ev,
        'notice': 'Borrowing cost is not the regulatory APR. A missing promotional claim does not prove deception.',
    }
