# AI Usage

## What's in this folder

| File | What it is |
|---|---|
| `session.jsonl` | The raw Claude Code session log, copied verbatim from `~/.claude/projects/`. The authoritative export. |
| `transcript.md` | The same session rendered as readable Markdown — prompts, replies, tool calls, and thinking. Long outputs are truncated; nothing is reworded or re-ordered. |

**One caveat, stated plainly:** the log is written live during the session, so the export
captures everything up to the point it was copied — the final few turns (writing this file,
the last commits) aren't in it. Refresh it with:

```bash
cp ~/.claude/projects/-home-joshua-Desktop-Backend-Technical-Challenge-project-b-ai-assisted/ce70aba3-*.jsonl prompts/session.jsonl
```

---

## Model used

**Claude Opus 4.8**, via Claude Code (CLI), for the whole project — planning, code, tests,
and docs. One model, no switching.

### Why this model

- **The work was reasoning-heavy, not volume-heavy.** The interesting parts of this project
  are judgment calls — 307 vs 301, 404 vs 410, whether "your URLs" implies ownership — not
  lines of code. Those are exactly where a stronger model pays for itself. The actual code
  is maybe 600 lines; the decisions behind it are the deliverable.
- **It caught its own errors.** Opus 4.8 proposed the mutation-testing pass that found my
  dead-code security guard (below). A model that only writes code wouldn't have questioned
  code it had just written.
- **Agentic tool use.** Claude Code drove the whole loop directly: ran pytest, started
  uvicorn, drove a real browser with Playwright, read the screenshots back. That closes the
  gap between "the code looks right" and "I watched it work."

### Why not the alternatives

- **Sonnet 5 / Haiku 4.5** — faster and cheaper, and honestly fine for CRUD scaffolding.
  But this project is small enough that speed saves minutes while a missed design flaw
  costs the submission. Wrong trade here.
- **ChatGPT / Codex in a browser** — the copy-paste loop breaks the thing that mattered
  most: the model running its own tests and seeing them fail. Verification would have been
  my job, and the transcript would be a record of intentions rather than results.

---

## How it was actually used

Not "generate a URL shortener." The session ran as a **design conversation first**:

1. **Brainstorm** — Claude interrogated the spec and surfaced ambiguities I hadn't
   resolved. The sharpest: *"a dashboard showing **your** URLs" is incompatible with a
   single shared API key* — with one key, "your URLs" just means "all URLs." That question
   reshaped the schema before a line was written.
2. **Design doc** → `docs/2026-07-17-url-shortener-design.md`, committed before implementing.
3. **Test-driven implementation** — tests first, watch them fail, then the code.
4. **Verification** — mutation testing, then a real browser driven through every state.

### The most useful thing it did

Partway through, every test passed on the first run. Instead of taking the win, Claude
flagged that as suspicious — tests that have never failed prove nothing — and ran a
**mutation-testing pass**: deliberately break the code, confirm a test screams.

Nine of ten mutations were caught. One survived: deleting the `javascript:`/`data:` scheme
allowlist broke **no test**. The reason was that Pydantic's `HttpUrl` already enforces
http/https, so the guard I'd written was unreachable — and the design doc's claim that
`HttpUrl` "is not sufficient on its own" was simply **wrong**.

The app was never vulnerable. But it was protected by a line I hadn't credited, while a
decorative line sat next to it looking like the protection. Both the code and the design
doc were corrected (the doc keeps the mistake visible rather than quietly editing it away).

Worth noting: **TDD alone would not have caught this.** The test passed either way. Only
breaking the code on purpose exposed it.

### Where I overrode it

- **Skipped the separate planning step.** The workflow wanted spec → plan → code. The spec
  was detailed enough to act as the plan; a second document would have been ceremony.
- **Kept Geist** against a design-linter warning that it's an overused typeface. The
  linter's right in general, but `project-a-manual` already ships Geist and these two
  projects are one submission that should look like one codebase.

### Where it was wrong, and I made it fix it

- The dead security guard above.
- A stray `0` typo inside JSX that would not have compiled.
- Two React lint errors it initially wrote past — `setState` inside an effect. The fix
  wasn't cosmetic: making the fetch effect cancellable closed a **real race** where
  switching API keys mid-request could paint one key's links under another key's session.
- It moved `pytest.ini` into `backend/`, silently breaking the entire test suite
  (`ModuleNotFoundError`). Caught only by following `SETUP.md` from scratch in a clean
  directory — the tests it had "verified" 20 minutes earlier no longer ran at all.

That last one is the honest summary of AI-assisted work: the code was good, and it still
managed to break its own test suite through a careless file operation while cleaning up.
The verification caught it. Nothing else would have.
