# Plan input: named greeting

story_id: DEMO-STORY-ID
source: operator

## Request

Extend the existing Python greeting function in this disposable repository.

## Required behaviour

- Calling `greet()` still returns `Hello!`.
- Calling `greet("Ada")` returns `Hello, Ada!`.
- Calling `greet("  Ada  ")` returns `Hello, Ada!`.
- Calling `greet("")` or `greet("   ")` raises `ValueError`.
- The behaviour of other argument types is outside this change's scope.

## Scope and constraints

Implementation belongs in `greeting.py`; regression tests belong in
`test_greeting.py`. Use Python's standard library and `python3 -m unittest -v`.
Do not add dependencies, network calls or product infrastructure. Keep the
baseline checkout unchanged; use the governed story worktree. Preserve the
locked criteria, real command output and independent verification evidence.

This is operator input, not a generated specification, locked plan or completed
run. The orchestrator must produce those artifacts through the nine stages.
