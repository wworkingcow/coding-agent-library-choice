# What makes a coding agent pick a library? A small controlled experiment with Claude Code

{{round1.levers_real|k}} of {{round1.levers_real|n}}. That is how often Claude Code, asked to add auth to a Next.js app and pick
whatever it thinks is best, built on the vendor whose quickstart sat inside the project. With nothing
planted the same task went to next-auth in {{round1.base.nextauth}} runs. WorkOS AuthKit, which the agent never
chose unprompted, got {{round1.workos_levers}} once its quickstart was there.
<!-- round2:done -->
Round 2 repeated it on a second task and newer models: for transactional email, Resend in
{{round2.tests.mail_base_resend_s55}} runs on Sonnet 5.5 with nothing planted, Postmark in
{{round2.tests.mail_postmark_docs_s55}} with Postmark's quickstart in the project.
<!-- /round2:done -->

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
  Claude Code picked next-auth in {{round1.base.nextauth}} baseline runs.
- **Vendor text inside the project flips it.** The same short vendor quickstart, placed in the
  project as a docs file + `llms.txt`, as a project skill, or served by an MCP server, flipped the
  choice to that vendor in {{round1.levers_real}} runs (95% CI {{round1.levers_real|ci}};
  Fisher exact test against baseline, {{round1.levers_real.p_vs_base|p}}).
- **The package has to exist.** The same text for a made-up vendor whose package is not on npm
  was adopted in {{round1.levers_fake}} runs. In {{round1.levers_fake.called_it_attack|k}} of those
  {{round1.levers_fake.called_it_attack|n}} runs the agent called the planted text a supply-chain risk or a
  prompt injection.
- **On the open web, comparison searches decide, not vendor sites.** With web search allowed and
  nothing planted, the pick moved to better-auth ({{round1.web.better}}). The first web action was a
  "X vs Y" comparison search in {{round1.web_trace.first_is_comparison_search}} of
  {{round1.web_trace.runs}} runs. Clerk was named in the searches of {{round1.web_trace.clerk_in_queries}}
  runs and picked in {{round1.web_trace.clerk_chosen}}; clerk.com was opened in
  {{round1.web_trace.clerk_site_fetched}}.
<!-- round2:done -->
- **Round 2 repeats it on email and newer models.** With nothing planted: Resend
  ({{round2.tests.mail_base_resend_s55}} on Sonnet 5.5, {{round2.tests.mail_base_resend_o55}} on Opus 5.5).
  With Postmark's quickstart in the project: Postmark ({{round2.tests.mail_postmark_docs_s55}},
  {{round2.tests.mail_postmark_docs_o55}}). For auth on Opus 5.5 the default moved to better-auth
  ({{round2.tests.auth_base_o55.better-auth}}), and WorkOS's quickstart still took it:
  {{round2.tests.auth_workos_docs_o55}}.
- **Being picked is not being installed.** In {{round2.tests.mail_base_nopkg_s55}} baseline runs on
  Sonnet 5.5 and {{round2.tests.mail_base_nopkg_o55}} on Opus 5.5 the agent picked Resend, then called
  its HTTP API with `fetch` and added no package. In {{round2.tests.mail_base_nopkg_said_nodep_s55}} and
  {{round2.tests.mail_base_nopkg_said_nodep_o55}} of those runs its final message gave the reason: no new
  dependency. With a Resend quickstart in the project, whose code uses the `resend` package, the
  package was skipped in {{round2.tests.mail_docs_resend_nopkg_s55}} and
  {{round2.tests.mail_docs_resend_nopkg_o55}} of the runs that picked Resend.
<!-- /round2:done -->
- **How small.** Round 1: {{round1.lever_arm_n}} runs per lever condition. Round 2: every number
  carries its own n, and the largest arm is ten runs. Directions are visible; shares are not.

## The bench

- **App.** A small Next.js 16 "Notely" app (notes, no auth), copied fresh for every run from a
  pinned commit.
