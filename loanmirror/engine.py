"""Transparent cash-flow calculations and synthetic-demo loan comparisons.
Not a compliance determination, lender verification, or financial advice.
"""
from dataclasses import dataclass
import math
from decimal import Decimal

MAX_AMOUNT = 1_000_000_000_000


def validate_amount(value: float, *, positive=False):
    if not math.isfinite(value) or not 0 <= value <= MAX_AMOUNT or (positive and value == 0):
        raise ValueError("Amounts must be finite, nonnegative and at most INR 1 trillion; principal must be positive")
    amount = Decimal(str(value))
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Use at most two decimal places for monetary amounts")
    return amount



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
    validate_amount(principal, positive=True)
    r = annual_nominal_pct / 1200.0
    if r == 0:
        return principal / months
    return principal * r / -math.expm1(-months * math.log1p(r))


def loan_math(terms: LoanTerms) -> LoanMath:
    principal = validate_amount(terms.principal, positive=True)
    fee = validate_amount(terms.processing_fee)
    tax = validate_amount(terms.fee_tax)
    e = emi(terms.principal, terms.annual_nominal_pct, terms.months)
    net = float(principal - fee - tax)
    if net <= 0:
        raise ValueError("Upfront fees must be less than the principal")
    # Stable annuity PV avoids exponent overflow on long, high-fee loans.
    def net_pv(monthly_rate: float) -> float:
        if monthly_rate == 0:
            return e * terms.months
        return e * (-math.expm1(-terms.months * math.log1p(monthly_rate)) / monthly_rate)
    # A perpetuity at e/net has PV=net; the finite annuity has smaller PV.
    lo, hi = 0.0, max(1.0, e / net)
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
            output.append({'status':'not_claimed','field':label,'detail':'No comparable claim extracted from advertisement; no contradiction inferred.'})
        elif v_kfs is None:
            output.append({'status':'unverified','field':label,'detail':'No comparable value extracted from KFS; verify manually.'})
        elif abs(float(v_ad)-float(v_kfs)) > 1e-6:
            output.append({'status':'conflict','field':label,'detail':f'Advertised {v_ad}{unit}; KFS {v_kfs}{unit}.'})
        else:
            output.append({'status':'match','field':label,'detail':f'Both documents state {v_kfs}{unit}.'})
    return output
