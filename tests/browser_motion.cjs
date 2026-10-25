// Start the app first; run with BASE_URL and optionally CHROMIUM_PATH.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {}), args:['--no-sandbox']});
  try {
    const page = await browser.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.BASE_URL || 'http://127.0.0.1:8004/compare');
    await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
    await page.locator('#processing_fee').fill('250');
    await page.click('#analyze');await page.waitForSelector('#results:not([hidden])');
    const metrics=await page.locator('#metrics strong').allTextContents();
    const evidence=await page.locator('#evidence pre').allTextContents();
    // Fire multiple changes in the same browser frame: latest choice wins with no queued translations.
    const animationState=await page.evaluate(()=>{
      const select=document.querySelector('#language');
      for(const lang of ['hi','mr','en','hi']){select.value=lang;select.dispatchEvent(new Event('change'));}
      const animations=document.querySelector('.workspace').getAnimations();
      return {lang:document.documentElement.lang,count:animations.length,duration:animations[0].effect.getTiming().duration,frames:animations[0].effect.getKeyframes()};
    });
    assert.equal(animationState.lang,'hi');assert.equal(animationState.count,1);
    assert.equal(animationState.duration,240);assert.equal(animationState.frames[0].filter,'blur(2px)');
    await page.evaluate(()=>Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{}))));
    assert.equal(await page.locator('.workspace').evaluate(el=>getComputedStyle(el).filter),'none');
    assert.equal(await page.locator('#processing_fee').inputValue(),'250');
    assert.deepEqual(await page.locator('#metrics strong').allTextContents(),metrics);
    assert.deepEqual(await page.locator('#evidence pre').allTextContents(),evidence);
    assert.equal(await page.locator('#language').isEnabled(),true);
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.selectOption('#language','mr');
    assert.equal(await page.locator('html').getAttribute('lang'),'mr');
    assert.equal(await page.evaluate(()=>document.getAnimations().length),0);
    await page.click('#analyze');await page.waitForFunction(()=>!document.querySelector('#analyze').disabled);
    assert.equal(await page.evaluate(()=>document.getAnimations().length),0);
    assert.equal(await page.locator('.workspace').evaluate(el=>el.classList.contains('is-busy')),false);
    await page.emulateMedia({reducedMotion:'no-preference'});
    await page.selectOption('#language','en');
    await page.evaluate(()=>window.dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.evaluate(()=>document.getAnimations().length),0);
    await page.setViewportSize({width:320,height:800});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    assert.deepEqual(errors,[]);
    console.log('Motion checks passed: 240ms blur, rapid switching, unchanged data, reduced motion, print cleanup and mobile width.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
