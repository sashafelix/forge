---
name: skill-validation
description: "Implement input validation on request DTOs, form payloads, and domain objects, close to the entry boundary. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-validation

## Purpose
Implement input validation on request DTOs, form payloads, and domain objects, close to the entry boundary.

**Applicability**: Examples below target Java + Jakarta Bean Validation (`@Valid`, custom `ConstraintValidator`). The principles (validate at the boundary, typed schemas, message catalogues, isolated validator unit tests) apply to any stack. Translate the mechanism:
- Node / TypeScript → Zod, Valibot, Yup, class-validator
- Python → Pydantic, Marshmallow, Django forms / DRF serializers
- Go → `go-playground/validator`, ozzo-validation
- .NET → DataAnnotations, FluentValidation
- React forms → Zod + react-hook-form, Formik + Yup

**Scope tag**: `stack:backend-*` or `stack:frontend-*` (wherever the boundary lives).

## Reads
- `docs/conventions/backend-conventions-general.md` (when stack is backend)
- `docs/conventions/backend-conventions-api-service.md`
- Any stack-specific testing conventions present under `docs/conventions/`

## Writes
- Custom constraints / validators under `{project_root}` in the stack's source tree
- Validator tests in the stack's test tree
- Decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Conventions

Examples below are Java/Spring-flavored. Adapt idioms to your stack.

### Custom Constraint Annotation Pattern
```java
@Constraint(validatedBy = MyValidator.class)
@Target({ElementType.FIELD, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
public @interface HasValidXxx {
    String message() default "...";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
```

### Validator Implementation Pattern
```java
public class MyValidator implements ConstraintValidator<HasValidXxx, TargetType> {
    @Override
    public boolean isValid(TargetType value, ConstraintValidatorContext context) {
        if (value == null) return true; // null handled by @NotNull
        // validation logic
    }
}
```

### Integration
- Use `@Valid` on controller `@RequestBody` parameters.
- Group validations with `groups = {...}` when needed.
- Validation errors handled by `skill-exception-handling` via `ConstraintViolationException`.

## Guardrails
- Keep validators stateless where possible.
- Test validators in isolation with unit tests.
- Document complex validation rules in decision log.




## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
