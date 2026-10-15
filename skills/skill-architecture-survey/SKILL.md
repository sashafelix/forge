---
name: skill-architecture-survey
description: Survey a scoped architectural pain point and propose simplifications without editing source.
---

# Scoped architecture survey

Use only for an operator-selected architecture question or an assigned review of a
changed area. Work read-only, with the caller's authorised files and evidence.

1. Define the maintenance pain and scope. Read applicable architectural decisions,
   module boundaries, callers and tests. A preference alone is not a defect.
2. Look for a concrete simplification: duplicated ownership, leaky interfaces,
   unnecessary cross-module knowledge or an untestable boundary. Record actual paths
   and observable consequences. Do not survey unrelated modules for extra findings.
3. For each useful candidate show the present boundary and proposed boundary, who
   would own the behaviour, preserved contracts, migration risks and guarding tests.
   A smaller public interface must not become an unbounded all-purpose module.
4. Present a small ranked set of options, including leaving the design unchanged.
   State conflicts with existing decisions and what requires an owner decision.
   Use Markdown or an existing trusted local renderer, never remote CDN scripts or
   model-generated executable HTML. Do not refactor during the survey.

Return advisory findings to the caller. Only an actual violation of a requirement,
contract or established standard belongs in a blocking verdict. The operator chooses
whether to create a separate bounded change through the usual delivery workflow.
