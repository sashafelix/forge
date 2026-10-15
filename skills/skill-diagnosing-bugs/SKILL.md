---
name: skill-diagnosing-bugs
description: Diagnose a reported bug or performance regression using reproducible evidence before proposing a fix.
---

# Evidence-led debugging

Use for a reported failure, intermittent defect or performance regression. Inherit
the caller's role and permissions. Read-only roles report reproduction needs; only
roles authorised to write tests or source may make those changes. No production
instrumentation or external access is granted by this helper.

1. Record the exact reported symptom and expected behaviour. Locate authorised
   existing logs, fixtures and call boundaries. Redact credentials from evidence.
2. Establish one repeatable observation: a failing test, bounded local command,
   captured replay or controlled measurement. Check that it detects this symptom,
   not merely a neighbouring error. Label the result `reproduced`, `captured-evidence`
   or `unverified`; report what cannot be reproduced rather than inventing certainty.
3. Minimise the reproducer while preserving the symptom. Pin time, random seeds and
   external boundaries where possible. For intermittent failures record the attempt
   count and reproduction rate; a single successful run is not proof of a fix.
4. Form a small ranked set of falsifiable hypotheses. Each predicts an observation
   that distinguishes it from the alternatives. Run only authorised, bounded probes,
   changing one factor at a time. For performance claims measure a baseline first.
5. Hand confirmed evidence to the appropriate normal RED/GREEN stages. The regression
   test must exercise the actual failure boundary. Rerun the original scenario after
   the fix; a smaller passing unit test alone is insufficient.
6. Identify temporary instrumentation, remove it only in an authorised writable role,
   and record the supported cause, remaining uncertainty and actual evidence references.

A missing reproducer can justify read-only investigation or an evidence request,
not a claim of root cause or permission for speculative production edits. Never
fabricate command results or make the implementer its own final verifier.
