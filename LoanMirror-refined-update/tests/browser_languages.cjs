// Run with Playwright installed: node tests/browser_languages.cjs
// Start the app on port 8001 first; set BASE_URL or CHROMIUM_PATH to override.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {}), args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(process.env.BASE_URL || 'http://127.0.0.1:8001');
    await page.waitForFunction(() => !document.querySelector('#analyze').disabled);
    await page.click('#analyze'); await page.waitForSelector('#results:not([hidden])');
    const originalEvidence = await page.locator('#evidence pre').allTextContents();
    for (const [lang, heading, conflict] of [['hi','ऋण लेने से पहले असली लागत जानें।','दस्तावेज़ों में अंतर'],['mr','कर्ज घेण्यापूर्वी खरा खर्च जाणून घ्या.','कागदपत्रांत फरक'],['en','Know the real cost before you borrow.','DOCUMENT MISMATCH']]) {
      await page.selectOption('#language',lang);
      assert.equal(await page.locator('html').getAttribute('lang'), lang);
      assert.equal(await page.locator('h1').innerText(), heading);
      assert.match(await page.locator('#findings').innerText(), new RegExp(conflict));
      assert.match(await page.locator('#metrics').innerText(), /9,410.00/);
      assert.deepEqual(await page.locator('#evidence pre').allTextContents(), originalEvidence);
      const missing = await page.evaluate(() => [...document.querySelectorAll('[data-i18n]')].filter(el => !translations[el.dataset.i18n]).map(el => el.dataset.i18n));
      assert.deepEqual(missing, []);
    }
    await page.selectOption('#language','hi');
    await page.reload(); await page.waitForFunction(() => !document.querySelector('#analyze').disabled);
    assert.equal(await page.locator('#language').inputValue(),'hi');
    await page.locator('#months').fill('');
    await page.click('#analyze');
    assert.match(await page.locator('#status').innerText(), /आवश्यक संख्यात्मक/);
    await page.locator('#months').fill('3');
    await page.locator('#processing_fee').fill('10000');
    await page.click('#analyze');
    await page.waitForFunction(() => document.querySelector('#status').textContent.includes('अग्रिम शुल्क'));
    await page.locator('#processing_fee').fill('0');
    await page.click('#analyze'); await page.waitForSelector('#results:not([hidden])');
    assert.match(await page.locator('#overrides').innerText(), /निकाला गया 500/);
    await page.selectOption('#language','mr');
    assert.match(await page.locator('#overrides').innerText(), /काढलेले 500/);
    const download = page.waitForEvent('download'); await page.click('#download');
    const fs = require('node:fs/promises');
    const data = JSON.parse(await fs.readFile(await (await download).path(),'utf8'));
    assert.equal(data.interface_language,'mr'); assert.equal(data.verified.processing_fee,0);
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:'/tmp/loanmirror-marathi-mobile.png',fullPage:true});
    await page.emulateMedia({media:'print'});
    assert.equal(await page.locator('#language').isVisible(),false);
    await page.emulateMedia({media:'screen'});
    await page.selectOption('#scenario','07_interest_not_advertised');
    await page.waitForFunction(() => !document.querySelector('#analyze').disabled);
    await page.click('#analyze'); await page.waitForSelector('#results:not([hidden])');
    assert.match(await page.locator('#findings').innerText(),/दावा केलेला नाही/);
    assert.deepEqual(errors,[]);
    // Storage can be unavailable in privacy-restricted browsers.
    await page.addInitScript(() => { Object.defineProperty(window,'localStorage',{get(){throw Error('Blocked');}}); });
    await page.reload(); await page.waitForFunction(() => !document.querySelector('#analyze').disabled);
    await page.selectOption('#language','hi');
    assert.equal(await page.locator('html').getAttribute('lang'),'hi');
    assert.deepEqual(errors,[]);
    console.log('Language browser checks passed: translations, results, evidence integrity, persistence, errors, overrides, export, mobile, print, blocked storage.');
  } finally { await browser.close(); }
})().catch(e => {console.error(e);process.exit(1);});