- **Agent.** Claude Code CLI {{round1.cli}} in headless mode (`claude -p`, permissions bypassed,
  stream-JSON output), model pinned by flag (transcripts show {{round1.models}}: Opus only in the
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
- **Size.** {{round1.lever_arm_n}} runs per lever condition, {{round1.base.nextauth|n}} baseline runs,
  {{round1.runs}} runs in round 1 in total.

## Results

| Condition (round 1, Sonnet 5) | Pick |
|---|---|
| Baseline (nothing planted) | {{round1.base.challenger}} (next-auth {{round1.base.nextauth}}) |
| Clerk: docs / skill / MCP | {{round1.levers_real.arms.t-auth-docs-clerk}} · {{round1.levers_real.arms.t-auth-skill-clerk}} · {{round1.levers_real.arms.t-auth-mcp-clerk}} |
| WorkOS AuthKit: docs / skill / MCP | {{round1.levers_real.arms.t-auth-docs-workos}} · {{round1.levers_real.arms.t-auth-skill-workos}} · {{round1.levers_real.arms.t-auth-mcp-workos}} |
| Keyhold (made up) | {{round1.levers_fake}} (next-auth {{round1.levers_fake.nextauth}}) |

**1. The default is a reflex, not a ranking.** {{round1.base.nextauth}} baseline runs went to next-auth,
{{round1.base.challenger}} to anything else.

**2. Text in the project's context flips the choice.** Real vendors together: {{round1.levers_real}}
(CI {{round1.levers_real|ci}}). WorkOS matters more than Clerk here: the agent knows Clerk anyway,
but never reaches for AuthKit unprompted, and still took it in {{round1.workos_levers}} runs once the
quickstart was in the project. Docs file, skill and MCP server worked about the same.

**3. The MCP server was used when its vendor was credible.** The `get_docs` tool was called in
{{round1.mcp_tool_called.clerk}} Clerk runs and {{round1.mcp_tool_called.workos}} WorkOS runs, but in
{{round1.mcp_tool_called.keyhold}} Keyhold runs: the server was there, and the agent didn't ask it.

**4. Agents check the registry.** The agent queried the npm registry in {{round1.npm_registry}} runs.
For the made-up vendor, the missing package ended the story: {{round1.levers_fake}} adoption, and in
{{round1.levers_fake.called_it_attack|k}} of {{round1.levers_fake.called_it_attack|n}} runs the agent explicitly flagged the planted text as suspicious.

**5. With web search, the agent shops by comparison, not by vendor site.** Pick: better-auth
{{round1.web.better}}, next-auth {{round1.web.nextauth}} ({{round1.web.p_better_vs_base|p}} against
baseline). The first web action was a comparison search ("X vs Y", "best auth for Next.js") in
{{round1.web_trace.first_is_comparison_search}}/{{round1.web_trace.runs}} runs. The only sites
opened were {{round1.web_trace.fetched_sites}}; better-auth.com was opened in
{{round1.web_trace.better_site_fetched}} runs, all {{round1.web_trace.better_site_fetched_and_chosen}}
of which chose it. Clerk was named in the searches of {{round1.web_trace.clerk_in_queries}} runs and
picked in {{round1.web_trace.clerk_chosen}}; WorkOS was named in {{round1.web_trace.workos_in_queries}}.

**6. An existing setup is sticky, docs can still move it.** In an app that already had next-auth
wired up, the task was to add a feature, and the agent was free to keep the existing setup
or replace the setup: with Clerk's quickstart present, {{round1.second_chance.docs_clerk}} runs
migrated to Clerk; without it, {{round1.second_chance.control}}.

**7. Two vendors in the project: fit decides, not order.** Clerk and WorkOS quickstarts side by
side, order alternated: Clerk {{round1.duo.clerk}}, WorkOS {{round1.duo.workos}}. Alone, WorkOS had
won {{round1.workos_levers}}. The runs that picked Clerk argued fit, not brand: drop-in sign-in
components inside the app instead of a hosted redirect.

**8. A different model has a different default.** Baseline on Claude Opus 5: better-auth
{{round1.opus5_base.better}}, next-auth {{round1.opus5_base.nextauth}}. Three runs prove nothing,
but the baseline is a property of the model, not of the task.

## Round 2: email, Opus 5.5, and a baseline re-check

<!-- round2:pending -->
Round 2 is designed and the harness is ready, but it has not been run yet. It adds a second task
(transactional email: a welcome email and a password reset), where a pilot on an earlier version
of the bench picked Resend in
{{pilot_mail.t-mail}} runs (and {{pilot_mail.t-mail-web}} with web search); a lever with a Postmark
quickstart; the same conditions on Claude Opus 5.5; and a baseline re-check on Claude Sonnet 5.5,
because the model changed since round 1. Round 2 runs on an API key in a clean environment, with
the model ID and billing source checked in every transcript. Results will be added here.
<!-- /round2:pending -->
<!-- round2:done -->
Round 2 ran {{round2.integrity.runs}} runs on an API key in a clean environment (model checked in every
transcript: {{round2.integrity.model_ok}} of {{round2.integrity.runs}} on the pinned model; CLI
{{round2.integrity.cli}}), for {{round2.cost_total_usd|usd}} in recorded cost.
{{round2.integrity.killed_by_timeout}} runs hit the 900-second limit after the choice was made; they are counted as
of that moment and record no cost, so that total is a lower bound. API errors: {{round2.integrity.api_failed}}.
The count includes round 3 below, which ran on the same key and the same bench.

- **Email, baseline.** Resend in {{round2.tests.mail_base_resend_s55}} runs on Sonnet 5.5
  (CI {{round2.tests.mail_base_resend_s55|ci}}) and {{round2.tests.mail_base_resend_o55}} on Opus 5.5.
- **Email, Postmark quickstart in the project.** Postmark in {{round2.tests.mail_postmark_docs_s55}}
  runs on Sonnet 5.5 (baseline {{round2.tests.mail_postmark_docs_s55.base}},
  {{round2.tests.mail_postmark_docs_s55.p|p}}) and {{round2.tests.mail_postmark_docs_o55}} on Opus 5.5
  (baseline {{round2.tests.mail_postmark_docs_o55.base}}, {{round2.tests.mail_postmark_docs_o55.p|p}}).
- **SDK or plain HTTP.** Runs that picked an email vendor but called its HTTP API with `fetch`
  instead of installing its package: baseline {{round2.tests.mail_base_nopkg_s55}} on Sonnet 5.5 and
  {{round2.tests.mail_base_nopkg_o55}} on Opus 5.5; with the Postmark quickstart
  {{round2.tests.mail_docs_nopkg_s55}} and {{round2.tests.mail_docs_nopkg_o55}}.
- **Auth baseline re-check on Sonnet 5.5.** next-auth {{round2.tests.auth_base_s55_nextauth}}
  (round 1 on Sonnet 5: {{round2.tests.auth_base_s55_nextauth.vs_round1}},
  {{round2.tests.auth_base_s55_nextauth.p|p}}).
- **Opus 5.5, auth.** Baseline: next-auth {{round2.tests.auth_base_o55.next-auth}}, better-auth
  {{round2.tests.auth_base_o55.better-auth}}, custom {{round2.tests.auth_base_o55.custom/none}}.
  With the WorkOS quickstart: WorkOS {{round2.tests.auth_workos_docs_o55}}
  ({{round2.tests.auth_workos_docs_o55.p|p}} against its baseline).

Few runs per arm, so these are directions, not shares. They repeat round 1 on a second task and on
newer models. With nothing planted the agent has a fixed default: Resend for email on both models;
for auth, next-auth on Sonnet 5.5 and better-auth on Opus 5.5, the way Opus 5 already leaned in
round 1. A vendor quickstart inside the project replaces that default: Postmark for email, WorkOS for
auth on Opus 5.5. One thing round 1 could not show: picking a vendor is not the same as installing
its SDK. Without docs, the agent mostly called Resend's HTTP API with `fetch`, and the final messages
give the reason: no new dependency. The pilot, on earlier models and an earlier version of the bench,
installed the `resend` package in all its Resend picks ({{pilot_mail.t-mail}} and
{{pilot_mail.t-mail-web}}). With the Postmark quickstart in the project, whose code uses the
`postmark` package, the package was installed.

## Round 3: the vendor it already picks, two vendors at once, and other defaults

Round 3 asked three follow-up questions on the same bench, all on Sonnet 5.5 unless noted.

- **Does a quickstart help the vendor the agent already picks?** Resend's own quickstart, same shape
  as Postmark's, whose code uses the `resend` package. The pick stayed Resend
  ({{round2.tests.mail_docs_resend_s55}} on Sonnet 5.5, {{round2.tests.mail_docs_resend_o55}} on Opus 5.5);
  what changed is the install. Without the quickstart the agent skipped the package in
  {{round2.tests.mail_base_nopkg_s55}} runs on Sonnet 5.5 and {{round2.tests.mail_base_nopkg_o55}} on Opus 5.5, saying "no new
  dependency" in {{round2.tests.mail_base_nopkg_said_nodep_s55}} and {{round2.tests.mail_base_nopkg_said_nodep_o55}}
  of those. With it, the package was skipped in {{round2.tests.mail_docs_resend_nopkg_s55}} runs on Sonnet 5.5 and
  {{round2.tests.mail_docs_resend_nopkg_o55}} on Opus 5.5.
- **Two email quickstarts side by side.** Resend and Postmark docs both in the project, `llms.txt`
  order alternated. Resend {{round2.tests.mail_duo_s55.resend}}, Postmark {{round2.tests.mail_duo_s55.postmark}}.
  By order: Resend first, {{round2.tests.mail_duo_s55.by_order.rp|picks}}; Postmark first,
  {{round2.tests.mail_duo_s55.by_order.pr|picks}}. Alone, Postmark's quickstart had won
  {{round2.tests.mail_postmark_docs_s55}}.
- **Web search on Sonnet 5.5, auth.** better-auth {{round2.tests.auth_web_s55.better-auth}}, next-auth
  {{round2.tests.auth_web_s55.next-auth}}, Clerk {{round2.tests.auth_web_s55.clerk}}, WorkOS
  {{round2.tests.auth_web_s55.workos}} ({{round2.tests.auth_web_s55.p_better_vs_base|p}} against the Sonnet 5.5
  baseline). First web action a comparison search in
  {{round2.tests.auth_web_s55.trace.first_is_comparison_search}}/{{round2.tests.auth_web_s55.trace.runs}} runs;
  sites opened: {{round2.tests.auth_web_s55.trace.fetched_sites}}; Clerk named in the searches of
  {{round2.tests.auth_web_s55.trace.clerk_in_queries}} runs, picked in {{round2.tests.auth_web_s55.trace.clerk_chosen}},
  clerk.com opened in {{round2.tests.auth_web_s55.trace.clerk_site_fetched}}.
- **Defaults for five other tasks**, nothing planted, same prompt shape ("pick whichever you think is
  best"). The pick is read the same way, from packages added and API hosts called.

| Task (Sonnet 5.5, baseline) | n | Pick |
|---|---|---|
| Payments: monthly Pro subscription, checkout, webhook | {{round2.tests.defaults_s55.pay.n}} | {{round2.tests.defaults_s55.pay|picks}} |
| LLM call: two-sentence summary of a note | {{round2.tests.defaults_s55.llm.n}} | {{round2.tests.defaults_s55.llm|picks}} |
| Database: persist users, migrations, typed queries | {{round2.tests.defaults_s55.db.n}} | {{round2.tests.defaults_s55.db|picks}} |
| File upload: image on a note, durable storage | {{round2.tests.defaults_s55.upload.n}} | {{round2.tests.defaults_s55.upload|picks}} |
| Background jobs: reminder 10 minutes after signup, with retries | {{round2.tests.defaults_s55.jobs.n}} | {{round2.tests.defaults_s55.jobs|picks}} |

A run can add more than one package (an ORM and a driver, for instance), so picks can add up to more than n.
"none" means the run finished without adding a vendor package or calling a vendor API;
"unmapped" means it added a package the script does not know, listed in `stats.json` under `deps`.
<!-- /round2:done -->

## What this does not show

- **One agent product.** This measures Claude Code, not "coding agents".
- **Small n.** {{round1.lever_arm_n}} runs per condition in round 1, at most ten per arm later.
  Directions are visible; shares are not. The confidence intervals are in `stats.json`.
- **The docs lever is a file inside the project**, not a vendor's public `llms.txt` on the web.
  Whether agents read a vendor's public `llms.txt` was not tested.
- **The vendor texts are condensed quickstarts written for the bench**, not the vendors' own pages.
  The Resend and Postmark texts were written to the same outline so the two could be compared.
- **Choice, not quality.** Whether the generated code works was not tested (no live vendor keys).
- **The LLM default is not a neutral read.** The agent is Claude; that it reached for Anthropic's SDK
  for the summarizer says nothing about how another agent would choose.
- **Round 1 isolation was incomplete.** It ran under a logged-in subscription account: account-level
  connectors were visible in {{round1.account_connectors}} runs (never called), and
  {{round1.russian_final}} final messages came back in the account's language (Russian) while the
  task was in English. Rounds 2 and 3 ran on an API key in a clean home directory.
- **Timing is not comparable.** Runs went in parallel (median {{round1.seconds.median}} s, max
  {{round1.seconds.max}} s; this is wall-clock time and in some runs far above the agent's own duration).
  {{round1.killed_by_timeout}} runs hit the 900-second limit after the choice was made and are counted as of
  that moment. The limit ended the recording, not the agent, so their transcripts run on past it.
  {{round1.api_error_replaced}} run failed with an API error and was re-run.
- **Bench leak, fixed.** The first baseline runs could read a git commit message about removing agent
  instruction files; some did. History was squashed to one neutral commit and the baseline re-run
  on it; the result did not change. In round 3 a batch of runs started from a scaffold that a dry
  run had dirtied; those runs were discarded before counting and the scaffold restored from git.
- **Cost.** Round 1 ran on a subscription; its nominal price was {{round1.nominal_cost_usd|usd}}
  (a lower bound: timed-out runs record no cost).

## What it suggests for developer-tool vendors

1. **Be in the project, not only on the web.** Starters, templates, example repos and quickstarts
   that end up inside a codebase get read. Outside the web condition the agent used web tools in
   {{round1.unprompted_web}} runs: error pages and setup docs of the library it was already
   implementing, or a lookup of the made-up package. Not shopping.
2. **Make sure the package resolves under the exact name your docs use.** Agents check npm, and an
   unresolvable package reads as an attack.
3. **Being named in comparisons is not being picked.** Clerk was in the searches of
   {{round1.web_trace.clerk_in_queries}} web runs and picked in {{round1.web_trace.clerk_chosen}}.
4. **Answer "how does this fit into my existing code".** When two vendors were both present, that
   answer decided.
<!-- round2:done -->
5. **Being picked is not being installed.** For email the agent mostly called the chosen vendor's
   HTTP API with `fetch` to avoid a dependency. With a quickstart in the project whose code uses the
   SDK, it installed the SDK, for Postmark and for Resend alike. If your SDK is the product, the
   quickstart is what gets it installed.
<!-- /round2:done -->

## Reproduce

- `./setup.sh` rebuilds the app from `bundles/` (the exact commits the runs started from);
  `prompts/` has the tasks verbatim; `levers/` has the planted texts and the MCP stub;
  `runs/claude/<condition>/<run>/` has each run's transcript, diff, final `package.json` and metadata.
- `./run.sh claude t-auth-base 9` adds one baseline run; `python3 report.py` prints the round 1 table;
  `python3 report_2610.py` recomputes every number in this article into `stats.json`;
  `python3 article/build_article.py` rebuilds this file.
