# Backend Conventions — Java Style

**Scope: Java/Spring backends only.** Invoke when `run-context.md > stack` is `backend-java`. The *Code Simplicity Rules* at the bottom of this file (small functions, Rule of Three, no dead code, don't-mock-what-you-don't-own) are general review guidance; everything else in this file is Java-specific.

Applies to: relevant stage agents through the matching `skills/` helpers. Helpers inherit the caller’s role and write limits; verification helpers inspect and report only.

## Class and Dependency Style
- Constructor injection only (`@RequiredArgsConstructor`).
- Dependency fields are `private final`.
- Keep class-level annotations grouped and consistent.
- Use `@Slf4j` for logging.

### Standard Class Annotation Order
```java
@Service  // or @RestController, @Configuration, etc.
@Slf4j
@RequiredArgsConstructor
public class MyService { ... }
```

## Function Style
- Method names are verb-first and behavior-specific.
- Prefer small methods; extract helper methods when branching grows.
- Return early on validation/guard conditions.
- Avoid `null` returns for collections; return empty collections.
- Keep side effects explicit (no hidden writes in mappers/util helpers).

## Controller Function Pattern
- Validate input (`@Valid`), authorize (`@PreAuthorize`), delegate to service.
- Do not embed business rules in controller methods.
- Sanitize user-controlled values before logging.

```java
@PreAuthorize("hasAuthority('User')")
@PutMapping("/warehouse")
public void updateMetadata(@Valid @RequestBody UpdateMetadataRequest request) {
    log.debug("Updating metadata"); // correlation ID comes from logging context
    request.getMetadataList().forEach(metadataService::updateMeta);
}
```

## Service Function Pattern
- Service contains business logic and transaction boundary.
- Keep orchestration readable; split deep logic into private helpers.
- Use Supplier pattern for exception creation:
```java
private static Supplier<EntityNotFoundException> getNotFoundSupplier(Long id) {
    return () -> new EntityNotFoundException(MyDto.class, "Not found: " + id);
}
```

## Stream API Patterns
- Use method references where possible: `.map(mapper::toDto)`.
- Use `.toList()` (Java 16+) instead of `.collect(Collectors.toList())`.
- Use Predicate factory methods for complex filters:
```java
private static Predicate<Communication> getPhonePredicate() {
    return c -> c.getType().equals(CommunicationType.PHONE);
}

return communications.stream()
    .filter(getPhonePredicate())
    .findAny()
    .flatMap(this::getPhoneNumber)
    .orElse("");
```

## Optional Patterns
```java
// Chained operations
return repository.findById(id)
    .map(mapper::toDto)
    .orElseThrow(getNotFoundSupplier(id));

// flatMap for nested Optionals
.flatMap(c -> Optional.ofNullable(c.getEmail()))
.orElse("");

// ifPresentOrElse for branching
optional.ifPresentOrElse(
    value -> { /* present */ },
    () -> { /* absent */ }
);
```

## Try-With-Resources
Always use for I/O operations:
```java
try (CustomZipInputStream zis = new CustomZipInputStream(inputStream)) {
    // process stream
} catch (Exception e) {
    log.error("Error processing: {}", e.getMessage(), e);
}
```

## Logging

### Parameterized Logging
```java
log.info("Processing warehouse: {} with status: {}", warehouseId, status);
log.debug("Request accepted"); // do not log the request body
log.error("APP-ERROR-IMPORT: {}", e.getLocalizedMessage(), e);
```

### Structured Log Prefixes
Use consistent prefixes for traceability:
- `APP-API-REQUEST-*`: API request logging
- `APP-ERROR-*`: Error conditions
- `APP-INTEGRATION-*`: External integration logging

### Rules
- Never log secrets/tokens.
- Omit/mask sensitive data; sanitize control characters only in approved non-sensitive fields. `LogSanitizer` is not a redactor.
- Include exception with stack trace: `log.error("msg: {}", e.getMessage(), e)`.

## AtomicInteger for Stream Counters
When counting in lambda/stream operations:
```java
AtomicInteger totalAdded = new AtomicInteger();
items.forEach(item -> {
    process(item);
    totalAdded.incrementAndGet();
});
log.info("Total added: {}", totalAdded.get());
```

## DateTime Handling
```java
// Store in UTC
private ZonedDateTime lastSyncDate = ZonedDateTime.now(ZoneId.of("UTC"));

// Display in local timezone
public String dateAsString() {
    ZonedDateTime localTime = lastSyncDate.withZoneSameInstant(ZoneId.of("Europe/Amsterdam"));
    return localTime.format(DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm z"));
}
```

## Minimal Function Skeleton
```java
public ResponseDto doAction(@Valid RequestDto request) {
    if (request == null) {
        throw new IllegalArgumentException("request is required");
    }
    var result = domainService.execute(request);
    return mapper.toResponse(result);
}
```

## Code Simplicity Rules
- **Write simple, boring code.** Clever code is a liability; readable code is an asset.
- **Rule of Three**: don't abstract until a pattern appears 3+ times. Premature DRY creates coupling.
- **Prefer composition over inheritance**: use interfaces and delegation; reserve inheritance for true is-a relationships.
- **Delete dead code aggressively**: no commented-out blocks, no unused imports, no orphaned methods. Version control is your backup.
- **Keep files focused**: split when a class exceeds ~300 lines or has more than 2 responsibilities.
- **Functions do one thing**: if you need the word "and" to describe what a function does, split it.
- **Don't mock what you don't own**: for external boundaries (REST clients, message brokers), use integration tests or test containers instead of mocking third-party APIs directly.


