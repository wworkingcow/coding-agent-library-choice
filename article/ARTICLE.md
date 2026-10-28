# What makes a coding agent pick a library? A small controlled experiment with Claude Code

17 of 18. That is how often Claude Code, asked to add auth to a Next.js app and pick
whatever it thinks is best, built on the vendor whose quickstart sat inside the project. With nothing
planted the same task went to next-auth in 8/8 runs. WorkOS AuthKit, which the agent never
chose unprompted, got 9/9 once its quickstart was there.
Round 2 repeated it on a second task and newer models: for transactional email, Resend in
10/10 runs on Sonnet 5.5 with nothing planted, Postmark in
10/10 with Postmark's quickstart in the project.

When a developer tells a coding agent "add auth, pick whatever you think is best", the agent
picks the vendor. Nobody visits a pricing page and nobody reads a comparison post: the choice
happens inside one tool call. I wanted to know what moves that choice, so I built a small test
bench and ran the same task many times under controlled changes. If you work on developer
relations for a library, these are the runs where your docs were, or were not, the reason you got picked.

This is a small experiment: one agent product, one app, a few runs per condition. It can show
large effects; it cannot estimate exact shares. Every number below is computed by a script
from the raw run data, which is in the repository together with the transcripts.

## TL;DR

- **The default is strong.** Asked to add email + password and Google sign-in to a Next.js app,
  Claude Code picked next-auth in 8/8 baseline runs.
- **Vendor text inside the project flips it.** The same short vendor quickstart, placed in the
  project as a docs file + `llms.txt`, as a project skill, or served by an MCP server, flipped the
  choice to that vendor in 17/18 runs (95% CI 74–99%;
  Fisher exact test against baseline, p < 0.0001).
- **The package has to exist.** The same text for a made-up vendor whose package is not on npm
  was adopted in 0/9 runs. In 4 of those
  9 runs the agent called the planted text a supply-chain risk or a
  prompt injection.
- **On the open web, comparison searches decide, not vendor sites.** With web search allowed and
  nothing planted, the pick moved to better-auth (6/8). The first web action was a
  "X vs Y" comparison search in 8 of
  8 runs. Clerk was named in the searches of 7
  runs and picked in 0; clerk.com was opened in
  0.
- **Round 2 repeats it on email and newer models.** With nothing planted: Resend
  (10/10 on Sonnet 5.5, 10/10 on Opus 5.5).
  With Postmark's quickstart in the project: Postmark (10/10,
  10/10). For auth on Opus 5.5 the default moved to better-auth
  (10/10), and WorkOS's quickstart still took it:
  10/10.
- **Being picked is not being installed.** In 10/10 baseline runs on
  Sonnet 5.5 and 7/10 on Opus 5.5 the agent picked Resend, then called
  its HTTP API with `fetch` and added no package. In 10/10 and
  5/7 of those runs its final message gave the reason: no new
  dependency. With a Resend quickstart in the project, whose code uses the `resend` package, the
  package was skipped in 0/10 and
  0/10 of the runs that picked Resend.
- **How small.** Round 1: 3 runs per lever condition. Round 2: every number
  carries its own n, and the largest arm is ten runs. Directions are visible; shares are not.

## The bench

- **App.** A small Next.js 16 "Notely" app (notes, no auth), copied fresh for every run from a
  pinned commit.
- **Agent.** Claude Code CLI 2.1.220 in headless mode (`claude -p`, permissions bypassed,
  stream-JSON output), model pinned by flag (transcripts show claude-opus-5, claude-sonnet-5: Opus only in the
  Opus condition).
- **Task.** One fixed prompt: add email + password and Google sign-in; pick whichever library or
  service you think is best. `prompts/` has it verbatim.
- **Conditions (levers).** One change per condition. *Baseline*: nothing. *Docs*: a condensed
  vendor quickstart as `docs/<vendor>.md` plus an `llms.txt` pointing at it. *Skill*: the same text
  as a Claude Code project skill. *MCP*: the same text served by a local stub MCP server with one
  `get_docs` tool. *Web*: web search and fetch allowed, nothing planted. Vendors: Clerk, WorkOS
  AuthKit, and "Keyhold", a made-up vendor whose package does not exist.
- **Reading the pick.** A script reads the diff of each run: packages added to `package.json`,
  imports, and API hosts called. Nothing is labeled by hand.
- **Size.** 3 runs per lever condition, 8 baseline runs,
  60 runs in round 1 in total.

## Results

| Condition (round 1, Sonnet 5) | Pick |
|---|---|
| Baseline (nothing planted) | 0/8 (next-auth 8/8) |
| Clerk: docs / skill / MCP | 2/3 · 3/3 · 3/3 |
| WorkOS AuthKit: docs / skill / MCP | 3/3 · 3/3 · 3/3 |
| Keyhold (made up) | 0/9 (next-auth 8/9) |

**1. The default is a reflex, not a ranking.** 8/8 baseline runs went to next-auth,
0/8 to anything else.

