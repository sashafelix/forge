# Backend Conventions — Entity, Repository, Mapper

**Scope: backend stacks with an ORM and DTO layer.** Examples below target Java + JPA + Lombok + MapStruct. The *principles* — audit fields on mutable entities, business-key equality, explicit fetch/cascade, DTO↔entity separation via a mapper — generalize to Node + TypeORM/Prisma, Python + SQLAlchemy/Django, Go + GORM, .NET + EF Core. Adapt idioms to the stack.

Applies to: relevant stage agents through the matching `skills/` helpers. Helpers inherit the caller’s role and write limits; verification helpers inspect and report only.

## Base Entity Pattern

All mutable entities extend `AbstractBaseEntity`:
```java
@Data
@MappedSuperclass
public abstract class AbstractBaseEntity implements Serializable {
    private static final long serialVersionUID = 1L;

    @CreationTimestamp
    @Column(name = "date_created", nullable = false, updatable = false)
    private LocalDateTime dateCreated;
    
    @Column(name = "user_created", updatable = false)
    private String userCreated;
    
    @UpdateTimestamp
    @Column(name = "date_changed")
    private LocalDateTime dateChanged;
    
    @Column(name = "user_changed")
    private String userChanged;

    @PrePersist
    public void prePersist() {
        setUserCreated(UserContextHolder.getUsername());
        setUserChanged(UserContextHolder.getUsername());
    }

    @PreUpdate
    public void preUpdate() {
        setUserChanged(UserContextHolder.getUsername());
    }
}
```

## Entity Annotations Pattern
```java
@Entity
@Data
@Table(name = "warehouse")
@EqualsAndHashCode(onlyExplicitlyIncluded = true, callSuper = false)
public class Warehouse extends AbstractBaseEntity implements Serializable {
    @Serial
    private static final long serialVersionUID = 1L;

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "warehouse_generator")
    @SequenceGenerator(name = "warehouse_generator", sequenceName = "warehouse_seq", allocationSize = 1)
    private Long id;

    @Column(nullable = false)
    @EqualsAndHashCode.Include
    private String warehouseNumber;  // Business key

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "organization_fk", referencedColumnName = "id")
    @ToString.Exclude
    private Organization organization;

    @OneToMany(fetch = FetchType.LAZY, mappedBy = "warehouse", cascade = CascadeType.ALL, orphanRemoval = true)
    @ToString.Exclude
    private List<Address> addresses = new ArrayList<>();
}
```

## Entity Rules
- Extend `AbstractBaseEntity` for audit support.
- Implement `Serializable` with `serialVersionUID`.
- Use `@EqualsAndHashCode(onlyExplicitlyIncluded = true, callSuper = false)`.
- Use `@EqualsAndHashCode.Include` on business key fields (not ID).
- Use `@ToString.Exclude` on relationships to prevent infinite loops.
- Match sequence allocation to the actual database sequence and project strategy; allocation size 1 is an example, not a PostgreSQL requirement.
- Explicit `@Column` constraints: `nullable = false` for required fields.
- Lazy fetch for collections, explicit cascade rules.
- Use `orphanRemoval = true` for owned collections.
- Avoid business-heavy logic in entities (simple derived properties OK).

## Derived Properties in Entities
Entities may contain simple computed/derived properties:
```java
public String getFullName() {
    StringBuilder sb = new StringBuilder(this.getName());
    if (StringUtils.isNotBlank(this.getAdditionalName())) {
        sb.append(" ").append(this.getAdditionalName());
    }
    return sb.toString();
}
```

## View Entity Pattern (Read-Only)
For database views, use immutable entities:
```java
@Entity
@Getter
@Setter
@Immutable
@Table(name = "warehouse_overview")
public class WarehouseOverview {
    @Id
    String warehouseNumber;
    
    // Manual equals/hashCode on business key
    @Override
    public boolean equals(Object o) { ... }
    @Override
    public int hashCode() { ... }
}
```
- Use `@Immutable` annotation.
- Use `@Getter/@Setter` instead of `@Data`.
- Do **not** extend `AbstractBaseEntity`.
- Manual `equals()`/`hashCode()` on business key.

## Repositories
- Use Spring Data repositories with explicit query intent.
- Annotate with `@Repository`.
- Keep repository methods focused and readable.
- Use query derivation method names.
- Return entities directly (mapping in service/mapper layer).

```java
@Repository
public interface WarehouseRepository extends JpaRepository<Warehouse, Long> {
    Warehouse findByWarehouseNumberAndOrganizationCode(String warehouseNumber, String organizationCode);
    Optional<WarehouseOverview> findByIdAndWarehouseNumberAndWarehouseStatusTrueAndWarehouseHiddenFalse(Long id, String warehouseNumber);
}
```

## Base DTO Pattern
```java
@Data
public abstract class AbstractAuditingDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @ReadOnlyProperty
    private LocalDateTime dateCreated;

    @ReadOnlyProperty
    private LocalDateTime dateChanged;
}
```

## DTO Conventions
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode(of = "id", callSuper = false)
public class WarehouseDto extends AbstractAuditingDTO implements Serializable {
    private Long id;
    private String name;
    
    @Singular
    private List<AddressDto> addresses;  // Use @Singular with @Builder
}
```
- Lombok `@Data`, `@Builder`, `@NoArgsConstructor`, `@AllArgsConstructor`.
- Implement `Serializable`.
- Extend `AbstractAuditingDTO` for audit fields.
- Explicit `@EqualsAndHashCode` based on ID.
- Use `@Singular` for collection fields with `@Builder`.
- Separate request/response DTOs in subpackages.

## EntityMapper Base Interface
```java
public interface EntityMapper<D, E> {
    D toDto(E e);
    E toEntity(D d);
    List<D> toDto(List<E> eList);
    List<E> toEntity(List<D> dList);
}
```

## MapStruct Mapper Conventions
```java
@Mapper(componentModel = "spring")
public interface WarehouseMapper extends EntityMapper<WarehouseDto, Warehouse> {

    @Mapping(target = "organizationCode", expression = "java(warehouse.getOrganization() != null ? warehouse.getOrganization().getCode() : null)")
    @Mapping(target = "name", expression = "java(warehouse.getFullName())")
    @Mapping(target = "warehouseType", source = "warehouseTypeArchitectural")
    WarehouseDto toDto(Warehouse warehouse);
}
```

### Composed Mappers
```java
@Mapper(componentModel = "spring", uses = {
    AddressMapper.class,
    CommunicationMapper.class
})
public interface WarehouseDetailMapper { ... }
```

### Mapper Decorators
```java
@Mapper(componentModel = "spring", uses = {...})
@DecoratedWith(WarehouseDecorator.class)
public interface XmlWarehouseMapper {
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "organization", ignore = true)
    Warehouse xmlToEntity(DataRecord record);
}
```

## Maven Configuration (MapStruct + Lombok)
```xml
<annotationProcessorPaths>
    <path><groupId>org.mapstruct</groupId><artifactId>mapstruct-processor</artifactId></path>
    <path><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId></path>
    <path><groupId>org.projectlombok</groupId><artifactId>lombok-mapstruct-binding</artifactId></path>
</annotationProcessorPaths>
<compilerArgs>
    <compilerArg>-Amapstruct.defaultComponentModel=spring</compilerArg>
</compilerArgs>
```

## Guardrails
- No entity leakage in controller responses.
- Ensure mapping updates whenever fields change.
- Explicitly map required fields. Use `ignore = true` only for intentionally excluded fields; do not silence missing mappings that affect the contract.


