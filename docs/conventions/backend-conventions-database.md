# Backend Conventions — Database and Flyway

**Scope: backend stacks with a SQL persistence layer.** Examples below target PostgreSQL + Flyway. The *safety principles* (forward-only migrations, backfill before NOT NULL, explicit PK/FK/index naming, auditable DDL) generalize to Liquibase / Drizzle / Prisma Migrate / Alembic / ActiveRecord / Knex. See `skills/skill-database/SKILL.md` for the stack-agnostic variant.

Applies to: relevant stage agents through the matching `skills/` helpers. Helpers inherit the caller’s role and write limits; verification helpers inspect and report only.

## Migration Naming
- Format: `V{YYYYMMDDHHMM}__description.sql`
- Examples:
  - `V202310131548__create_schema.sql`

## Schema + DDL Rules
- Follow the existing project schema; `ai_pipeline` below is an illustrative name.
- Forward-only migrations.
- Deterministic SQL (no environment-specific behavior).
- Explicit PK/FK/index names.

## Schema Setup Pattern
```sql
create schema if not exists ai_pipeline;
create sequence if not exists {entity}_seq start 1 increment 1 minValue 1;
```

## Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Schema | lowercase | `inventory`, `ai_pipeline` |
| Table | snake_case | `warehouse`, `organization` |
| Column | snake_case | `warehouse_number`, `date_created` |
| Primary Key | `ID` or `id` | `ID bigserial primary key` |
| Sequence | `{entity}_seq` | `warehouse_seq`, `history_seq` |
| Foreign Key | `fk_{table}_{referenced}` | `fk_warehouse_organization` |
| Unique Index | `uk_{column}` | `uk_warehouse_number` |
| View | descriptive_name | `warehouse_overview`, `inventory_summary_view` |

## Table Creation Pattern
```sql
CREATE TABLE ai_pipeline.warehouse (
    ID                  bigserial primary key,
    WAREHOUSE_NUMBER       VARCHAR(255) NOT NULL,
    NAME                VARCHAR(255) NOT NULL,
    ORGANIZATION_FK     bigint constraint fk_warehouse_organization
                        references ai_pipeline.organization,
    date_created        timestamp DEFAULT now(),
    user_created        character varying(50),
    date_changed        timestamp DEFAULT now(),
    user_changed        character varying(50)
);
```

## Audit Columns (mutable tables)
- `date_created` - timestamp with `DEFAULT now()`, not updatable
- `user_created` - varchar(50), not updatable
- `date_changed` - timestamp with `DEFAULT now()`
- `user_changed` - varchar(50)

## PostgreSQL-Specific Types
- Use `bigserial` for auto-increment primary keys.
- Use `character varying(n)` or `VARCHAR(n)` for strings.
- Use `timestamp` for datetime fields.
- Use `numeric(precision, scale)` for decimal fields.
- Use `boolean` for flags.

## Flyway Configuration
```yaml
spring:
  flyway:
    enabled: true
    validate-on-migrate: true
    baseline-on-migrate: false
    out-of-order: false
    schemas: ai_pipeline
```

## Compatibility
- Document migration impact in story `decision-log.md`.
- Mark breaking vs non-breaking contract impact in `handoff.md`.

## Verification
- Migrations run clean on empty database.
- No hidden manual patch steps.
- Verify migrations against the actual target database engine/version using isolated test infrastructure. H2 compatibility mode can support focused tests but does not prove PostgreSQL DDL, locking or migration compatibility.
- Enable baselining or out-of-order migrations only through an explicit, reviewed migration plan.


