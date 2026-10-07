---
name: skill-security
description: "Apply backend security controls for endpoints, data access, and logging. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-security

## Purpose
Apply backend security controls for endpoints, data access, and logging.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-security.md`
- `docs/conventions/backend-conventions-testing-style.md`

## Writes
- security config and authorization annotations in scope
- security-focused tests in scope
- decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Security Configuration

Use the project's authentication mechanism with fail-closed authorization, explicit endpoint policy and applicable CSRF protection. See `docs/conventions/backend-conventions-security.md` for the shared rules. Do not blanket-permit Actuator/docs endpoints or copy a permit-all local profile into a shared environment.

`@PreAuthorize` requires method security to be enabled; test with the actual application security configuration, not only an annotation in isolation.

### Authorization Annotations
```java
@PreAuthorize("hasAuthority('ADMIN')")
@GetMapping("/admin/users")
public List<UserDto> getUsers() { ... }

@PreAuthorize("hasAnyAuthority('USER', 'ADMIN')")
@GetMapping("/orders")
public List<OrderDto> getOrders() { ... }
```

## Log Sanitization Utility

This skill owns the `LogSanitizer` utility to prevent log injection (CWE-117):

```java
public final class LogSanitizer {
    private LogSanitizer() {}

    public static String getSanitizedStringForLogging(@Nullable String input) {
        if (input == null) return "";
        return input
            .replace('\n', '_')
            .replace('\r', '_')
            .replace('\t', '_');
    }
}
```

This removes control characters only; it does not redact secrets or PII. First select approved non-sensitive fields, then sanitize those fields if needed. Never log raw user input or whole request bodies. Example for an already approved non-sensitive value:
```java
log.info("Operation: {}", LogSanitizer.getSanitizedStringForLogging(safeOperationName));
```

## Security Testing

### Controller Security Test Pattern
```java
@WebMvcTest(OrderController.class)
@Import(MethodSecurityConfig.class)
class OrderControllerSecurityTest {
    @Autowired
    private MockMvc mvc;

    @Test
    @WithMockUser(authorities = "ADMIN")
    void adminEndpoint_withAdmin_shouldSucceed() throws Exception {
        mvc.perform(get("/api/admin/orders"))
            .andExpect(status().isOk());
    }

    @Test
    @WithMockUser(authorities = "USER")
    void adminEndpoint_withUser_shouldForbid() throws Exception {
        mvc.perform(get("/api/admin/orders"))
            .andExpect(status().isForbidden());
    }

    @Test
    @WithAnonymousUser
    void protectedEndpoint_anonymous_shouldUnauthorize() throws Exception {
        mvc.perform(get("/api/orders"))
            .andExpect(status().isUnauthorized());
    }
}
```

## Guardrails
- Fail closed: deny by default, permit explicitly.
- No secret exposure in logs, errors, or responses.
- Omit/mask sensitive fields before logging; `LogSanitizer` only handles control characters.
- Test both positive (authorized) and negative (unauthorized) access paths.
- Use test identities for development; a local profile is not a security boundary.

## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
