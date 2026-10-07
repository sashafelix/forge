# Backend Conventions — Quality, Observability, DevOps, Compliance

**Scope: backend stacks.** Examples below target Java + Maven + Spring Boot (JaCoCo, Micrometer Tracing, Logback, Spring Actuator). The *principles* — coverage target with exclusions for trivial classes, structured logging with traceable prefixes, profile-based config, externalized secrets, traceability from requirement → code → test → release — apply to any stack. Translate the mechanisms:
- Coverage: JaCoCo → c8 / Istanbul (Node), coverage.py (Python), `go test -cover`, Coverlet (.NET)
- Tracing: Micrometer Tracing → OpenTelemetry SDK (any stack)
- Logging: Logback → pino/winston (Node), structlog (Python), zap/zerolog (Go), Serilog (.NET)
- Profiles: Spring profiles → `NODE_ENV`/dotenv, `APP_ENV`, Go build tags, ASP.NET environments

Applies to: relevant stage agents through the matching `skills/` helpers. Helpers inherit the caller’s role and write limits; verification helpers inspect and report only.

## Contract Guard
- Validate API and schema compatibility.
- Explicitly label breaking vs non-breaking changes.

## Code Coverage (JaCoCo)

### Maven Configuration
```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>${jacoco.version}</version> <!-- approved project-managed version -->
    <executions>
        <execution>
            <id>prepare-coverage</id>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>coverage-report</id>
            <phase>verify</phase>
            <goals><goal>report</goal></goals>
        </execution>
        <execution>
            <id>jacoco-check</id>
            <phase>verify</phase>
            <goals><goal>check</goal></goals>
            <configuration>
                <excludes>
                    <exclude>com/example/generated/**</exclude>
                </excludes>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.80</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### Coverage Exclusions
Use only project-approved exclusions for generated or demonstrably trivial code. Do not exclude all model/DTO packages when they contain logic. The 80% threshold above is illustrative, not a pipeline-wide requirement.

Run the Maven `verify` lifecycle with a forked test JVM and retain the JaCoCo agent arguments if Surefire/Failsafe configures `argLine`; otherwise coverage may be absent. See [JaCoCo Maven documentation](https://www.jacoco.org/jacoco/trunk/doc/maven.html).

## Maven Profiles
```xml
<profiles>
    <profile>
        <id>local</id>
        <activation><activeByDefault>true</activeByDefault></activation>
        <properties><active-profiles>local</active-profiles></properties>
    </profile>
    <profile>
        <id>test</id>
        <properties><active-profiles>test</active-profiles></properties>
    </profile>
    <profile>
        <id>int</id>
        <properties><active-profiles>int</active-profiles></properties>
    </profile>
    <profile>
        <id>prod</id>
        <properties><active-profiles>prod</active-profiles></properties>
    </profile>
</profiles>
```

## Observability

### Structured Logging (Logstash)
```xml
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>${logstash-logback-encoder.version}</version> <!-- project-managed -->
</dependency>
```

### Distributed tracing

For the Spring Boot 3 reference stack, use Micrometer Tracing with a supported bridge and exporter selected through the project's dependency management. Do not add the older `spring-cloud-starter-sleuth` starter to a Boot 3 application. See [Spring Boot 3 tracing](https://docs.spring.io/spring-boot/3.5/reference/actuator/tracing.html).

### Log Prefixes for Traceability
- `APP-API-REQUEST-*`: API request logging
- `APP-ERROR-*`: Error conditions
- `APP-INTEGRATION-*`: External integration

### Actuator Configuration

Start with minimal exposure. Add metrics or other endpoints only under the project’s authentication/network policy; exposure is separate from authorization.
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health
  endpoint:
    health:
      probes:
        enabled: true
      show-details: never
```

### Observability Rules
- Add meaningful structured logs for key business flow transitions.
- Add metrics/traces for critical paths and failure points.
- Omit/mask sensitive fields before logging; `LogSanitizer` only removes control characters.

## Caching
```java
@SpringBootApplication
@EnableCaching
public class Application { ... }

@Bean
public Caffeine caffeineConfig() {
    return Caffeine.newBuilder()
        .expireAfterWrite(60, TimeUnit.MINUTES);
}
```

## Scheduling
```java
@SpringBootApplication
@EnableScheduling
public class Application { ... }
```

## DevOps

### Docker Configuration
```dockerfile
FROM openjdk:21
ARG JAR_FILE=target/app*.jar
WORKDIR /opt/app
COPY ${JAR_FILE} app.jar
RUN mkdir /opt/app/tmp
ENTRYPOINT ["java", "-Djava.io.tmpdir=/opt/app/tmp", "-jar", "app.jar"]
VOLUME /opt/app/tmp
```

### CI/CD Rules
- CI/CD must enforce tests and quality gates.
- Keep environment configs separated.
- Keep secrets external to repo.

## Application Configuration

### Profile-Based Config Files
| Profile | File | Purpose |
|---------|------|---------|
| default | `application.yml` | Base configuration |
| local | `application-local.yml` | Local development |
| int | `application-int.yml` | Integration environment |
| test | `application-test.yml` | Test environment |
| prod | `application-prod.yml` | Production |

### Configuration Properties Class
```java
@Configuration
@ConfigurationProperties(prefix = "app-name")
public class AppProperties {
    private List<String> cors;
    // getters/setters
}
```

## Compliance
- Maintain traceability from requirement -> code -> test -> release artifact.
- Keep release evidence concise and linked.

## Decision Management
- Story-level decisions are append-only in `decision-log.md`.
- Global index updated with links/summaries only.


