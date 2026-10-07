---
name: skill-api-service
description: "Implement controller/service/validation/error handling for backend APIs. Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-api-service

## Purpose
Implement controller/service/validation/error handling for backend APIs.

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-java-style.md`
- `docs/conventions/backend-conventions-api-service.md`
- `docs/conventions/backend-conventions-testing-style.md`

## Writes
- controller/service/DTO/exception handler files in scope
- contract-impact notes in `docs/agent/runs/{story_id}/decision-log.md`

## Controller Conventions

### Structure
```java
@Slf4j
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {
    private final OrderService orderService;

    @GetMapping("/{id}")
    public ResponseEntity<OrderDto> getOrder(@PathVariable Long id) {
        return ResponseEntity.ok(orderService.findById(id));
    }

    @PostMapping
    @PreAuthorize("hasAuthority('ORDER_CREATE')")
    public ResponseEntity<OrderDto> createOrder(@Valid @RequestBody CreateOrderRequest request) {
        log.info("Creating order"); // correlation ID supplied by the logging context
        return ResponseEntity.status(HttpStatus.CREATED).body(orderService.create(request));
    }
}
```

### Rules
- `@Slf4j` for logging.
- `@RequiredArgsConstructor` for DI.
- Base path via `@RequestMapping` at class level.
- Use `ResponseEntity<T>` for status control.
- Use `@Valid` on `@RequestBody`.
- Use `@PreAuthorize` for role-based access.
- Log only approved non-sensitive fields. `LogSanitizer` removes control characters; it does not mask secrets, PII or full request bodies.

### OpenAPI Documentation
```java
@Operation(
    summary = "Get order by ID",
    description = "Returns order details for the given ID"
)
@ApiResponses({
    @ApiResponse(responseCode = "200", description = "Order found",
        content = @Content(schema = @Schema(implementation = OrderDto.class))),
    @ApiResponse(responseCode = "404", description = "Order not found",
        content = @Content(schema = @Schema(implementation = ApiError.class)))
})
@GetMapping("/{id}")
public ResponseEntity<OrderDto> getOrder(@PathVariable Long id) { ... }
```

## Service Conventions

### Structure
```java
@Service
@RequiredArgsConstructor
@Slf4j
public class OrderService {
    private final OrderRepository orderRepository;
    private final OrderMapper orderMapper;

    @Transactional(readOnly = true)
    public OrderDto findById(Long id) {
        return orderRepository.findById(id)
            .map(orderMapper::toDto)
            .orElseThrow(() -> new EntityNotFoundException(Order.class, "id", id.toString()));
    }

    @Transactional
    public OrderDto create(CreateOrderRequest request) {
        Order order = orderMapper.toEntity(request);
        return orderMapper.toDto(orderRepository.save(order));
    }
}
```

### Rules
- `@Service` annotation.
- `@RequiredArgsConstructor` for DI, `final` fields.
- Use Stream API with mapper method references.
- Role-based logic via `UserContextHolder`.

### UserContextHolder Usage
```java
public class UserContextHolder {
    public static String getUsername() {
        UserDetails user = getUserInfo();
        return user != null ? user.getUsername() : "System";
    }

    public static boolean hasUserRole(String role) {
        UserDetails user = getUserInfo();
        return user != null && user.getAuthorities().stream()
            .anyMatch(a -> a.getAuthority().equals(role));
    }
}
```

Use in service:
```java
if (UserContextHolder.hasUserRole("ADMIN")) {
    // admin-only logic
}
```

## DTO Conventions

### Request DTOs
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CreateOrderRequest {
    @NotNull
    private Long customerId;

    @NotEmpty
    private List<OrderItemRequest> items;
}
```

### Response DTOs
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(of = "id", callSuper = false)
public class OrderDto extends AbstractAuditingDTO {
    private Long id;
    private String orderNumber;
    private OrderStatus status;
    private List<OrderItemDto> items;
}
```

## Guardrails
- Thin controllers: business logic lives in services.
- Explicit validation with `@Valid` and Bean Validation.
- Consistent error payloads via `skill-exception-handling`.
- Maintain OpenAPI/contract compatibility unless approved.
- Log user input only after sanitization.




## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
