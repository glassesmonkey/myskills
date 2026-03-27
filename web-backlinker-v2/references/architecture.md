# Architecture

## Goal

Build a backlink skill that is cheaper on later runs than on the first run.

That means the skill must remember:

- what the promoted site is
- how each target site accepts submissions
- which account already exists for that target
- which promoted site was already submitted there

## What To Keep From The Reference Projects

From `glassesmonkey/backlink-pilot-backup`:

- fast scouting mindset
- generic form-filling fallback
- target catalog mindset
- UTM tagging as a first-class concern

From `glassesmonkey/myskills/web-backlinker`:

- run manifest and runtime directories
- task store and small-batch worker model
- site playbooks as reusable memory
- account registry and submission ledger
- promoted-site profile as a first-class artifact

## What To Improve

The new skill tightens six things:

1. First-success memory is mandatory.
   A successful first submission must create or improve a site playbook so the next run starts from reuse, not rediscovery.

2. Email verification is a real runtime capability.
   The skill uses the Google Workspace `gog` CLI instead of hand-waving mailbox steps.

3. OAuth is supported, but only inside a bounded policy.
   The skill may use OAuth when it is the natural route, but it does not accept suspicious scopes or anti-bot escalation.

4. Queue draining is autonomous.
   One blocked row cannot stall the rest of the campaign.

5. UTM tagging is universal.
   Every outbound promoted URL is built through the same deterministic helper.

6. Promoted-site probing is proactive and resumable.
   The skill builds a material pack up front and can backfill missing facts later.

## Four Memory Layers

### 1. Promoted-site profile

This is the source of truth for copy and facts.

Store:

- product identity
- descriptions
- categories
- factual claims
- approved emails
- approved disclosure boundaries

### 2. Site playbook

This is the reusable memory for a target site.

Store:

- entry URL
- auth route
- field map
- stable steps
- success signals
- fallback route
- replay confidence

### 3. Account registry

This prevents pointless re-registration.

Store:

- target domain
- account reference
- signup email
- auth type
- browser profile reference
- status

### 4. Submission ledger

This prevents duplicate submissions for the same promoted site.

Key each record by:

- promoted URL without query
- target domain
- target normalized URL when available

## Runtime Layout

Use one local base directory:

```text
data/backlink-helper/
  accounts/
  artifacts/
  playbooks/
    patterns/
    sites/
  profiles/
  runs/
  tasks/
  submission-ledger.json
```

## Non-goals

- bypassing advanced anti-bot systems
- auto-paying for listings
- auto-accepting reciprocal backlink deals
- inventing missing marketing facts
- turning one huge browser session into the only source of truth
