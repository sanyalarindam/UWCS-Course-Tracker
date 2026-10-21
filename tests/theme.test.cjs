const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

function boot(preference, systemDark) {
  const root = { dataset: { themePreference: preference } };
  const button = { attributes: {}, setAttribute(name, value) { this.attributes[name] = value; } };
  const selector = { value: '' };
  const system = { matches: systemDark, addEventListener(name, callback) { this.change = callback; } };
  const window = { matchMedia: () => system };
  const document = {
    documentElement: root,
    querySelectorAll: () => [button],
    querySelector: () => selector,
    addEventListener(name, callback) { this.ready = callback; },
  };
  runInNewContext(readFileSync(join(__dirname, '../web/theme.js'), 'utf8'), { window, document });
  document.ready();
  return { root, button, selector, system, apply: window.UWCSTheme.apply };
}

test('system mode follows a dark device setting before the document renders', () => {
  const page = boot('system', true);
  assert.equal(page.root.dataset.theme, 'dark');
  assert.equal(page.button.attributes['aria-pressed'], 'true');
  assert.equal(page.button.attributes['aria-label'], 'Switch to light mode');
  assert.equal(page.selector.value, 'system');
});

test('system mode follows a light device setting', () => {
  const page = boot('system', false);
  assert.equal(page.root.dataset.theme, 'light');
  assert.equal(page.button.attributes['aria-label'], 'Switch to dark mode');
});

test('an explicit dark preference overrides the device setting', () => {
  const page = boot('dark', false);
  assert.equal(page.root.dataset.theme, 'dark');
  page.system.matches = false;
  page.system.change();
  assert.equal(page.root.dataset.theme, 'dark');
});

test('an explicit light preference overrides a dark device setting', () => {
  const page = boot('light', true);
  assert.equal(page.root.dataset.theme, 'light');
  page.apply('dark');
  assert.equal(page.root.dataset.theme, 'dark');
  assert.equal(page.selector.value, 'dark');
});

test('device changes apply only while system mode is selected', () => {
  const page = boot('system', false);
  page.system.matches = true;
  page.system.change();
  assert.equal(page.root.dataset.theme, 'dark');
  page.apply('light');
  page.system.change();
  assert.equal(page.root.dataset.theme, 'light');
  assert.equal(page.button.attributes['aria-pressed'], 'false');
});
