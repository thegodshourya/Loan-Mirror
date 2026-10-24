"""Creates clearly labelled imaginary example documents. No real lender identity used."""
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
import json
from loanmirror.engine import LoanTerms,loan_math

CASES = [
('01_clean_match',10000,12,6,0,0,12,6,0),
('02_fee_not_advertised',10000,12,3,500,90,12,3,None),
('03_fee_conflict',10000,12,3,500,90,12,3,0),
('04_rate_conflict',20000,15,6,0,0,12,6,None),
('05_tenure_conflict',15000,10,9,250,45,10,6,None),
('06_fee_disclosed',12000,13,12,250,45,13,12,250),
('07_interest_not_advertised',7000,18,6,0,0,None,6,None),
('08_large_upfront_fee',6000,20,2,1000,180,20,2,None),
('09_zero_interest',12000,0,3,0,0,0,3,0),
('10_two_year_loan',85000,11.5,24,400,72,11.5,24,None),
('11_one_month_loan',5000,30,1,100,18,30,1,None),
('12_higher_principal',100000,9.9,12,1200,216,9.9,12,1200),
('13_rate_decimal_conflict',9000,17,4,0,0,16.5,4,None),
('14_no_fee_long_loan',25000,16,18,0,0,16,18,0),
('15_tenure_ad_mismatch',30000,14,12,0,0,14,10,None),
]

def make_pdf(path, heading, rows, note):
    c=Canvas(str(path), pagesize=(595,842)); W,H=595,842
    c.setFillColor(HexColor('#153134'));c.rect(0,H-126,W,126,fill=1,stroke=0)
    c.setFillColor(HexColor('#E8F4EE'));c.setFont('Helvetica-Bold',19);c.drawString(43,H-67,heading)
    c.setFont('Helvetica',10);c.drawString(43,H-94,'LOANMIRROR / FICTIONAL DEMO DOCUMENT')
    c.setFillColor(HexColor('#153134'));y=665
    for label,value in rows:
      c.setFont('Helvetica-Bold',11);c.drawString(45,y,label)
      c.setFont('Helvetica',12);c.drawString(230,y,str(value));y-=40
    c.setStrokeColor(HexColor('#B9CAC6'));c.line(45,y-10,550,y-10)
    c.setFont('Helvetica',9);c.setFillColor(HexColor('#425E5E'))
    c.drawString(45,90,note)
    c.drawString(45,70,'TRAINING SAMPLE ONLY / NOT A REAL LOAN OFFER OR KFS')
    c.save()


def main():
    dest=Path(__file__).parent/'samples';dest.mkdir(exist_ok=True)
    cases=[]
    for id,principal,rate,months,fee,tax,ad_rate,ad_months,ad_fee in CASES:
        t=LoanTerms(principal,rate,months,fee,tax);m=loan_math(t)
        ad_rows=[('Principal Amount:',f'INR {principal:,.2f}')]
        if ad_rate is not None: ad_rows.append(('Annual Nominal Interest:',f'{ad_rate:.2f}%'))
        if ad_months is not None: ad_rows.append(('Tenure:',f'{ad_months} months'))
        if ad_fee is not None: ad_rows.append(('Processing Fee:',f'INR {ad_fee:,.2f}'))
        make_pdf(dest/f'{id}_advertisement.pdf','DEMO / LOAN OFFER',ad_rows,'Advertising excerpt. It is not a KFS or a complete contract.')
        kfs_rows=[('Sanctioned Loan Amount:',f'INR {principal:,.2f}'),('Annual Nominal Interest:',f'{rate:.2f}%'),('Loan Tenure:',f'{months} months'),('Processing Fee:',f'INR {fee:,.2f}'),('Tax on Fee:',f'INR {tax:,.2f}'),('Net Disbursed:',f'INR {m.net_proceeds:,.2f}'),('Monthly Instalment:',f'INR {m.scheduled_emi:,.2f}')]
        make_pdf(dest/f'{id}_kfs.pdf','DEMO / LOAN TERMS',kfs_rows,'Simplified synthetic illustration, not a regulatory-compliant real KFS.')
        cases.append({'id':id,'principal':principal,'annual_nominal_pct':rate,'months':months,'processing_fee':fee,'fee_tax':tax,'ad_rate':ad_rate,'ad_months':ad_months,'ad_fee':ad_fee,'expected_emi':m.scheduled_emi,'expected_net':m.net_proceeds})
    (dest/'manifest.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    print(f'Generated {len(cases)} pairs of synthetic PDFs.')

if __name__=='__main__':main()
