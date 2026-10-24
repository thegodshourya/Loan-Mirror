from pathlib import Path
import json,math
import pytest
from loanmirror.engine import LoanTerms,loan_math,evaluate_claims,emi
from loanmirror.parser import read_pdf
BASE=Path(__file__).parents[1] / 'samples'
CASES=json.loads((BASE/'manifest.json').read_text())

@pytest.mark.parametrize('case',CASES,ids=[c['id'] for c in CASES])
def test_synthetic_pdf_scenario(case):
    ad,_=read_pdf(BASE/f"{case['id']}_advertisement.pdf")
    kfs,evidence=read_pdf(BASE/f"{case['id']}_kfs.pdf")
    for key in ['principal','annual_nominal_pct','months','processing_fee','fee_tax']:
        assert math.isclose(kfs[key],case[key],abs_tol=1e-6), f'{case["id"]}: {key}'
        assert evidence[key]
    if case['ad_rate'] is not None: assert math.isclose(ad['annual_nominal_pct'],case['ad_rate'])
    else: assert 'annual_nominal_pct' not in ad
    if case['ad_fee'] is not None: assert math.isclose(ad['processing_fee'],case['ad_fee'])
    else: assert 'processing_fee' not in ad
    math_result=loan_math(LoanTerms(**{k:kfs[k] for k in ['principal','annual_nominal_pct','months','processing_fee','fee_tax']}))
    assert math.isclose(math_result.scheduled_emi,case['expected_emi'],rel_tol=1e-12)
    assert math.isclose(math_result.net_proceeds,case['expected_net'],rel_tol=1e-12)
    outcome=evaluate_claims(ad,kfs)
    expected={field for field,v in [('Annual nominal interest',case['ad_rate'] if case['ad_rate'] is not None and case['ad_rate']!=case['annual_nominal_pct'] else None),('Tenure',case['ad_months'] if case['ad_months']!=case['months'] else None),('Processing fee',case['ad_fee'] if case['ad_fee'] is not None and case['ad_fee']!=case['processing_fee'] else None)] if v is not None}
    assert {o['field'] for o in outcome if o['status']=='conflict'}==expected

@pytest.mark.parametrize('principal,rate,n,result',[(12000,0,12,1000),(10000,12,3,3400.2211148146785),(6000,20,2,3075.20661157025)])
def test_emi_formula(principal,rate,n,result):
    assert math.isclose(emi(principal,rate,n),result,rel_tol=1e-6)

def test_reject_invalid_inputs():
    with pytest.raises(ValueError): emi(-1,12,12)
    with pytest.raises(ValueError): loan_math(LoanTerms(1000,12,1,1500,0))


def test_small_rate_long_term_and_high_fee_irr():
    assert math.isclose(emi(12000,1e-12,12),1000,rel_tol=1e-10)
    assert math.isfinite(emi(10000,1000,600))
    result=loan_math(LoanTerms(1000,0,1,900,0))
    assert math.isclose(result.model_effective_annual_pct,(10**12-1)*100,rel_tol=1e-10)
    with pytest.raises(ValueError): loan_math(LoanTerms(1000,12,12,-10,0))
