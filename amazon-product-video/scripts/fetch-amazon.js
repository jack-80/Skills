const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 },
    locale: 'en-US',
  });
  const page = await ctx.newPage();
  try {
    await page.goto('https://www.amazon.com/dp/B096MVP136', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(4000);
    const title = await page.title();
    console.log('TITLE:', title);
    // main image
    const mainImg = await page.evaluate(() => {
      const el = document.querySelector('#landingImage') || document.querySelector('#imgTagWrapperId img') || document.querySelector('#main-image');
      if (!el) return null;
      return { src: el.src, dataOldHires: el.getAttribute('data-old-hires'), dyn: el.getAttribute('data-a-dynamic-image') };
    });
    console.log('MAIN_IMG:', JSON.stringify(mainImg));
    // all image block thumbs
    const thumbs = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('#altImages img, .imageThumbnail img').forEach(i => out.push(i.src));
      return out;
    });
    console.log('THUMBS:', JSON.stringify(thumbs.slice(0, 12)));
    // price
    const price = await page.evaluate(() => {
      const el = document.querySelector('.a-price .a-offscreen');
      return el ? el.textContent : null;
    });
    console.log('PRICE:', price);
  } catch (e) {
    console.log('ERROR:', e.message);
  }
  await browser.close();
})();
