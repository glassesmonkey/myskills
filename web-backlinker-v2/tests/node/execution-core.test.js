import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';

import generic from '../../packages/execution-core/src/adapters/generic.js';
import { resolveAdapter } from '../../packages/execution-core/src/adapters/index.js';
import { scout } from '../../packages/execution-core/src/scout/discover.js';

function withServer(routes, run) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((request, response) => {
      const body = routes[request.url] || routes.default;
      response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      response.end(body);
    });
    server.listen(0, async () => {
      const port = server.address().port;
      const baseUrl = `http://127.0.0.1:${port}`;
      try {
        await run(baseUrl);
        server.close(() => resolve());
      } catch (error) {
        server.close(() => reject(error));
      }
    });
  });
}

test('resolveAdapter falls back to generic for unknown sites', () => {
  const adapter = resolveAdapter({ domain: 'unknown.test' });
  assert.equal(adapter.key, 'generic');
});

test('scout detects directory form and auth hints', async () => {
  await withServer(
    {
      '/': `
        <html><body>
          <a href="/submit">Submit your tool</a>
        </body></html>
      `,
      '/submit': `
        <html><body>
          <h1>Submit your tool</h1>
          <form action="/done" method="post">
            <label for="name">Product name</label>
            <input id="name" name="name" />
            <label for="url">Website URL</label>
            <input id="url" name="url" />
            <textarea name="description"></textarea>
            <button type="submit">Submit</button>
          </form>
        </body></html>
      `,
    },
    async (baseUrl) => {
      const result = await scout(baseUrl, { deep: true });
      assert.equal(result.site_type, 'directory');
      assert.equal(result.auth_type, 'none');
      assert.equal(result.submission_type, 'form');
      assert.ok(result.field_map.product_name);
    },
  );
});

test('generic adapter produces compile hints in dry-run mode', async () => {
  await withServer(
    {
      default: `
        <html><body>
          <form action="/done" method="post">
            <label for="tool">Tool name</label>
            <input id="tool" name="tool" />
            <label for="site">Website</label>
            <input id="site" name="site" />
            <label for="email">Email</label>
            <input id="email" name="email" />
            <textarea name="description" placeholder="Description"></textarea>
            <button type="submit">Submit</button>
          </form>
        </body></html>
      `,
    },
    async (baseUrl) => {
      const result = await generic.submit({
        provider: 'dry-run',
        task: {
          normalized_url: baseUrl,
        },
        brief: {
          promoted_site: {
            product_name: 'Demo Tool',
            tracked_url: 'https://example.com/?utm_source=test',
            contact_emails: ['team@example.com'],
            short_description: 'A test submission',
          },
        },
      });
      assert.equal(result.outcome, 'defer_retry');
      assert.equal(result.provider, 'dry-run');
      assert.equal(result.compile_hint.adapter, 'generic');
      assert.ok(result.compile_hint.field_map.product_name);
    },
  );
});
