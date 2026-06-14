# Retrieval Eval Harness

This folder holds lightweight evaluation utilities for the advanced retrieval
stack.

The purpose is simple:

- check whether query planning surfaces the right store mix
- check whether store queries include the right debate terms
- check whether metadata hints align with the teaching goal
- check whether structured evidence contains the expected lane types

This is intentionally heuristic-first.

It is not trying to perfectly judge retrieval quality.
It is trying to give the project a stable internal benchmark so future RAG
changes are not judged only by intuition.

## What is covered now

- query-plan evaluation
- structured-evidence lane evaluation
- representative fixture cases for:
  - preknowledge retrieval
  - argument-generation retrieval
  - coaching retrieval

## What should come next

- fixture cases built from real lesson failures
- expected-source validation using persisted retrieval traces
- duplicate-rate checks
- vocabulary freshness checks
- end-to-end lesson usefulness scoring
