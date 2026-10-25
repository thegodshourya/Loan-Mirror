from fastapi.testclient import TestClient
from server import app
client=TestClient(app)

def test_catalog():
    data=client.get('/api/scenarios')
    assert data.status_code==200
    assert len(data.json())==15

def test_extract_sample():
    result=client.post('/api/extract',data={'case_id':'03_fee_conflict'})
    assert result.status_code==200
    assert result.json()['terms']['processing_fee']==500
    assert result.json()['advertisement']['processing_fee']==0

def test_api_direct_mismatch():
    payload={'case_id':'03_fee_conflict','principal':10000,'annual_nominal_pct':12,'months':3,'processing_fee':500,'fee_tax':90}
    result=client.post('/api/analyze',data=payload)
    assert result.status_code==200
    data=result.json()
    assert data['advertisement']['processing_fee']==0
    assert data['derived']['net_disbursed']==9410
    assert data['derived']['total_repayment']==10200.66
    assert any(f['status']=='conflict' and f['field']=='Processing fee' for f in data['findings'])


def test_manual_edits_do_not_rewrite_document_evidence():
    payload={'case_id':'03_fee_conflict','principal':10000,'annual_nominal_pct':12,'months':3,'processing_fee':0,'fee_tax':0}
    response=client.post('/api/analyze',data=payload)
    assert response.status_code==200
    report=response.json()
    assert report['derived']['net_disbursed']==10000
    assert report['overrides']=={'processing_fee':0,'fee_tax':0}
    assert any(f['status']=='conflict' and f['field']=='Processing fee' for f in report['findings'])
    assert any(f['status']=='match' and f['field']=='Processing fee' for f in report['input_comparison'])


def test_upload_pair_and_reject_partial_or_invalid_uploads():
    from pathlib import Path
    root=Path(__file__).parents[1]/'samples'
    files={kind:(kind+'.pdf',(root/f'03_fee_conflict_{kind}.pdf').read_bytes(),'application/pdf') for kind in ('advertisement','kfs')}
    response=client.post('/api/extract',data={'case_id':'03_fee_conflict'},files=files)
    assert response.status_code==200
    assert response.json()['terms']['processing_fee']==500
    assert client.post('/api/extract',data={'case_id':'03_fee_conflict'},files={'kfs':files['kfs']}).status_code==400
    files['kfs']=('bad.pdf',b'not a PDF','application/pdf')
    assert client.post('/api/extract',data={'case_id':'03_fee_conflict'},files=files).status_code==400
    files['kfs']=('large.pdf',b'%PDF-'+b'0'*5_000_000,'application/pdf')
    assert client.post('/api/extract',data={'case_id':'03_fee_conflict'},files=files).status_code==400


def test_missing_extraction_is_not_fabricated():
    import pymupdf as fitz
    with fitz.open() as doc:
        doc.new_page().insert_text((72,72),'An unsupported loan document')
        raw=doc.tobytes()
    response=client.post('/api/extract',data={'case_id':'03_fee_conflict'},files={k:('empty.pdf',raw,'application/pdf') for k in ('advertisement','kfs')})
    assert response.status_code==200
    assert response.json()['terms']=={}


def test_health_and_sample_not_found():
    assert client.get('/healthz').json()['status']=='ok'
    assert client.get('/api/sample/missing/kfs').status_code==404
    assert client.get('/api/sample/03_fee_conflict/kfs').headers['content-type']=='application/pdf'


import pytest
@pytest.mark.parametrize('key,value',[('principal','nan'),('annual_nominal_pct','inf'),('processing_fee','nan'),('fee_tax',-1),('months',601),('months',1.5),('annual_nominal_pct',1001),('processing_fee',10000)])
def test_invalid_financial_inputs(key,value):
    payload={'case_id':'03_fee_conflict','principal':10000,'annual_nominal_pct':12,'months':3,'processing_fee':500,'fee_tax':90}
    payload[key]=value
    assert client.post('/api/analyze',data=payload).status_code in (400,422)


def test_frontend_assets_are_versioned_and_not_cached():
    import hashlib
    from pathlib import Path
    root=Path(__file__).parents[1]
    page=client.get('/compare')
    assert page.headers['cache-control']=='no-store'
    for name in ('app.js','i18n.js'):
        version=hashlib.sha256((root/name).read_bytes()).hexdigest()[:12]
        assert f'/{name}?v={version}' in page.text
        assert client.get('/'+name).headers['cache-control']=='no-store'
