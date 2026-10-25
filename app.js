const $ = id => document.getElementById(id);
const keys = ['principal', 'annual_nominal_pct', 'months', 'processing_fee', 'fee_tax'];
const money = n => '₹' + Number(n).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const REQUEST_TIMEOUT_MS = 45000;
let retryAction = null;
function offerRetry(action) { retryAction = action; $('retry').hidden = false; }
let lastStatus = {key: 'Select a sample to begin.', values: {}};
let currentCase = '03_fee_conflict', extracted = false, report = null;
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) {
    if (tag !== 'pre' && translations[text]) el.dataset.i18n = text;
    el.textContent = tag === 'pre' ? text : t(text);
  }
  if (className) el.className = className;
  return el;
}
function status(key, values = {}) {
  lastStatus = {key, values};
  $('status').removeAttribute('data-i18n');
  $('status').textContent = t(key, {...values, ...(values.error ? {error: t(values.error)} : {})});
}
function invalidate(clearFields = false) {
  report = null; $('results').hidden = true;
  if (clearFields) {
    extracted = false;
    keys.forEach(k => $(k).value = '');
    $('source-evidence').replaceChildren();
  }
  $('analyze').disabled = !extracted;
}
function busy(value) {
  if (value) $('retry').hidden = true;
  document.querySelector('.workspace').classList.toggle('is-busy', value);
  $('status').setAttribute('aria-busy', String(value));
  document.querySelectorAll('input, select:not(#language), button').forEach(el => el.disabled = value);
  if (!value) $('analyze').disabled = !extracted;
}
function formData() {
  const form = new FormData(); form.append('case_id', currentCase);
  const ad = $('adfile').files[0], kfs = $('kfsfile').files[0];
  if (Boolean(ad) !== Boolean(kfs)) throw Error('Upload both PDFs, or clear both to use the sample pair.');
  for (const [name, file] of [['advertisement', ad], ['kfs', kfs]]) {
    if (!file) continue;
    if (file.size > 5000000) throw Error('Each PDF must be smaller than 5 MB.');
    form.append(name, file);
  }
  return form;
}
async function request(path, form) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    let response;
    try { response = await fetch(path, {...(form ? {method:'POST', body:form} : {}), signal:controller.signal}); }
    catch (error) { throw Error(error.name === 'AbortError' ? 'Request timed out. Please try again.' : 'Network request failed. Please try again.'); }
    let data;
    try { data = await response.json(); }
    catch { throw Error('The service returned an unexpected response. Please try again.'); }
    if (!response.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Check the required numeric fields and try again.');
    return data;
  } finally { clearTimeout(timer); }
}
function downloadLinks() {
  for (const [id, kind] of [['adlink', 'advertisement'], ['kfslink', 'kfs']]) {
    $(id).href = '/api/sample/' + currentCase + '/' + kind;
    $(id).hidden = Boolean($('adfile').files.length || $('kfsfile').files.length);
  }
}
function evidenceBox(title, evidence) {
  const box = node('div'); box.append(node('h3', title));
  const lines = Object.values(evidence);
  if (!lines.length) box.append(node('p', 'No supported fields found. Check the document and enter the terms manually.'));
  lines.forEach(line => box.append(node('pre', line)));
  return box;
}
async function extract() {
  invalidate(true); busy(true); status('Reading the source documents…');
  try {
    const data = await request('/api/extract', formData());
    keys.forEach(k => $(k).value = data.terms[k] ?? '');
    $('source-evidence').replaceChildren(evidenceBox('Advertisement', data.ad_evidence), evidenceBox('Loan terms / KFS', data.term_evidence));
    extracted = true;
    const missing = keys.filter(k => data.terms[k] === undefined);
    status(missing.length ? '{count} fields could not be extracted. Enter them from your document; no values have been assumed.' : 'Fields extracted. Verify the figures and evidence before comparing.', {count: missing.length});
  } catch (e) { status('Could not extract: {error}', {error: e.message}); offerRetry(extract); }
  finally { busy(false); }
}
function renderReport(data, scroll = true) {
  report = data;
  $('results').hidden = false;
  const m = data.derived;
  const source = data.source === 'Uploaded document pair' ? t('Uploaded document pair') : t((data.source || currentCase).replaceAll('_',' ').replace(/\b[a-z]/g, ch => ch.toUpperCase()));
  $('report-context').textContent = source + ' · ' + new Date(data.generated_at).toLocaleString(language === 'en' ? 'en-IN' : language + '-IN');
  $('report-inputs').replaceChildren();
  const termNames = {principal:'Principal',annual_nominal_pct:'Annual nominal interest',months:'Tenure',processing_fee:'Processing fee',fee_tax:'Fee tax'};
  for (const key of keys) {
    const value = key === 'months' ? t('{value} months',{value:data.verified[key]}) : key === 'annual_nominal_pct' ? data.verified[key]+'%' : money(data.verified[key]);
    const item = node('div'); item.append(node('dt',termNames[key]), node('dd',value)); $('report-inputs').append(item);
  }
  $('metrics').replaceChildren();
  for (const [name, value] of [['Principal', data.verified.principal], ['Cash received', m.net_disbursed], ['Total repayments', m.total_repayment], ['Borrowing cost', m.borrowing_cost]]) {
    const metric = node('div', undefined, 'metric');
    metric.append(node('div', name, 'label'), node('strong', money(value)));
    $('metrics').append(metric);
  }
  $('explanation').textContent = t('Estimated monthly EMI: {emi} over {months} months. Assumes fixed reducing-balance interest, equal month-end payments and upfront fee deduction. Borrowing cost is not the regulatory APR.', {emi: money(m.emi), months: data.verified.months});
  const bar = node('div', undefined, 'cost-bar'); bar.setAttribute('aria-hidden', 'true');
  const cash = node('span'), cost = node('span');
  cash.style.width = (m.net_disbursed / m.total_repayment * 100) + '%';
  cost.style.flex = '1'; bar.append(cash, cost); $('explanation').append(bar);
  $('findings').replaceChildren();
  for (const finding of data.findings) {
    const el = node('div', undefined, 'finding ' + finding.status);
    const labels = {conflict: 'DOCUMENT MISMATCH', match: 'CONSISTENT', not_claimed: 'NOT CLAIMED', unverified: 'UNVERIFIED'};
    const field = {'Annual nominal interest': 'annual_nominal_pct', Tenure: 'months', 'Processing fee': 'processing_fee'}[finding.field];
    const format = value => field === 'months' ? t('{value} months', {value}) : field === 'processing_fee' ? money(value) : value + '%';
    const detail = finding.status === 'conflict' ? t('Advertised {ad}; KFS {kfs}.', {ad: format(data.advertisement[field]), kfs: format(data.extracted[field])})
      : finding.status === 'match' ? t('Both documents state {value}.', {value: format(data.extracted[field])})
      : t(finding.detail);
    el.append(node('strong', t(labels[finding.status]) + ' · ' + t(finding.field)), node('span', detail));
    $('findings').append(el);
  }
  $('overrides').hidden = !Object.keys(data.overrides).length;
  $('overrides').replaceChildren(node('strong', 'Manually verified figures used for the calculation'));
  for (const [key, value] of Object.entries(data.overrides)) {
    $('overrides').append(node('p', t('{field}: extracted {before} → entered {after}', {field: t({principal:'Principal',annual_nominal_pct:'Annual nominal interest',months:'Tenure',processing_fee:'Processing fee',fee_tax:'Fee tax'}[key]), before: data.extracted[key] ?? t('not found'), after: value})));
  }
  $('overrides').append(node('p', 'Document findings compare the extracted source text. Your edited figures affect the cash-flow calculation and are listed here separately.'));
  $('evidence').replaceChildren(evidenceBox('Advertisement', data.ad_evidence), evidenceBox('Loan terms / KFS', data.kfs_evidence));
  status('Report ready. Review any mismatches with your lender.');
  if (scroll) {
    revealElements([...document.querySelectorAll('#metrics .metric')]);
    animateElement(document.querySelector('.cost-bar'), [{transform:'scaleX(0)'}, {transform:'scaleX(1)'}], {duration:500});
    $('results').scrollIntoView({behavior: reducedMotion.matches ? 'instant' : 'smooth', block: 'start'});
  }
}
async function analyze() {
  if (!extracted) return;
  for (const key of keys) {
    if (!$(key).checkValidity()) {
      status('Check the required numeric fields and try again.');
      $(key).focus();
      return;
    }
  }
  invalidate(); busy(true); status('Calculating the cost…');
  try {
    const form = formData(); keys.forEach(key => form.append(key, $(key).value));
    const data = await request('/api/analyze', form);
    data.source = $('adfile').files.length ? 'Uploaded document pair' : currentCase;
    data.generated_at = new Date().toISOString();
    renderReport(data);
  } catch (e) { status('Analysis failed: {error}', {error: e.message}); offerRetry(analyze); }
  finally { busy(false); }
}
$('scenario').addEventListener('change', async e => {
  currentCase = e.target.value; $('adfile').value = ''; $('kfsfile').value = '';
  downloadLinks(); await extract();
});
for (const id of ['adfile', 'kfsfile']) $(id).addEventListener('change', () => {
  invalidate(true); downloadLinks(); status('Documents changed. Select both PDFs and extract again.');
});
keys.forEach(key => $(key).addEventListener('input', () => { invalidate(); status('Terms changed. Calculate again to update the report.'); }));
$('retry').addEventListener('click', () => retryAction?.());
$('extract').addEventListener('click', extract);
$('analyze').addEventListener('click', analyze);
$('print').addEventListener('click', () => {
  $('evidence').closest('details').open = true; window.print();
});
$('download').addEventListener('click', () => {
  if (!report) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify({...report, interface_language: language}, null, 2)], {type: 'application/json'}));
  const link = node('a'); link.href = url; link.download = 'LoanMirror-report.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
async function init() {
  busy(true);
  try {
    const cases = await request('/api/scenarios');
    $('scenario').replaceChildren();
    cases.forEach(c => { const option = node('option', c.label); option.value = c.id; $('scenario').append(option); });
    $('scenario').value = currentCase; downloadLinks(); await extract();
  } catch (e) { status('Unable to load examples. Reload the page to retry.'); offerRetry(init); }
  finally { busy(false); }
}
document.addEventListener('loanmirror:language', () => {
  if (report) renderReport(report, false);
  else status(lastStatus.key, lastStatus.values);
});
init();