**2. Text in the project's context flips the choice.** Real vendors together: 17/18
(CI 74–99%). WorkOS matters more than Clerk here: the agent knows Clerk anyway,
but never reaches for AuthKit unprompted, and still took it in 9/9 runs once the
quickstart was in the project. Docs file, skill and MCP server worked about the same.

**3. The MCP server was used when its vendor was credible.** The `get_docs` tool was called in
3/3 Clerk runs and 3/3 WorkOS runs, but in
0/3 Keyhold runs: the server was there, and the agent didn't ask it.

**4. Agents check the registry.** The agent queried the npm registry in 42/60 runs.
For the made-up vendor, the missing package ended the story: 0/9 adoption, and in
4 of 9 runs the agent explicitly flagged the planted text as suspicious.

**5. With web search, the agent shops by comparison, not by vendor site.** Pick: better-auth
6/8, next-auth 2/8 (p = 0.007 against
baseline). The first web action was a comparison search ("X vs Y", "best auth for Next.js") in
8/8 runs. The only sites
opened were better-auth.com, nextjs.org; better-auth.com was opened in
4 runs, all 4
of which chose it. Clerk was named in the searches of 7 runs and
picked in 0; WorkOS was named in 0.

**6. An existing setup is sticky, docs can still move it.** In an app that already had next-auth
wired up, the task was to add a feature, and the agent was free to keep the existing setup
or replace the setup: with Clerk's quickstart present, 3/5 runs
migrated to Clerk; without it, 0/3.

**7. Two vendors in the project: fit decides, not order.** Clerk and WorkOS quickstarts side by
side, order alternated: Clerk 5/6, WorkOS 0/6. Alone, WorkOS had
won 9/9. The runs that picked Clerk argued fit, not brand: drop-in sign-in
components inside the app instead of a hosted redirect.

**8. A different model has a different default.** Baseline on Claude Opus 5: better-auth
2/3, next-auth 1/3. Three runs prove nothing,
but the baseline is a property of the model, not of the task.

## Round 2: email, Opus 5.5, and a baseline re-check

Round 2 ran 160 runs on an API key in a clean environment (model checked in every
transcript: 160 of 160 on the pinned model; CLI
2.1.299), for $28.88 in recorded cost.
2 runs hit the 900-second limit after the choice was made; they are counted as
of that moment and record no cost, so that total is a lower bound. API errors: 0.
The count includes round 3 below, which ran on the same key and the same bench.

- **Email, baseline.** Resend in 10/10 runs on Sonnet 5.5
  (CI 72–100%) and 10/10 on Opus 5.5.
- **Email, Postmark quickstart in the project.** Postmark in 10/10
  runs on Sonnet 5.5 (baseline 0/10,
  p < 0.0001) and 10/10 on Opus 5.5
  (baseline 0/10, p < 0.0001).
- **SDK or plain HTTP.** Runs that picked an email vendor but called its HTTP API with `fetch`
  instead of installing its package: baseline 10/10 on Sonnet 5.5 and
  7/10 on Opus 5.5; with the Postmark quickstart
  0/10 and 0/10.
- **Auth baseline re-check on Sonnet 5.5.** next-auth 10/10
  (round 1 on Sonnet 5: 8/8,
  p = 1).
- **Opus 5.5, auth.** Baseline: next-auth 0/10, better-auth
  10/10, custom 0/10.
  With the WorkOS quickstart: WorkOS 10/10
  (p < 0.0001 against its baseline).

Few runs per arm, so these are directions, not shares. They repeat round 1 on a second task and on
newer models. With nothing planted the agent has a fixed default: Resend for email on both models;
for auth, next-auth on Sonnet 5.5 and better-auth on Opus 5.5, the way Opus 5 already leaned in
round 1. A vendor quickstart inside the project replaces that default: Postmark for email, WorkOS for
auth on Opus 5.5. One thing round 1 could not show: picking a vendor is not the same as installing
its SDK. Without docs, the agent mostly called Resend's HTTP API with `fetch`, and the final messages
give the reason: no new dependency. The pilot, on earlier models and an earlier version of the bench,
installed the `resend` package in all its Resend picks (3/3 and
2/2). With the Postmark quickstart in the project, whose code uses the
`postmark` package, the package was installed.

## Round 3: the vendor it already picks, two vendors at once, and other defaults

Round 3 asked three follow-up questions on the same bench, all on Sonnet 5.5 unless noted.

- **Does a quickstart help the vendor the agent already picks?** Resend's own quickstart, same shape
  as Postmark's, whose code uses the `resend` package. The pick stayed Resend
  (10/10 on Sonnet 5.5, 10/10 on Opus 5.5);
  what changed is the install. Without the quickstart the agent skipped the package in
  10/10 runs on Sonnet 5.5 and 7/10 on Opus 5.5, saying "no new
  dependency" in 10/10 and 5/7
  of those. With it, the package was skipped in 0/10 runs on Sonnet 5.5 and
  0/10 on Opus 5.5.
