---
name: skill-exception-handling
description: "Implement centralized exception / error handling with consistent API error responses. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-exception-handling

## Purpose
Implement centralized exception / error handling with consistent API error responses.

**Applicability**: This skill's code examples target Java + Spring's `@RestControllerAdvice`. The *principles* (central handler, typed domain errors, consistent response shape, correlation id, no stack traces in prod) apply to any stack. Translate the mechanism to your framework:
- Express/Fastify/NestJS → error-handling middleware / `ExceptionFilter`
- FastAPI → `exception_handler` + `HTTPException`
- Django → middleware + DRF `exception_handler`
- Go (chi/echo/gin) → error middleware
- .NET → `IExceptionFilter` / `UseExceptionHandler`

**Scope tag**: `stack:backend-*`. Frontend error boundaries are out of scope (see stack-specific UI conventions).

## Reads
- `docs/conventions/backend-conventions-general.md` (when stack is backend)
- `docs/conventions/backend-conventions-api-service.md`
- Any stack-specific testing conventions present under `docs/conventions/`

## Writes
- Custom exception / error types under `{project_root}` in the stack's source tree
- API error response structures in the same tree
- Global exception handler in the stack's canonical location (e.g., `@RestControllerAdvice` in Spring, error middleware in Express, `exception_handler` in FastAPI)
- Exception-handling tests in the stack's test tree
- Decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Conventions

Examples below are Java/Spring-flavored. Adapt idioms to your stack.

### Custom Exception Pattern
```java
public class EntityNotFoundException extends RuntimeException {
    public EntityNotFoundException(Class clazz, String... searchParams) {
        super(generateMessage(clazz.getSimpleName(), toMap(searchParams)));
    }
}
```

### ApiError Response Structure
```java
@Data
public class ApiError {
    private HttpStatus status;
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "dd-MM-yyyy hh:mm:ss")
    private LocalDateTime timestamp;
    private String message;
    private String debugMessage;
    private List<ApiSubError> subErrors;
}
```

### Global Exception Handler Pattern
```java
@RestControllerAdvice
@Slf4j
public class RestExceptionHandler {

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<?> handleConstraintViolation(ConstraintViolationException ex) {
        ApiError error = new ApiError(BAD_REQUEST);
        error.setMessage("Validation error");
        error.addValidationErrors(ex.getConstraintViolations());
        return buildResponseEntity(error);
    }

    @ExceptionHandler(EntityNotFoundException.class)
    public ResponseEntity<?> handleEntityNotFound(EntityNotFoundException ex) {
        return buildResponseEntity(new ApiError(NOT_FOUND, ex));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<?> handleAccessDenied(AccessDeniedException ex) {
        return buildResponseEntity(new ApiError(FORBIDDEN, ex));
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<?> handleDataIntegrity(DataIntegrityViolationException ex) {
        if (ex.getCause() instanceof ConstraintViolationException) {
            return buildResponseEntity(new ApiError(CONFLICT, "Database error", ex.getCause()));
        }
        return buildResponseEntity(new ApiError(INTERNAL_SERVER_ERROR, ex));
    }
}
```

### Required Exception Types
- `EntityNotFoundException` (404)
- `BadRequestException` (400)
- `AccessDeniedException` (403)
- `DataIntegrityViolationException` (409/500)

## Guardrails
- Never expose stack traces in production responses.
- Always include timestamp and correlation ID in error responses.
- Log exceptions with appropriate level (warn for client errors, error for server errors).
- Test each exception handler path.




## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
