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

Open port 8000 in your browser. The welcome page explains the product; choose **Start comparing** to open `/compare`. Alternatively run `bash run_demo_mac_linux.sh`; Windows users can run `run_demo_windows.bat`.

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

## Interface languages

Use the language selector in the header to choose English, Hindi or Marathi. The choice is remembered on this browser when local storage is available. Switching language preserves the entered terms and current report. Labels, scenarios, application validation messages, findings and the printable report are translated locally, without any translation service or API key. Browser-native file-picker controls follow the browser/OS language.

Source PDFs and verbatim evidence remain in their original language. This feature does not add extraction support for Hindi or Marathi PDFs. Downloaded JSON retains stable API field names and includes `interface_language`.

Browser regression check (with Playwright and its Chromium installed): start the app on port 8001, then run `node tests/browser_languages.cjs`. Set `BASE_URL` or `CHROMIUM_PATH` for another URL or an installed Chromium executable.

Language loading resilience: the homepage uses content-versioned script URLs and no-store responses to avoid mixing scripts across deployments. The language selector initializes independently of calculation code and remains available while requests load.

## Refined design update

The web interface now follows the Superdesign concept: forest green and ivory, serif headings, a clearly labelled fictional example, grouped form controls, and a high-contrast cost summary. The layout was checked in English, Hindi and Marathi at widths of 320, 390, 768 and 1440 pixels. All display copy remains local and the app loads no external font or design framework. Original PDF excerpts remain verbatim.

The visual concept is available at https://superdesign.dev/teams/b71eabff-859c-4b23-bba3-ce85f044a439/projects/00be3879-6092-470a-8947-acc3fe4cba87 . This is the design canvas; the working implementation is in this repository.

## Motion

Language switches update text immediately, followed by a 240 ms, 2 px blur/fade. Rapid switches cancel the previous effect. Sections reveal once on entry, result cards appear in sequence, and the cost bar draws in. Layered summary-card shadows, hover/press feedback and a request-only loading pulse complete the effect. All motion respects reduced-motion preferences; active animations are cancelled before printing. No animation library or external asset is needed.

With the app running, use `BASE_URL=http://127.0.0.1:8004 node tests/browser_motion.cjs` to verify rapid switching, data preservation, reduced-motion behavior and print cleanup (Playwright required).

## Public-demo reliability update

The homepage (`/`) now explains LoanMirror, offers English/Hindi/Marathi selection and retains the layered animations. The comparison workflow lives at `/compare`; the logo returns to the welcome page.

PDF fields are extracted only when their complete units and values match supported layouts. Percentage fees, unsupported suffixes, invalid comma grouping and conflicting repeated fields remain blank. Their original lines are retained for manual review. A missing extracted claim is described as unverified extraction rather than proof that the source never stated it.

Amounts support paise (two decimal places), up to INR 1 trillion; tenures are 1–600 whole months and nominal annual rates 0–1000%. Uploaded PDF parsing uses a separate killable process: one worker at a time, 12-second wall timeout, and Unix limits of 256 MB address space and 8 CPU seconds. Requests are capped at 10.5 MB total; each PDF remains capped at 5 MB, 50 pages and 250,000 extracted characters. Busy workers return a retryable response. These bounds improve resilience; they are not a security certification or full operating-system sandbox.

Browser requests time out after 45 seconds, report service/network errors clearly and offer **Try again**. Reports include the source, generation time and verified terms so printed reports preserve the calculation inputs.

Run the Python suite with `python -m pytest tests -q`. For browser checks, start port 8006 and run (with Playwright installed):

```sh
BASE_URL=http://127.0.0.1:8006/compare node tests/browser_languages.cjs
BASE_URL=http://127.0.0.1:8006/compare node tests/browser_motion.cjs
BASE_URL=http://127.0.0.1:8006 node tests/browser_public.cjs
```

Set `CHROMIUM_PATH` when using an existing Chromium executable. See `AUDIT.md` for the completed checks and limitations.
