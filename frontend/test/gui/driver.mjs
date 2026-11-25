/** GUI-only test driver for the documented cua_repl Tab Playwright surface.
 * No direct HTTP, React internals, request interception or provider fixtures.
 * Supply the bound tab and a writable evidence directory from cua_repl.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export function createGuiDriver(tab, directory) {
  const records = [];
  let current;

  async function snapshot() {
    return tab.playwright.evaluate(() => {
      const replies = [...document.querySelectorAll('.message--assistant')];
      const last = replies.at(-1);
      const text = (selector) => last?.querySelector(selector)?.innerText || '';
      return {
        heading: document.querySelector('h1')?.innerText || '',
        health: document.querySelector('.service-status')?.innerText || '',
        reply: text('.markdown'),
        badges: text('.response-badges'),
        limitation: text('.limitation'),
        missing: text('.missing-info'),
        error: text('.error-message'),
        cancelled: text('.message-notice'),
        loading: Boolean(last?.querySelector('.thinking')),
        sources: [...(last?.querySelectorAll('.source-card summary') || [])].map(node => node.innerText),
        timingLabel: text('.message-actions'),
        userMessages: [...document.querySelectorAll('.user-bubble')].map(node => node.innerText),
        messages: document.querySelectorAll('.message').length,
        editors: document.querySelectorAll('textarea').length,
        editorValue: document.querySelector('textarea')?.value || '',
        horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
        viewport: { width: window.innerWidth, height: window.innerHeight },
        mainText: document.querySelector('main')?.innerText || '',
      };
    });
  }

  async function save(record) {
    await mkdir(directory, { recursive: true });
    record.screenshot = `${record.id}.png`;
    try {
      await writeFile(join(directory, record.screenshot), await tab.screenshot({ fullPage: false }));
    } catch {
      // A failed evidence capture must not discard the observed test outcome.
      record.screenshot = null;
      record.captureWarning = 'La captura del navegador no estuvo disponible en este punto.';
    }
    records.push(record);
    await writeFile(join(directory, 'observations.json'), JSON.stringify(records, null, 2));
    return record;
  }

  async function newChat() {
    if (!(await tab.playwright.getByRole('button', { name: /Nueva consulta/ }).isVisible())) {
      await tab.playwright.getByRole('button', { name: 'Mostrar u ocultar navegación', exact: true }).click();
    }
    await tab.playwright.getByRole('button', { name: /Nueva consulta/ }).click();
  }

  async function start(id, question, mode = 'query', category = '') {
    await newChat();
    await tab.playwright.locator('.composer-tools').getByRole('button', { name: mode === 'search' ? 'Manuales' : 'Soporte TI', exact: true }).click();
    if (mode === 'search') await tab.playwright.getByLabel('Preferencia de categoría').selectOption(category);
    await tab.playwright.getByLabel('Consulta de soporte TI', { exact: true }).fill(question);
    current = { id, mode, question, category, startedAt: new Date().toISOString(), startMs: Date.now() };
    await tab.playwright.getByRole('button', { name: 'Enviar consulta', exact: true }).click();
    return finish();
  }

  async function finish() {
    try {
      await tab.playwright.locator('.message--assistant').last().waitFor({ state: 'visible', timeoutMs: 5_000 });
      await tab.playwright.locator('.thinking').waitFor({ state: 'hidden', timeoutMs: 40_000 });
    } catch {
      const observed = await snapshot();
      if (observed.loading) return { id: current.id, pending: true, elapsedSeconds: (Date.now() - current.startMs) / 1000 };
    }
    await tab.playwright.locator('.assistant-label').last().click();
    const record = { ...current, finishedAt: new Date().toISOString(), elapsedSeconds: (Date.now() - current.startMs) / 1000, observed: await snapshot() };
    delete record.startMs;
    return save(record);
  }

  async function checkpoint(id, description, checks, notes = '') {
    return save({ id, description, checks, notes, finishedAt: new Date().toISOString(), observed: await snapshot() });
  }

  return { records, snapshot, checkpoint, newChat, start, finish };
}
