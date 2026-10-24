# Evidence and positioning — LoanMirror / CYPHER ’26

Research prepared October 24, 2026. Links should be checked before submitting.

## Official challenge and event

- Organiser-supplied `CYPHER_26_Problem_Statements_Bento.pdf`, page 2 (Theme 02: FinTech, Digital Commerce & Cyber Security), explicitly calls out *deceptive lending traps, online financial fraud* and transparent small-merchant financial security.
- The [Unstop listing](https://unstop.com/hackathons/cypher-digiweek-jc-bose-university-of-science-and-technology-ymca-faridabad-1771873/amp) requires Round 1 PPT to cover: **Problem Statement, Proposed Solution, Technical Feasibility, Innovation & Real-World Impact, Implementation Plan**. It states submission via **Unstop**, 25 Oct 2026, 11:59 PM IST, top 25 advance, eight-hour in-person finale on 29 Oct 2026.
- The event screenshot supplied by the team is a **HackBriven** page with completed registration and a *HackBriven* submission instruction. **Submission channel is unresolved.** Confirm through official event dashboard/organizer WhatsApp before submitting; do not assume registration on one portal entails a submission on the other.

## Regulator / real problem

- Reserve Bank of India, [Key Facts Statement (KFS) for Loans & Advances](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12663&Mode=0), circular RBI/2024-25/18, dated 15 April 2024. The KFS standardises key loan terms and total cost of credit through APR and amortisation details.
- RBI [Digital Lending Directions, 2025](https://www.rbi.org.in/), relevant to disclosures to borrowers and the Key Facts Statement. An [RBI-hosted 2022 digital lending guideline](https://systemhealth.rbi.org.in/Scripts/NotificationUser.aspx_Id%3D12382%26Mode%3D0.html) explains APR and KFS disclosure principles. Prefer the 2024/2025 regulations for contemporary framing; operational requirements depend on lender category and updated directions.
- RBI-hosted [microfinance master directions](https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D12256%282%29.html) explain KFS as standardised facts and distinguish APR as including interest and other charges. An APR different from the nominal interest is **not in itself fraud**. No claim that LoanMirror certifies RBI compliance is justified.

## Prior art / pressure test

- [MySmartCoPilot — Loan Comparison Calculator](https://mysmartcopilot.com/tools/loan-comparison-calculator/) already compares offers based on user-entered fees, interest and APR. Therefore LoanMirror cannot claim 'first tool to reveal hidden charges' or 'first true-cost calculator'.
- [Decode the Loans](https://www.decodetheloans.com/) publicly advertises a borrower-focused AI document analysis platform for loan agreements, charges, hidden clauses and loan comparisons. Therefore 'AI that reads loan agreements' **is not a defensible novelty claim**.
- [Fiscus](https://www.fiscus.ai/) performs lender-side loan document intelligence and traceable underwriting. This demonstrates document intelligence already exists in the market but targets a different user/workflow.

**Reasonable narrow differentiator for the hackathon:** a lightweight borrower-side *advertisement-to-KFS claim reconciliation* that classifies direct contradictions separately from missing promotional information; independent deterministic EMI and net disbursement figures; document evidence attached to each finding; human verification and local processing. This is a focused implementation/UX differentiator, not an invention or monopoly.

## Engineering evidence

- 15 pairs / 30 synthetically generated sample PDFs, in `prototype/samples/`.
- 22/22 pytest cases pass locally; see `test_results.txt`. These cover the generated documents, independent math fixtures, invalid inputs and FastAPI endpoints.
- HTML frontend and FastAPI backend. Manual verification step; deterministic parser for provided synthetic templates. **No general extraction accuracy, real-lender performance, human-user study, privacy compliance certification, or installed AI model claim has been established.**

## Synthetic math used in the deck

- Sanctioned principal = ₹10,000
- Nominal annual interest = 12%, fixed, monthly reducing balance; monthly rate 1%
- Term = 3 end-of-month payments
- Processing fee = ₹500; tax on processing fee = ₹90, deducted upfront
- Disbursed to borrower = ₹9,410
- Model EMI = ₹3,400.2211148146785
- Total model repayments = ₹10,200.663344444036
- Borrower cost over cash received = ₹790.663344444036

These figures are an illustration; in real lending, timing, amortization convention, third-party charges, taxes, repayment schedules and lender product terms can differ. **The borrower cost is not presented as an official APR.**