- **Two email quickstarts side by side.** Resend and Postmark docs both in the project, `llms.txt`
  order alternated. Resend 10/10, Postmark 0/10.
  By order: Resend first, resend 5/5; Postmark first,
  resend 5/5. Alone, Postmark's quickstart had won
  10/10.
- **Web search on Sonnet 5.5, auth.** better-auth 10/10, next-auth
  0/10, Clerk 0/10, WorkOS
  0/10 (p < 0.0001 against the Sonnet 5.5
  baseline). First web action a comparison search in
  10/10 runs;
  sites opened: better-auth.com; Clerk named in the searches of
  10 runs, picked in 0,
  clerk.com opened in 0.
- **Defaults for five other tasks**, nothing planted, same prompt shape ("pick whichever you think is
  best"). The pick is read the same way, from packages added and API hosts called.

| Task (Sonnet 5.5, baseline) | n | Pick |
|---|---|---|
| Payments: monthly Pro subscription, checkout, webhook | 10 | stripe 10/10 |
| LLM call: two-sentence summary of a note | 10 | anthropic 10/10 |
| Database: persist users, migrations, typed queries | 10 | drizzle 10/10, postgres.js 7/10, better-sqlite3 2/10, pg 1/10 |
| File upload: image on a note, durable storage | 10 | s3 10/10 |
| Background jobs: reminder 10 minutes after signup, with retries | 10 | inngest 10/10 |

A run can add more than one package (an ORM and a driver, for instance), so picks can add up to more than n.
"none" means the run finished without adding a vendor package or calling a vendor API;
"unmapped" means it added a package the script does not know, listed in `stats.json` under `deps`.

## What this does not show

- **One agent product.** This measures Claude Code, not "coding agents".
- **Small n.** 3 runs per condition in round 1, at most ten per arm later.
  Directions are visible; shares are not. The confidence intervals are in `stats.json`.
- **The docs lever is a file inside the project**, not a vendor's public `llms.txt` on the web.
  Whether agents read a vendor's public `llms.txt` was not tested.
- **The vendor texts are condensed quickstarts written for the bench**, not the vendors' own pages.
  The Resend and Postmark texts were written to the same outline so the two could be compared.
- **Choice, not quality.** Whether the generated code works was not tested (no live vendor keys).
- **The LLM default is not a neutral read.** The agent is Claude; that it reached for Anthropic's SDK
  for the summarizer says nothing about how another agent would choose.
- **Round 1 isolation was incomplete.** It ran under a logged-in subscription account: account-level
  connectors were visible in 34/60 runs (never called), and
  26/60 final messages came back in the account's language (Russian) while the
  task was in English. Rounds 2 and 3 ran on an API key in a clean home directory.
- **Timing is not comparable.** Runs went in parallel (median 536 s, max
  3011 s; this is wall-clock time and in some runs far above the agent's own duration).
  3 runs hit the 900-second limit after the choice was made and are counted as of
  that moment. The limit ended the recording, not the agent, so their transcripts run on past it.
  1 run failed with an API error and was re-run.
- **Bench leak, fixed.** The first baseline runs could read a git commit message about removing agent
  instruction files; some did. History was squashed to one neutral commit and the baseline re-run
  on it; the result did not change. In round 3 a batch of runs started from a scaffold that a dry
  run had dirtied; those runs were discarded before counting and the scaffold restored from git.
- **Cost.** Round 1 ran on a subscription; its nominal price was $108.65
  (a lower bound: timed-out runs record no cost).

## What it suggests for developer-tool vendors

1. **Be in the project, not only on the web.** Starters, templates, example repos and quickstarts
   that end up inside a codebase get read. Outside the web condition the agent used web tools in
   7/52 runs: error pages and setup docs of the library it was already
   implementing, or a lookup of the made-up package. Not shopping.
2. **Make sure the package resolves under the exact name your docs use.** Agents check npm, and an
   unresolvable package reads as an attack.
3. **Being named in comparisons is not being picked.** Clerk was in the searches of
   7 web runs and picked in 0.
4. **Answer "how does this fit into my existing code".** When two vendors were both present, that
   answer decided.
5. **Being picked is not being installed.** For email the agent mostly called the chosen vendor's
   HTTP API with `fetch` to avoid a dependency. With a quickstart in the project whose code uses the
   SDK, it installed the SDK, for Postmark and for Resend alike. If your SDK is the product, the
   quickstart is what gets it installed.

## Reproduce

- `./setup.sh` rebuilds the app from `bundles/` (the exact commits the runs started from);
  `prompts/` has the tasks verbatim; `levers/` has the planted texts and the MCP stub;
  `runs/claude/<condition>/<run>/` has each run's transcript, diff, final `package.json` and metadata.
- `./run.sh claude t-auth-base 9` adds one baseline run; `python3 report.py` prints the round 1 table;
  `python3 report_2610.py` recomputes every number in this article into `stats.json`;
  `python3 article/build_article.py` rebuilds this file.

---
*Every number above is filled in from `stats.json` by `article/build_article.py` (2026-10-27).*
