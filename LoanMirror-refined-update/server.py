"""Run: python -m uvicorn server:app --host 127.0.0.1 --port 8000
Proof of concept. Processes documents in memory; synthetic test PDFs only.
"""
from pathlib import Path
import json
import hashlib
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from loanmirror.engine import LoanTerms, loan_math, evaluate_claims
from loanmirror.parser import read_pdf

ROOT=Path(__file__).parent
SAMPLE_ROOT=ROOT/'samples'
SAMPLES={c['id']:c for c in json.loads((SAMPLE_ROOT/'manifest.json').read_text())}
app=FastAPI(title='LoanMirror',version='1.0.0')

@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith('/api/') or request.url.path in ('/', '/app.js', '/i18n.js'):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.get('/healthz')
def health():
    return {'status': 'ok', 'service': 'LoanMirror'}

@app.get('/', response_class=HTMLResponse)
def home():
    html = (ROOT/'index.html').read_text(encoding='utf8')
    for filename in ('i18n.js', 'app.js'):
        version = hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()[:12]
        html = html.replace(f'src="/{filename}"', f'src="/{filename}?v={version}"')
    return html

@app.get('/app.js')
def javascript():
    return FileResponse(ROOT/'app.js', media_type='text/javascript')

@app.get('/i18n.js')
def translations():
    return FileResponse(ROOT/'i18n.js', media_type='text/javascript')

@app.get('/api/scenarios')
def scenarios():
    return [{'id':name,'label':name.replace('_',' ').title()} for name in SAMPLES]

@app.get('/api/sample/{case_id}/{kind}')
def sample(case_id:str,kind:str):
    if case_id not in SAMPLES or kind not in ('advertisement','kfs'):
        raise HTTPException(404,'Scenario not found')
    path=SAMPLE_ROOT/f'{case_id}_{kind}.pdf'
    return FileResponse(path,filename=path.name,media_type='application/pdf')

async def input_pdf(up:UploadFile|None,case_id:str,which:str):
    if up is None:
        return SAMPLE_ROOT/f'{case_id}_{which}.pdf'
    raw=await up.read(5_000_001)
    if not raw.startswith(b'%PDF-') or len(raw)>5_000_000:
        raise HTTPException(400,'Upload must be a PDF smaller than 5 MB')
    return raw

async def read_docs(case_id:str,advertisement:UploadFile|None,kfs:UploadFile|None):
    if case_id not in SAMPLES: raise HTTPException(404,'Scenario not found')
    if (advertisement is None) != (kfs is None):
        raise HTTPException(400,'Upload both documents together, or use a sample pair')
    try:
        ad,ad_ev=read_pdf(await input_pdf(advertisement,case_id,'advertisement'))
        terms,terms_ev=read_pdf(await input_pdf(kfs,case_id,'kfs'))
        return ad,ad_ev,terms,terms_ev
    except HTTPException:raise
    except Exception:raise HTTPException(422,'Unable to read this PDF. Use an unlocked digital-text PDF.')

@app.post('/api/extract')
async def extract(case_id:str=Form(...),advertisement:UploadFile|None=File(None),kfs:UploadFile|None=File(None)):
    ad,ad_ev,terms,terms_ev=await read_docs(case_id,advertisement,kfs)
    return {'advertisement':ad,'ad_evidence':ad_ev,'terms':terms,'term_evidence':terms_ev}

@app.post('/api/analyze')
async def analyze(case_id:str=Form(...),principal:float=Form(...),annual_nominal_pct:float=Form(...),months:int=Form(...),processing_fee:float=Form(...),fee_tax:float=Form(...),advertisement:UploadFile|None=File(None),kfs:UploadFile|None=File(None)):
    ad,ad_ev,extracted,terms_ev=await read_docs(case_id,advertisement,kfs)
    if principal<=0 or annual_nominal_pct<0 or months<1 or months>600 or processing_fee<0 or fee_tax<0:
        raise HTTPException(400,'Invalid verified numbers')
    effective={'principal':principal,'annual_nominal_pct':annual_nominal_pct,'months':months,'processing_fee':processing_fee,'fee_tax':fee_tax}
    try:
        m=loan_math(LoanTerms(**effective))
    except (ValueError, OverflowError) as exc:raise HTTPException(400,str(exc))
    return {'verified':effective, 'advertisement':ad,
            'derived':{'emi':round(m.scheduled_emi,2),'total_repayment':round(m.total_repayments,2),
                       'net_disbursed':round(m.net_proceeds,2),'borrowing_cost':round(m.borrowing_cost,2)},
            'findings':evaluate_claims(ad,extracted), 'input_comparison':evaluate_claims(ad,effective),
            'extracted':extracted, 'overrides':{k:v for k,v in effective.items() if extracted.get(k) != v},'ad_evidence':ad_ev,'kfs_evidence':terms_ev,
            'notice':'Synthetic prototype. Borrowing cost is not the regulatory APR. A missing promotional fee does not prove deception.'}
