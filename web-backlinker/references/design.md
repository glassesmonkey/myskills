# Web Backlinker Design

## Purpose

Turn backlink operations into a repeatable system instead of ad-hoc browser work. The system should:

1. Import a txt list of target URLs
2. Create a Google Sheet control panel immediately
3. Build a factual profile for the promoted site
4. Scout and classify targets before execution
5. Execute backlink work as resumable single-URL tasks
6. Mark human-required rows without blocking the batch
7. Learn successful paths into reusable local playbooks
8. Recover cleanly from stalls, crashes, or long-running task interruptions

## Non-goals for v1

- Do not auto-write and publish long-form articles
- Do not auto-interact in communities beyond simple classification/routing
- Do not bypass CAPTCHA or Cloudflare challenges
- Do not auto-pay for listings
- Do not auto-accept reciprocal backlink requirements
- Do not store passwords in Sheet
- Do not let the system autonomously rewrite its core risk rules
- Do not depend on one giant continuous run to finish an entire target batch

## Core objects

### Promoted Site
The site/product that should receive the backlink. Example: ExactBank or OmniConvert.

Responsibilities:
- produce reusable descriptions and category mappings
- constrain claims to evidence-backed facts
- provide copy variants for directory forms, community blurbs, and article angles

### Target Site
The platform where a backlink/listing/content placement may happen.

Examples:
- tool directories
- launch platforms
- forums and communities
- article platforms
- unknown or custom platforms

### Run
A batch execution instance identified by `run_id`.

A run owns:
- sheet link
- target import summary
- per-row results
- artifacts and evidence
- a final summary
- local task-store path

### Task
A single recoverable unit of work for one target URL.

A task owns:
- one target URL / domain
- one current state
- attempt counters
- checkpoint metadata
- last progress timestamp
- last error
- optional playbook match
- optional worker lock information

### Playbook
A reusable memory artifact describing how a target site or a family of similar sites can be handled.

There are two playbook scopes:
- `site`: one concrete domain/platform
- `pattern`: a reusable class such as `google-oauth-directory`

## Storage architecture

### Google Sheet: operational state and review surface
Use Sheet for:
- current run status
- row triage
- human review
- queueing and summaries
- playbook index only

### Local workspace files: canonical memory and task recovery
Use local files for:
- full product profiles
- full playbook bodies
- run manifests
- screenshots / HTML / notes / artifacts
- task-store state and checkpoints

### Secrets store: credentials only
Use keyring or another secure local secret store for:
- passwords
- app passwords
- sensitive tokens

## Runtime architecture

### Principle: one URL = one worker task
Do not ask a single worker turn to process the whole batch. Each worker should:
- claim one executable task
- advance that task through one or more meaningful phases
- checkpoint progress
- finish in a recoverable state

This makes failures local instead of batch-wide.

### Principle: separate worker from watchdog/summary
Worker runs should:
- claim one task
- scout or execute it
- update task state, sheet state, and artifacts
- exit

Watchdog/summary runs should:
- inspect the task store and recent progress
- detect stalled tasks
- trigger recovery when needed
- report concise progress summaries

Do not combine deep browser execution and broad reporting into one oversized periodic job.

### Principle: long task overall, short progress gaps
A single URL may legitimately take 10-20 minutes because of signup, email verification, uploads, or redirects. That is acceptable.

What is not acceptable is a task that makes no visible progress for several minutes without checkpointing.

Recommended defaults:
- task total timeout: 900-1200 seconds
- expected checkpoint cadence: 60-120 seconds
- stalled if no progress: 300 seconds

## End-to-end workflow

### Phase 0 — bootstrap
Create the local runtime layout and a new run manifest.

### Phase 1 — create the Sheet first
Return the sheet link immediately to the user using `[WB-INIT]`.

### Phase 2 — import and normalize targets
Read the txt file, dedupe by normalized URL, assign row ids, write `Targets`, initialize the local task store, and apply the cross-run submission ledger so already-submitted targets get parked before execution.

### Phase 3 — build/update product profile
Inspect the promoted site and build a factual profile before filling submissions.

### Phase 4 — scout targets
Determine:
- site type
- auth type
- submit path
- blockers
- automation level
- possible playbook match

Persist scouting results into both Sheet and local task state.

### Phase 5 — execute via single-URL workers
Primary v1 focus:
- tool directories
- launch platforms
- standard add-listing flows
- Google OAuth
- email signup
- email verification

### Phase 6 — mark human-required rows and continue
Any row that requires human review should be marked and skipped for now, not allowed to stop the batch.

### Phase 7 — learn
Successful runs update site playbooks, upsert the submission ledger for cross-run dedupe, and may later contribute to pattern playbooks.

### Phase 8 — watchdog and summary
A separate watchdog inspects whether tasks are progressing and restarts/resumes work when progress stalls.

## v1 scope

### Included
- txt import
- Google Sheet control panel
- local task-store persistence
- promoted-site profiling
- target scouting and classification
- directory / launch-platform execution
- non-blocking human queueing
- local playbook storage
- fixed-format run status lines
- worker/watchdog separation

### Deferred
- auto-posting long-form articles
- autonomous community participation
- pricing / payment decisions
- sophisticated multi-step content adaptation for UGC platforms
- dynamic rule rewriting
- full external webhook dispatcher
- Lobster-based deterministic workflow orchestration

## Practical adoption order

1. Persist task state locally
2. Execute one URL per worker
3. Split watchdog/summary away from worker execution
4. Use heartbeat only as a watchdog/reminder, not as the primary executor
5. Gradually move unattended browser work toward a managed profile
