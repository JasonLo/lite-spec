# Carrier task wrapper — forces the lite-spec workflow

You are solving an open-source issue end-to-end. You MUST use the lite-spec
workflow for every step. Do NOT skip steps even if the task feels small.

## Issue

- **Repo:** {{repo}}
- **Title:** {{issue_title}}
- **Excerpt:**

  {{issue_body_excerpt}}

A seed EARS-form outcome derived from the issue (use as the starting point for
your intent — refine if you can articulate a sharper SHALL):

> {{intent_seed_outcome}}

## Required workflow

Perform these steps in order. After each step, narrate one line: what you did
and what's next.

1. **Initialize spec scaffolding** — Invoke `/spec-init` to create
   `specs/CONSTITUTION.md`, `specs/INTENT/`, and `specs/DECISIONS.md` if they
   are missing.
2. **Write the constitution** — Invoke `/spec-constitution` and produce at
   minimum these principles: (a) every EARS outcome MUST carry a `[test: ...]`
   citation; (b) DECISIONS entries MUST carry an `[intent: I-N]` tag; (c) no
   hand-written `status: complete` on intent frontmatter.
3. **Open an intent** — Invoke `/spec-intent new` with a title derived from the
   issue. Refine the seed outcome into one or more EARS SHALL statements with
   `[test: ...]` citations pointing at the test file named in the task spec.
4. **Implement the fix** — Edit the code to make the cited test pass. You MAY
   edit other code, but every change MUST be defensible against an EARS
   outcome in your intent.
5. **Log a decision** — Invoke `/spec-decisions add` to capture at least one
   non-trivial choice you made (architectural, scope, library). Include the
   `[intent: I-N]` tag.
6. **Verify drift** — Invoke `/spec-check`. The cited tests will run. Iterate
   on the implementation until your intent reaches `status: complete`.
7. **Emit the patch** — Print a unified diff of your changes to stdout under
   a fenced ```diff``` block, suitable for `git apply`.

## Hard rules

- Do NOT hand-write `status: complete` in intent.md frontmatter. `spec-check`
  is the only oracle for that field.
- Do NOT invent decisions that you did not actually make during this task.
- If `spec-check` reports `unverifiable` outcomes, re-invoke `/spec-intent
  refine` to add citations rather than papering over the gap.
- The final patch MUST be the diff of your code changes, NOT the diff of the
  `specs/` tree. The `specs/` tree is captured separately by the harness.

When done, end your final message with a line of the form:

    RESULT: done

so the harness knows execution completed normally.
