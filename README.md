# LoanMirror

**See the cost behind a loan offer.** Compare an advertisement with its Key Facts Statement (KFS), check the extracted evidence, and calculate what the borrower receives and repays.

This replaces the original Recipient-Check / Blockscout concept. The GitHub repository can keep its current name; the application is LoanMirror.

## Run locally

Python 3.12 is recommended. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open port 8000 in your browser. Alternatively run `bash run_demo_mac_linux.sh`; Windows users can run `run_demo_windows.bat`.

## Demo in one minute

1. Use the default **03 Fee Conflict** example. All 15 sample pairs are fictional.
2. Open the sample advertisement (₹0 fee) and KFS (₹500 fee + ₹90 tax).
3. Review the extracted values and source evidence, then choose **Calculate & compare**.
4. Show ₹9,410 cash received, ₹10,200.66 scheduled repayments, and ₹790.66 borrowing cost on a ₹10,000 loan.
5. Show the processing-fee mismatch and exact source lines. Print/save the report as PDF or download its JSON data.
6. Switch to **01 Clean Match** to demonstrate that matching documents are reported consistently.

For custom documents, upload **both** digital-text PDFs, at most 5 MB and 50 pages each. Extract again after changing files. Missing values remain blank and require manual verification. Edited figures affect the calculation; extracted document findings remain separate, and the report records all overrides.

## Deploy on Render

1. Commit and push these files to your GitHub repository.
2. Sign in to Render, choose **New → Blueprint**, and connect that repository.
3. Render reads `render.yaml`. Review its web service and deploy it. No API keys, database, or environment secrets are required.
4. Wait until `/healthz` returns `{"status":"ok","service":"LoanMirror"}` on the assigned Render URL.
5. Open the deployed homepage and run the fee-conflict demo above. Confirm the values and PDF downloads before sharing the link.

If configuring a web service manually: use Python 3.12, build command `pip install -r requirements.txt`, start command `python -m uvicorn server:app --host 0.0.0.0 --port $PORT --limit-concurrency 20`, and health path `/healthz`. Leave the root directory blank because the app is at the repository root. Free-service availability and cold starts depend on Render's current plan. This is a Python web service, not a GitHub Pages static site.

## Docker

```sh
docker build -t loanmirror .
docker run --rm -p 8000:8000 loanmirror
```

The container runs as an unprivileged user and respects `PORT` (default 8000). On a public host, terminate HTTPS at the hosting platform or reverse proxy. A proxy request-body limit around 11 MB and rate limits are recommended for public uploads; the application also checks individual file size and PDF page count. No persistent volume is needed.

## Verification

```sh
.venv/bin/python -m pytest tests -q
```

The suite covers 15 PDF scenarios, financial formulas, source provenance after manual edits, missing fields, invalid monetary inputs, uploads, health checks, and API behavior. GitHub Actions runs it on pushes and pull requests. `requirements.txt` pins the tested dependencies.

## Scope and data handling

- Extraction uses deterministic patterns for the supplied layouts. Arbitrary lender formats and scanned PDFs may need manual entry; OCR is not included.
- EMI assumes fixed reducing-balance interest, nominal annual rate divided by 12, and equal month-end payments. Fees and tax are deducted upfront. Borrowing cost is total scheduled repayments minus net proceeds, **not regulatory APR**.
- Comparisons cover nominal rate, tenure and processing fee. An omitted promotional claim is not a contradiction or proof of deception.
- The app does not intentionally retain uploaded files or report data. Uploads travel to the server; multipart handling can use temporary files. There is no account system or document storage. Use fictional or redacted documents for the public demo.
- No external AI calls, lender verification, regulatory certification, or guarantee of hackathon results is claimed.

Pitch materials from the supplied package are in `docs/`. Their event and research claims are supplied reference material, not independently reverified here. The optional `generate_samples.py` script needs `reportlab` if you choose to regenerate fixtures; the checked-in PDFs need no regeneration.

## Validation in this workspace

35 automated tests passed, plus Chromium checks of the sample flow, manual edits, file-upload pairing, report downloads, print rendering and a 390 px mobile layout. The live HTTP calculation and health endpoint passed. Docker image download succeeded, but the image build could not install packages because this environment's Docker build network could not resolve the package index; the Docker deployment remains unverified. Render deployment requires your hosting account and has not been performed.
