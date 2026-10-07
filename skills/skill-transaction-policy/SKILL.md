---
name: skill-transaction-policy
description: "Apply correct transactional boundaries for service-layer methods that write to a database. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-transaction-policy

## Purpose
Apply correct transactional boundaries for service-layer methods that write to a database.

**Applicability**: Examples below target Java/Spring's `@Transactional`. The principles (atomic write units, read-only query hints, no network I/O inside a DB transaction, explicit rollback semantics) apply to any stack. Translate the mechanism:
- Node + Prisma → `prisma.$transaction`
- Node + Drizzle / Knex → `db.transaction(async tx => …)`
- Python + SQLAlchemy → `session.begin()` / `with db.session.begin():`
- Django ORM → `@transaction.atomic`
- Go + sqlx / pgx → `tx, err := db.Begin(); defer tx.Rollback()`
- .NET EF Core → `await using var tx = await db.Database.BeginTransactionAsync()`

**Scope tag**: `stack:backend-*` with a persistence layer. Skip for pure frontend / stateless stacks.

## Reads
- `docs/conventions/backend-conventions-general.md` (when stack is backend)
- `docs/conventions/backend-conventions-api-service.md`

## Writes
- Transaction-boundary annotations / constructs on service methods under `{project_root}` in the stack's source tree
- Transaction-related test cases in the stack's test tree
- Decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Conventions

Examples below are Java/Spring-flavored. Adapt idioms to your stack.

### Default Rules
| Operation Type | Annotation | Propagation |
|----------------|------------|-------------|
| Read-only query | `@Transactional(readOnly = true)` | REQUIRED |
| Single write | `@Transactional` | REQUIRED |
| Batch write | `@Transactional` | REQUIRED |
| Mixed read/write | `@Transactional` | REQUIRED |
| External call + write | `@Transactional` on write portion only | REQUIRES_NEW if isolation needed |

### Placement
- Place `@Transactional` on public service methods, not on private helpers.
- Do not place `@Transactional` on controllers.

### EntityManager Usage
```java
@PersistenceContext
private EntityManager entityManager;

@Transactional
public void batchProcess() {
    // process items
    entityManager.flush(); // explicit sync when needed
    entityManager.clear(); // clear persistence context for large batches
}
```

### Error Handling
- RuntimeExceptions trigger rollback by default.
- Checked exceptions do not trigger rollback unless `rollbackFor` is specified.
- Use `@Transactional(rollbackFor = Exception.class)` when checked exceptions should rollback.

### Anti-Patterns to Avoid
- `@Transactional` on private methods (proxy bypass).
- Long-running transactions holding DB locks.
- Transactions spanning external HTTP calls.

## Guardrails
- Log transactional boundary decisions in decision log.
- Test rollback behavior for critical write paths.
- Prefer read-only transactions for query methods (performance + safety).




## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
