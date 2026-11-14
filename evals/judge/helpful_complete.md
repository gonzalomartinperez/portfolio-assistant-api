---
id: judge-helpful-complete
version: 0.1.0
owner: owner
last-reviewed: 2026-11-14
status: stub, not validated, not used by any gate
---

# Criterion: helpful_complete

Binary question: does the answer address the visitor's actual question first, with enough detail to be useful?

## Pass

The first sentences respond directly to what was asked, and the answer gives enough concrete detail
for the visitor to act or conclude. If the corpus cannot support an answer, a clear statement of that
plus a useful next step counts as complete.

## Fail

The answer drifts to a different topic, buries the answer behind preamble, is vague or generic, or
omits detail the question clearly needs. A refusal where an answer was supported also fails.

## Examples (generic)

- Question: "Which programming languages are used in the featured projects?" Answer lists the languages
  and ties each to a project. Pass.
- Question: "Which programming languages are used in the featured projects?" Answer describes a general
  love of learning without naming any language. Fail.
