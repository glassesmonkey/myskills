# Browser-Use Fast Path

## Goal

Use `browser-use` direct CLI as a **low-token execution lane** for repeatable directory/listing submissions.

This lane exists to reduce repeated OpenClaw `browser`-tool step orchestration on stable targets.

## Scope

Prefer this lane only when all are true:
- site is a directory / launch platform / listing surface
- submission structure is stable enough to replay
- success and failure signals are easy to detect
- the site is likely to be reused across campaigns or across multiple promoted sites
- flow stays within approved policy boundaries

Do **not** use this lane by default for:
- Google OAuth first-pass exploration
- CAPTCHA / Cloudflare / phone verification
- reciprocal backlink or paid listings
- community/forum/article posting
- long-form manual writing

## Lane lifecycle

1. `native_scout`
   - first contact with a new site
   - discover entrypoints, auth type, field structure, blockers, and output signals

2. `compile_playbook`
   - convert the discovered path into a replayable site playbook
   - store field mappings, direct steps, result checks, and fallback route

3. `browser_use_direct_observe`
   - run the compiled path with extra observation and validation
   - do not yet trust it as fully automatic

4. `browser_use_direct`
   - promote only after replay succeeds and the path looks stable enough for reuse

## Success criteria

A site is eligible for full fast-path promotion only when:
- the path succeeds at least once in scout/compile mode
- replay succeeds at least once with the compiled playbook
- selectors or other locators appear stable enough to reuse
- output checks can distinguish success / pending email / needs human / failure

## Route heuristics

### Good fast-path candidates
- no-auth directory submit forms
- email-signup directory flows with standard HTML forms
- launch/listing forms with fixed fields and clear confirmation messages

### Weak candidates
- mixed modal/SPA flows with unstable locators
- flows that need reading and reacting to lots of free-form site content
- surfaces where success is only knowable through opaque dashboards or email timing

## Token model

The fast path is attractive when repeated runs would otherwise force OpenClaw to:
- inspect page state repeatedly
- decide each next browser action step-by-step
- spend `gpt-5.4` tokens on UI interpretation that could have been compiled once

The first successful compile may cost more than a one-off run. The savings appear on replay.

## Required playbook fields for this lane

Prefer these fields in site playbooks:
- `execution_mode: browser_use_direct`
- `automation_disposition: AUTO_EXECUTE` or `ASSISTED_EXECUTE`
- `stability_score`
- `replay_confidence`
- `last_validated_at`
- `field_map`
- `direct_steps`
- `result_checks`
- `fallback_route`

## Operational rule

Treat `browser_use_direct` as a **fast path**, not as the only path. The native browser / relay stack remains the scout and fallback path.
