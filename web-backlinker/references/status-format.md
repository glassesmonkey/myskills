# Fixed Status Format

Use these exact prefixes so updates stay machine-readable and human-scannable.

## Init

```text
[WB-INIT] run={run_id} | sheet={sheet_link} | targets={count} | mode={mode} | promoted={product_or_pending}
```

Emit once, immediately after creating the Sheet.

## Row result

```text
[WB-ROW] run={run_id} | idx={n}/{total} | domain={domain} | type={site_type} | result={status} | route={strategy} | reason={reason_or_-} | next={next_action}
```

Emit once when a row reaches its terminal status for the current run.

Typical `result` values:
- `SUBMITTED`
- `PENDING_EMAIL`
- `NEEDS_HUMAN`
- `SKIPPED`
- `FAILED`
- `VERIFIED`

## Summary

```text
[WB-SUMMARY] run={run_id} | total={n} | submitted={n1} | verified={n2} | pending_email={n3} | needs_human={n4} | skipped={n5} | failed={n6}
```

Emit once at the end of the run.

## Halt

```text
[WB-HALT] run={run_id} | reason={infra_reason} | last_domain={domain_or_-} | recover={suggested_next_step}
```

Emit only when infrastructure-wide failure makes continuing unsafe or impossible.
