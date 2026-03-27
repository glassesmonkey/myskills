# Worker Brief

## Goal

Keep the browser worker small.

The worker should not reread the full profile, full task store, and raw scouting artifacts on every row. Instead, hand it one compact brief with only the facts needed now.

## Include

- target URL and domain
- route and execution mode
- auth and anti-bot classification
- promoted-site name and approved descriptions
- the tracked UTM URL for this target
- preferred contact emails
- matched playbook summary
- matched account summary
- missing fields that may still block the row

## Exclude

- old logs
- full event history
- large raw HTML
- duplicate profile prose

## Use

Generate the brief immediately before execution so it reflects the latest task, playbook, and account memory.
