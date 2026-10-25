"""Regression cases for the public-demo audit; no calls to the deployed service."""
import asyncio
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path
import pytest
import pymupdf
from fastapi.testclient import TestClient
import server
from loanmirror.parser import extract_fields, read_pdf
from loanmirror.engine import LoanTerms, loan_math, emi

client=TestClient(server.app)
base=Path(__file__).parents[1]/'samples'
payload=dict(case_id='03_fee_conflict',principal=10000,annual_nominal_pct=12,months=3,processing_fee=500,fee_tax=90)

@pytest.mark.parametrize('text,key',[
 ('Processing Fee: INR 2%','processing_fee'),('Principal Amount: INR 1 lakh','principal'),
 ('Processing Fee: INR 10,00','processing_fee'),('Processing Fee: INR 1.2.3','processing_fee'),
 ('Processing Fee: INR -500','processing_fee'),('Loan Tenure: 12 months extra','months'),
 ('Annual Nominal Interest: 12.3.4%','annual_nominal_pct'),('Processing Fee: INR '+'9'*400,'processing_fee'),
 ('Processing Fee: INR 500\nProcessing Fee: INR 900','processing_fee'),
 ('Processing Fee: INR 500\nProcessing Fee: INR 2%','processing_fee')])
def test_unsupported_or_ambiguous_values_are_not_guessed(text,key):
 fields,evidence=extract_fields(text)
 assert key not in fields
 assert evidence[key]

@pytest.mark.parametrize('value,expected',[('1,00,000.50',100000.5),('100,000.50',100000.5),('100000.50',100000.5),('0',0)])
def test_supported_amounts(value,expected):
 assert extract_fields('Processing Fee: INR '+value)[0]['processing_fee']==expected


def test_identical_duplicate_is_valid():
 assert extract_fields('Processing Fee: INR 500\nProcessing Fee: INR 500.00')[0]['processing_fee']==500

@pytest.mark.parametrize('principal,rate,months',[(.01,0,1),(10000,12,3),(12500.75,7.345,60),(100000,0.000001,600),(1e12,1000,600)])
def test_emi_against_independent_decimal_formula(principal,rate,months):
 with localcontext() as ctx:
  ctx.prec=60
  p=Decimal(str(principal));r=Decimal(str(rate))/1200
  expected=p/months if r==0 else p*r*(1+r)**months/((1+r)**months-1)
 assert math.isclose(emi(principal,rate,months),float(expected),rel_tol=1e-12)


def test_high_fee_long_loan_and_cents():
 result=loan_math(LoanTerms(10000,12,600,9999.99,0))
 assert result.net_proceeds==.01 and math.isfinite(result.model_effective_annual_pct)
 assert loan_math(LoanTerms(.03,0,1,.01,.01)).net_proceeds==.01

@pytest.mark.parametrize('key,value',[('principal',.001),('processing_fee',.001),('fee_tax',.001),('principal',1e13),('principal',float('inf')),('processing_fee',float('nan'))])
def test_invalid_money_is_rejected(key,value):
 terms=dict(principal=10000,annual_nominal_pct=12,months=3,processing_fee=500,fee_tax=90);terms[key]=value
 with pytest.raises(ValueError):loan_math(LoanTerms(**terms))

@pytest.mark.parametrize('case',json.loads((base/'manifest.json').read_text()),ids=lambda c:c['id'])
def test_all_sample_pairs_through_api(case):
 extract=client.post('/api/extract',data={'case_id':case['id']})
 assert extract.status_code==200
 result=client.post('/api/analyze',data=dict(case_id=case['id'],**extract.json()['terms']))
 assert result.status_code==200
 assert result.json()['derived']['net_disbursed']==round(case['expected_net'],2)
 assert result.json()['derived']['emi']==round(case['expected_emi'],2)


def pdf(pages=1,encrypted=False):
 with pymupdf.open() as doc:
  for _ in range(pages):doc.new_page().insert_text((72,72),'Processing Fee: INR 500')
  return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='test') if encrypted else doc.tobytes()

