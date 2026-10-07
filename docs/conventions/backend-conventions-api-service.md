# Backend Conventions — API and Service Layer

**Scope: backend stacks** (invoke when `run-context.md > stack` is `backend-*`). Examples below target Java + Spring; translate idioms to Node/Python/Go/.NET as needed. The *principles* — thin controllers, business logic in services, DTO separation, explicit error model, sanitized logs, documented contracts — apply to any backend.

Applies to: relevant stage agents through the matching `skills/` helpers. Helpers inherit the caller’s role and write limits; verification helpers inspect and report only.

## Controllers

### Structure
- Thin controllers: validate, authorize, delegate, return DTO.
- Use `@Valid` for request validation.
- Keep endpoint behavior explicit and documented.
- Use `@Slf4j` for logging.
- Use `@AllArgsConstructor` or `@RequiredArgsConstructor` for dependency injection.
- Base path via `@RequestMapping` at class level.

### Response Patterns
- Use `ResponseEntity<T>` when status code control is needed.
- Direct DTO return for simple 200 OK responses (Spring handles serialization).
- Wrapper DTOs for responses combining metadata and data lists.

### Path Variable Naming
- Use camelCase for path variables: `/warehouse/{id}/{warehouseNumber}`.
- Match parameter names to path variable names.

### Input Sanitization
- Choose approved non-sensitive fields before logging; omit or mask sensitive values. `LogSanitizer` only removes control characters:
```java
log.info("Operation: {}", LogSanitizer.getSanitizedStringForLogging(safeOperationName));
```

### Structured Logging Keys
- Use consistent prefixes for log messages:
  - `APP-API-REQUEST-*`: API request logging
  - `APP-ERROR-*`: Error conditions
  - `APP-INTEGRATION-*`: External integration logging

## Services

### Structure
- Business logic belongs in services.
- Use `@Service` annotation.
- Use `@RequiredArgsConstructor` with `private final` fields.
- Define transactional boundaries clearly with `@Transactional`.
- Keep side effects explicit.

### Transaction Management
- Use `@Transactional` on methods requiring database transactions.
- Use `EntityManager.flush()` when explicit synchronization is needed.
- Use try-with-resources for I/O operations.

### Helper Methods
- Extract private static supplier methods for exception creation:
```java
private static Supplier<EntityNotFoundException> getNotFoundExceptionSupplier(Long id) {
    return () -> new EntityNotFoundException(Class.class, "Not found: " + id);
}
```

### Stream Patterns
- Use method references: `.map(mapper::toDto)`.
- Use `.toList()` (Java 16+) instead of `.collect(Collectors.toList())`.

## Error Model
- Use global exception handler (`@RestControllerAdvice`).
- Return consistent `ApiError` response structure.
- Include timestamp, status, a safe public message and a correlation identifier. Keep internal debug details in appropriately protected diagnostics.
- Sub-errors for validation failures.
- Avoid leaking internal stack details in API responses.
- Use `ResponseStatusException` for simple inline error cases.

## OpenAPI and Contracts

### Annotation Pattern
```java
@Operation(
    summary = "Brief description",
    description = "Detailed description with formatting"
)
@ApiResponses(value = {
    @ApiResponse(responseCode = "200", description = "Success",
        content = {@Content(mediaType = "application/json",
            schema = @Schema(implementation = ResponseDto.class))}),
    @ApiResponse(responseCode = "404", description = "Not found",
        content = @Content)
})
```

### Documentation Rules
- Keep API docs aligned with implementation.
- Use JavaDoc comments for endpoint documentation.
- Use text blocks for multi-line descriptions.
- Any contract-affecting change must be logged in `decision-log.md`.


