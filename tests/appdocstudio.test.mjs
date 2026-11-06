import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const root = new URL('..', import.meta.url);
const html = readFileSync(new URL('index.html', root), 'utf8');

function extractScript() {
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  assert.ok(blocks.length >= 1, 'index.html must contain an inline script');
  return blocks.join('\n');
}

function makeEl() {
  return {
    value: '', textContent: '', innerHTML: '', style: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {}, appendChild() {}, setAttribute() {}, getContext() { return null; },
  };
}

function loadApp() {
  const elements = new Map();
  const document = {
    getElementById(id) { if (!elements.has(id)) elements.set(id, makeEl()); return elements.get(id); },
    querySelector() { return makeEl(); },
    querySelectorAll() { return []; },
    createElement() { return makeEl(); },
    addEventListener() {},
    body: makeEl(),
  };
  document.getElementById('projectPath').value = 'FixtureProject';
  const ctx = {
    document, window: {}, alert() {}, console,
    btoa: (s) => Buffer.from(s, 'binary').toString('base64'),
    atob: (s) => Buffer.from(s, 'base64').toString('binary'),
    setTimeout, clearTimeout, fetch: async () => { throw new Error('offline in tests'); },
  };
  ctx.window = ctx; ctx.globalThis = ctx;
  vm.createContext(ctx);
  vm.runInContext(extractScript(), ctx); // throws on any syntax error in the app script
  const evalIn = (expr) => vm.runInContext(expr, ctx);
  return { ctx, elements, document, evalIn };
}

test('inline app script parses and exposes the generator functions', () => {
  const { ctx, evalIn } = loadApp();
  for (const fn of ['scanProject', 'genRole', 'exportAllRoles', 'exportJSON', 'detectVersion', 'bumpVersion']) {
    assert.equal(typeof ctx[fn], 'function', `${fn} must be defined`);
  }
  assert.equal(evalIn('HANDSAKE.register().app'), 'AppDocStudio');
});

test('scanProject scans the built-in fixture project and extracts functions and variables', () => {
  const { ctx, evalIn } = loadApp();
  ctx.scanProject();
  const pd = evalIn('projectData');
  assert.equal(pd.files.length, 8, 'fixture project has 8 files');
  assert.ok(pd.totalLines > 0, 'line count must be accumulated');
  const fnNames = pd.functions.map(f => f.name);
  for (const expected of ['fetchData', 'getUser', 'createUser']) {
    assert.ok(fnNames.includes(expected), `expected extracted function ${expected}, got ${fnNames.join(',')}`);
  }
  assert.ok(pd.vars.length > 0, 'variables must be extracted');
});

test('genRole generates a distinct document for each of the six roles', () => {
  const { ctx, document } = loadApp();
  const seen = new Set();
  for (const role of ['user', 'dev', 'maint', 'reg', 'admin', 'ops']) {
    ctx.genRole(role);
    const doc = document.getElementById('roleDoc').textContent;
    assert.ok(doc.startsWith('# '), `role ${role} doc must be markdown headed`);
    assert.ok(doc.length > 80, `role ${role} doc too short`);
    seen.add(doc.split('\n')[0]);
  }
  assert.equal(seen.size, 6, 'each role must produce a distinct title');
});

test('exportJSON emits valid JSON describing the scanned project', () => {
  const { ctx, document } = loadApp();
  ctx.scanProject();
  ctx.exportJSON();
  const parsed = JSON.parse(document.getElementById('exportOutput').value);
  assert.equal(parsed.files.length, 8);
});

test('page shell declares its surfaces', () => {
  assert.ok(html.includes('<title>AppDocStudio'), 'title must name the app');
  assert.ok(html.includes('name="version"'), 'version meta must be present');
});
