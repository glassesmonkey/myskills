#!/usr/bin/env node
import process from 'node:process';
import { listAdapters, resolveAdapter } from './adapters/index.js';
import { readJson, writeJson, parseArgs } from './utils/io.js';
import { scout } from './scout/discover.js';
import { chooseProvider } from './providers/index.js';

function printAndMaybeWrite(result, outPath) {
  if (outPath) {
    writeJson(outPath, result);
  }
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

async function run() {
  const [command, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);

  if (!command || command === 'help') {
    process.stdout.write('Usage: node src/cli.js <adapters|scout|submit>\n');
    process.exit(1);
  }

  if (command === 'adapters') {
    printAndMaybeWrite({ ok: true, adapters: listAdapters() }, args.out);
    return;
  }

  if (command === 'scout') {
    if (!args.url) {
      throw new Error('--url is required for scout');
    }
    const result = await scout(args.url, { deep: Boolean(args.deep) });
    printAndMaybeWrite({ ok: true, scout: result }, args.out);
    return;
  }

  if (command === 'submit') {
    const task = readJson(args['task-file'], {});
    const brief = readJson(args['brief-file'], {});
    const plan = readJson(args['plan-file'], {});
    const credentials = readJson(args['credentials-file'], {});
    const adapter = resolveAdapter(task, args.adapter || 'auto');
    const providerOptions = {
      cdpUrl: args['cdp-url'] || '',
      playwrightWsUrl: args['playwright-ws-url'] || '',
      browserRuntime: {
        cdp_url: args['cdp-url'] || '',
        playwright_ws_url: args['playwright-ws-url'] || '',
      },
    };
    const requestedProvider = args.provider || (plan.execution_mode === 'manual' ? 'manual' : '');
    const provider = chooseProvider(requestedProvider, providerOptions);
    const result = await adapter.submit({
      provider,
      bbMode: args['bb-mode'] || 'auto',
      cdpUrl: args['cdp-url'] || '',
      playwrightWsUrl: args['playwright-ws-url'] || '',
      browserRuntime: {
        cdp_url: args['cdp-url'] || '',
        playwright_ws_url: args['playwright-ws-url'] || '',
      },
      task,
      brief,
      plan,
      credentials,
    });
    printAndMaybeWrite(
      {
        ok: true,
        adapter: adapter.key,
        provider: result.provider || provider,
        result,
      },
      args.out,
    );
    return;
  }

  throw new Error(`unknown command: ${command}`);
}

run().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});
