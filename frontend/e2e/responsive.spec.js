// Layout checks at phone, tablet and desktop widths (projects in playwright.config.js),
// in light and dark themes. Screenshots land in e2e/.screens (git-ignored) for review.
import { expect, test } from '@playwright/test';

async function noHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'page scrolls sideways').toBeLessThanOrEqual(0);
  // Clipped controls don't widen the page, so also check that every visible control is on screen.
  const offscreen = await page.evaluate(() =>
    [...document.querySelectorAll('header a, header button, main button, main a, input')]
      .filter((el) => el.offsetParent !== null && !el.closest('dialog'))
      .filter((el) => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && (r.left < -1 || r.right > window.innerWidth + 1);
      })
      .map((el) => el.getAttribute('aria-label') || el.textContent.trim().slice(0, 30)),
  );
  expect(offscreen, 'controls cut off at the screen edge').toEqual([]);
}

for (const theme of ['light', 'dark']) {
  test(`sandbox and benchmark fit the screen (${theme})`, async ({ page }, testInfo) => {
    await page.addInitScript((t) => localStorage.setItem('theme', t), theme);
    await page.goto('/');
    await expect(page.getByText(/Hi Aarav/)).toBeVisible();

    // Navigation and the case picker are always reachable.
    await expect(page.getByRole('link', { name: 'Benchmark' })).toBeInViewport();
    await expect(page.getByRole('button', { name: /change case/i })).toBeInViewport();
    await expect(page.getByRole('textbox', { name: /reply as/i })).toBeInViewport();

    const input = page.getByRole('textbox', { name: /reply as/i });
    await input.fill('Yes, send me the payment link please');
    await input.press('Enter');
    await expect(page.getByRole('link', { name: /Pay ₹279\.00/ })).toBeVisible();
    await noHorizontalOverflow(page);
    const name = `${testInfo.project.name}-${theme}`;
    await page.screenshot({ path: `e2e/.screens/sandbox-${name}.png` });

    const mobile = (page.viewportSize()?.width ?? 1440) < 768;
    if (mobile) {
      // One pane at a time on phones; the others are a tap away.
      await page.getByRole('tab', { name: 'Audit' }).click();
      await expect(page.getByRole('heading', { name: 'Guardrails' })).toBeVisible();
      await page.getByRole('tab', { name: 'Case' }).click();
      await expect(page.getByText('Max discount')).toBeVisible();
      await page.screenshot({ path: `e2e/.screens/sandbox-case-${name}.png` });
    }

    await page.getByRole('link', { name: 'Benchmark' }).click();
    const run = page.getByRole('button', { name: 'Run benchmark', exact: true });
    if (await run.isEnabled()) await run.click();
    await expect(page.getByRole('progressbar')).toBeHidden({ timeout: 60_000 });
    await expect(run).toBeEnabled({ timeout: 60_000 });
    await expect(page.getByRole('button', { name: /^Case 50:/ })).toBeEnabled({ timeout: 60_000 });
    await noHorizontalOverflow(page);
    await page.screenshot({ path: `e2e/.screens/benchmark-${name}.png`, fullPage: true });
  });
}
