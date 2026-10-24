# CYPHER ’26 — two-minute pitch guide

Team: **Indian Avengers** · Product: **LoanMirror** · Theme 02

## Slide 1 — The hook (20 seconds)

"A loan offer might lead with a 12% annual interest rate. But that figure alone doesn't tell a borrower what will actually enter their bank account, or what they'll repay. We built LoanMirror to connect the advertisement to the terms — with evidence, not guesses."

## Slide 2 — The problem (20 seconds)

"In our synthetic example, a ₹10,000 loan deducts ₹590 in fees and tax before disbursement. The borrower receives ₹9,410, yet repays ₹10,200.66 over three months. The challenge isn't that different rates have different definitions; it's that the total cash flow is difficult to reconcile from separate documents."

## Slide 3 — The product (22 seconds)

"The user supplies an advertisement and loan terms, confirms extracted figures, and receives a transparent breakdown. When both documents state directly conflicting fees or rates, we flag that exact conflict and show the supporting text. We deliberately distinguish an omission from a contradiction."

## Slide 4 — Engineering (22 seconds)

"Our prototype extracts text from supported digital PDFs, maps relevant fields, asks the user to verify them, then calculates EMI and compares like-for-like terms deterministically. AI-assisted extraction is a future extension, not a dependency in the MVP. Every financial number can be reproduced."

## Slide 5 — Tested and limited (20 seconds)

"We generated 15 fictional advertisement-and-KFS pairs. All 15 scenario cases passed, alongside additional calculations and API checks — 22 automated tests in total. These are controlled synthetic tests, not a claim about real lender documents or market-wide accuracy. That distinction is intentional."

## Slide 6 — Execution / close (16 seconds)

"The eight-hour finale is scoped around ingestion, validation, explanation and a reliable live demonstration. Our goal isn't another EMI calculator. It's a borrower-facing evidence layer between what a loan promises and what the loan terms actually establish. LoanMirror: understand before you sign."

## Questions to rehearse

1. **Is this already in the market?** Yes, loan comparison and document intelligence both exist. Our narrower wedge is direct advertisement-to-KFS reconciliation with supporting citations, offline/local-friendly implementation and user-verified deterministic maths. We do not claim invention.
2. **Does an APR higher than nominal interest imply deception?** No. APR accounts for more charges. We do not flag this as misconduct; we only compare equivalent claims and explain cash flows.
3. **Is the AI running?** No machine-learning model is included in this scoped prototype. Rules and financial calculations are currently deterministic. Future extraction models may improve resilience to diverse templates.
4. **How accurate is PDF extraction?** It worked on 15/15 generated pairs. No real-document accuracy estimate is available; we use human confirmation to prevent silent errors.
5. **What prevents user data exposure?** The demo runs on the user's own local machine and does not call cloud AI services, but it has not undergone a production security audit. Avoid real customer data in demonstrations.
6. **What happens when a field is missing?** The UI exposes editable terms; the comparison status 'not claimed'/'unverified' avoids inventing a conclusion.
