"""Transparent cash-flow calculations and synthetic-demo loan comparisons.
Not a compliance determination, lender verification, or financial advice.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class LoanTerms:
    principal: float
    annual_nominal_pct: float
    months: int
    processing_fee: float = 0.0
    fee_tax: float = 0.0


@dataclass(frozen=True)
class LoanMath:
    scheduled_emi: float
    total_repayments: float
    net_proceeds: float
    borrowing_cost: float
    model_effective_annual_pct: float


def emi(principal: float, annual_nominal_pct: float, months: int) -> float:
    """Reducing-balance EMI using an assumed nominal annual rate / 12."""
    if (not all(math.isfinite(x) for x in (principal, annual_nominal_pct, months))
        or principal <= 0 or not isinstance(months, int) or not 1 <= months <= 600
        or not 0 <= annual_nominal_pct <= 1000):
        raise ValueError("Use a finite positive principal, 1–600 whole months and a nominal rate from 0–1000%")
    r = annual_nominal_pct / 1200.0
    if r == 0:
        return principal / months
    return principal * r / -math.expm1(-months * math.log1p(r))


def loan_math(terms: LoanTerms) -> LoanMath:
    if not all(math.isfinite(x) and x >= 0 for x in (terms.processing_fee, terms.fee_tax)):
        raise ValueError("Fees and taxes must be finite and nonnegative")
    e = emi(terms.principal, terms.annual_nominal_pct, terms.months)
    net = terms.principal - terms.processing_fee - terms.fee_tax
    if net <= 0:
        raise ValueError("Upfront fees must be less than the principal")
    # Periodic borrower IRR: proceeds now; assumed equal payments at end of each month.
    def net_pv(monthly_rate: float) -> float:
        return sum(e / (1 + monthly_rate) ** t for t in range(1, terms.months + 1))
    lo, hi = 0.0, 1.0
    while net_pv(hi) > net:
        hi *= 2
    for _ in range(100):
        mid = (lo + hi) / 2
        if net_pv(mid) > net:
            lo = mid
        else:
            hi = mid
    monthly = (lo + hi) / 2
    if not all(math.isfinite(x) for x in (e, e * terms.months, ((1 + monthly) ** 12 - 1) * 100)):
        raise ValueError("Amounts exceed supported calculation range")
    return LoanMath(
        scheduled_emi=e,
        total_repayments=e * terms.months,
        net_proceeds=net,
        borrowing_cost=e * terms.months - net,
        model_effective_annual_pct=((1 + monthly) ** 12 - 1) * 100,
    )


def evaluate_claims(ad: dict, kfs: dict) -> list[dict]:
    """Directly compare LIKE-FOR-LIKE fields; never equate nominal rate with APR."""
    output = []
    for field, label, unit in [
        ('annual_nominal_pct','Annual nominal interest','%'),
        ('months','Tenure',' months'),
        ('processing_fee','Processing fee',' INR'),
    ]:
        v_ad = ad.get(field)
        v_kfs = kfs.get(field)
        if v_ad is None:
            output.append({'status':'not_claimed','field':label,'detail':'Not stated in advertisement; no contradiction inferred.'})
        elif v_kfs is None:
            output.append({'status':'unverified','field':label,'detail':'Not found in KFS; verify manually.'})
        elif abs(float(v_ad)-float(v_kfs)) > 1e-6:
            output.append({'status':'conflict','field':label,'detail':f'Advertised {v_ad}{unit}; KFS {v_kfs}{unit}.'})
        else:
            output.append({'status':'match','field':label,'detail':f'Both documents state {v_kfs}{unit}.'})
    return output
