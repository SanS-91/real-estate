const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const path = require('node:path');

async function main() {
  const source = path.join(__dirname, '../workers/news-rss-fallback/src/index.mjs');
  const worker = await import(pathToFileURL(source).href);
  const morning = Date.parse('2026-10-12T03:45:00Z');
  const slot = '2026-10-12T03:15:00Z';
  assert.equal(worker.macroSlotAt(morning), slot);
  assert.throws(() => worker.macroSlotAt(Date.parse('2026-10-12T03:50:00Z')), /Unexpected/);

  let calls = [];
  const fetcher = (runs, status = 204) => async (url, options) => {
    calls.push({ url, options });
    if (!options.method) {
      return { ok: true, json: async () => ({ workflow_runs: runs }) };
    }
    return { status };
  };
  const successful = [{
    head_branch: 'main', created_at: '2026-10-12T03:21:00Z',
    event: 'schedule', status: 'completed', conclusion: 'success'
  }];
  assert.equal((await worker.recoverMacro(morning, 'test-token', fetcher(successful))).status,
    'already-success');
  assert.equal(calls.length, 1);

  calls = [];
  const running = [{
    head_branch: 'main', created_at: '2026-10-12T03:30:00Z',
    event: 'schedule', status: 'in_progress', conclusion: null
  }];
  assert.equal((await worker.recoverMacro(morning, 'test-token', fetcher(running))).status,
    'already-running');
  assert.equal(calls.length, 1);

  calls = [];
  const failed = [{
    head_branch: 'main', created_at: '2026-10-12T03:20:00Z',
    event: 'schedule', status: 'completed', conclusion: 'failure'
  }];
  assert.equal((await worker.recoverMacro(morning, 'test-token', fetcher(failed))).status,
    'dispatched');
  assert.equal(calls.length, 2);
  assert.equal(calls[1].options.method, 'POST');
  assert.ok(calls[1].url.endsWith('/actions/workflows/macro-candidate.yml/dispatches'));
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    ref: 'main', inputs: { source: 'daily-markets-production' }
  });

  calls = [];
  await assert.rejects(() => worker.recoverMacro(morning, 'test-token', fetcher([], 403)),
    /HTTP 403/);
  assert.equal(calls.length, 2);

  // The existing RSS scheduler must retain its original hourly routing and slot.
  assert.equal(worker.slotAt(Date.parse('2026-10-12T04:50:00Z')),
    '2026-10-12T04:20:00Z');
  console.log('PASS Macro Cloudflare fallback: success/running/failure/dispatch + RSS contract');
}
main().catch(err => { console.error(err); process.exitCode = 1; });
