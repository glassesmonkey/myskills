# playwright-cli Reading Route

Use this only when normal readable-page routes fail.

## Escalate to playwright-cli when

- page requires login
- content appears after click / scroll / consent accept
- page is hydrated by JS and text is missing in Jina / Scrapling / web_fetch
- session cookies or localStorage are required

## Why

For reading tasks, `playwright-cli` is not the cheapest extractor by itself. Its job is to **reveal the real content**, then extract only the content container HTML.

## Suggested flow

1. Open page in a stable session:

```bash
playwright-cli -s=reader open <url> --persistent
```

2. If needed, log in or interact:

```bash
playwright-cli -s=reader snapshot
playwright-cli -s=reader click <ref>
playwright-cli -s=reader press End
playwright-cli -s=reader wait 2000
```

3. Extract only the article/content HTML:

```bash
playwright-cli -s=reader eval "() => {
  const el = document.querySelector('article, main, .post-content, .entry-content, [class*=content], [class*=article]');
  return (el || document.body).outerHTML;
}"
```

4. Convert HTML to Markdown:

```bash
playwright-cli -s=reader eval "() => {
  const el = document.querySelector('article, main, .post-content, .entry-content, [class*=content], [class*=article]');
  return (el || document.body).outerHTML;
}" | python3 scripts/html_to_markdown.py
```

## Local note

If `playwright-cli` is missing on the host, record that limitation and use the best available route instead of pretending browser extraction is available.