@pytest.mark.parametrize('raw',[b'%PDF-garbage',pdf(51),pdf(encrypted=True)])
def test_invalid_pdfs_fail_cleanly(raw):
 result=client.post('/api/extract',data={'case_id':'03_fee_conflict'},files={k:('test.pdf',raw,'application/pdf') for k in ['advertisement','kfs']})
 assert result.status_code==422
 assert 'Traceback' not in result.text
 assert client.get('/healthz').status_code==200


def test_body_limit_before_parser(monkeypatch):
 monkeypatch.setattr(server,'MAX_REQUEST_BYTES',100)
 result=client.post('/api/extract',content=b'x'*101)
 assert result.status_code==413
 assert result.headers['cache-control']=='no-store'


def test_streamed_body_limit_without_content_length(monkeypatch):
 monkeypatch.setattr(server,'MAX_REQUEST_BYTES',100)
 async def exercise():
  called=False
  async def inner(scope,receive,send):
   nonlocal called;called=True
  messages=iter([{'type':'http.request','body':b'x'*60,'more_body':True},{'type':'http.request','body':b'x'*60,'more_body':False}]);sent=[]
  async def receive():return next(messages)
  async def send(message):sent.append(message)
  await server.RequestSizeLimit(inner)({'type':'http','method':'POST','headers':[]},receive,send)
  assert not called and sent[0]['status']==413
 asyncio.run(exercise())


def test_worker_timeout_kills_process(monkeypatch):
 processes=[]
 original=asyncio.create_subprocess_exec
 async def slow(*args,**kwargs):
  proc=await original(server.sys.executable,'-c','import time;time.sleep(60)',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE)
  processes.append(proc);return proc
 monkeypatch.setattr(server.asyncio,'create_subprocess_exec',slow)
 monkeypatch.setattr(server,'PDF_TIMEOUT',.05)
 raw=pdf()
 result=client.post('/api/extract',data={'case_id':'03_fee_conflict'},files={k:('test.pdf',raw,'application/pdf') for k in ['advertisement','kfs']})
 assert result.status_code==422 and 'too long' in result.json()['detail']
 assert processes[0].returncode is not None
 assert client.get('/healthz').status_code==200


def test_busy_worker_fails_fast(monkeypatch):
 monkeypatch.setattr(server,'PDF_SLOTS',asyncio.Semaphore(0))
 raw=pdf()
 result=client.post('/api/extract',data={'case_id':'03_fee_conflict'},files={k:('test.pdf',raw,'application/pdf') for k in ['advertisement','kfs']})
 assert result.status_code==503


def test_home_and_compare_routes():
 home=client.get('/');compare=client.get('/compare')
 assert home.status_code==compare.status_code==200
 assert 'How it works' in home.text and 'href="/compare"' in home.text
 assert 'id="analyze"' in compare.text and 'id="analyze"' not in home.text
 assert "object-src 'none'" in home.headers['content-security-policy']


def test_cents_api_and_untrusted_html_as_evidence():
 result=client.post('/api/analyze',data={**payload,'principal':10000.5,'processing_fee':500.25,'fee_tax':90.05})
 assert result.status_code==200 and result.json()['derived']['net_disbursed']==9410.2
 fields,evidence=extract_fields('Processing Fee: INR 500 <script>alert(1)</script>')
 assert fields=={} and '<script>' in evidence['processing_fee']


def test_pdf_worker_keeps_health_responsive_and_limits_concurrency(monkeypatch):
    import httpx
    original=asyncio.create_subprocess_exec
    async def exercise():
        started=asyncio.Event()
        async def slow(*args,**kwargs):
            process=await original(server.sys.executable,'-c','import time; time.sleep(.25); print("[{},{}]")',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE)
            started.set()
            return process
        monkeypatch.setattr(server.asyncio,'create_subprocess_exec',slow)
        monkeypatch.setattr(server,'PDF_SLOTS',asyncio.Semaphore(1))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url='http://test') as session:
            files={k:('test.pdf',b'%PDF-test','application/pdf') for k in ('advertisement','kfs')}
            first=asyncio.create_task(session.post('/api/extract',data={'case_id':'03_fee_conflict'},files=files))
            await started.wait()
            health=await session.get('/healthz')
            second=await session.post('/api/extract',data={'case_id':'03_fee_conflict'},files=files)
            assert health.status_code==200 and second.status_code==503
            assert (await first).status_code==200
    asyncio.run(exercise())
