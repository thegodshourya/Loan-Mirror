# LoanMirror public-demo audit — 25 October 2026

## Reproduced defects and fixes

- A percentage fee (`INR 2%`) was extracted as a flat INR 2. Unsupported units now remain unfilled with their evidence retained.
- `INR 1 lakh` was extracted as INR 1. Extraction now requires the complete supported amount format.
- Conflicting repeated fields silently selected the first value. Ambiguous fields now require manual verification.
- Very long digit strings produced infinity and could fail JSON serialization. Extraction now rejects nonfinite and out-of-range values.
- A 600-month loan with high upfront fees overflowed in the IRR calculation. A stable annuity present-value formula now handles it.
- Monetary form inputs rejected valid paise amounts. Browser and server validation now agree on two-decimal amounts.
- Fetch requests could leave the tool busy indefinitely or show raw JSON parsing errors for an HTML service error. Requests now time out, show translated recovery messages, and support retry.
- Upload limits were checked only after multipart parsing and PDF parsing could block the main event loop. Total request limits now run before form parsing; uploaded PDFs run in a bounded, killable subprocess.
- Printed reports omitted a concise summary of the verified inputs. Reports now retain those inputs, source and generation time.

## Product changes

- Separate multilingual welcome page at `/` and comparison tool at `/compare`.
- Existing layered animations and language preferences are retained across navigation.
- Script content versioning and cache controls remain enabled.
- A restrictive content security policy protects the application pages. No new runtime dependencies were added.

## Completed local verification

- **88 Python tests passed**: all 15 sample scenarios, API routes, PDF upload handling, unsupported and conflicting fields, independent high-precision financial checks, fractional amounts, invalid values, upload request limits with and without Content-Length, encrypted/corrupt/oversized-page PDFs, worker timeout cleanup, concurrency and health responsiveness.
- **Three browser suites passed**: languages, animation behavior and public workflow recovery.
- **24 responsive combinations passed**: two pages × three languages × four widths (320, 390, 768 and 1366 px).
- Browser checks cover retry after HTML errors, failed startup recovery, simulated request timeout, language persistence across navigation, fractional amounts, report inputs in print, original evidence preservation, reduced motion and rapid language changes.
- Python dependency consistency, JavaScript syntax and Git whitespace checks passed.
- One test-library deprecation warning remains about Starlette's httpx test-client integration; no tests failed.

## Limits

These checks do not establish a bug-free or compliance-certified product. Real-world lender formats remain outside general-purpose extraction support; scanned PDFs still need OCR, which is not included. Resource-limited subprocesses are not full OS sandboxes. Large-scale load testing, a professional security audit, regulatory APR certification and public-host verification of this new release were not performed. Native file pickers follow browser/OS language. No changes were pushed or deployed automatically.
