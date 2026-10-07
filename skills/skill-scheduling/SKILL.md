---
name: skill-scheduling
description: "Implement `@Scheduled` background tasks for periodic backend jobs (imports, syncs, cleanup, etc.). Use when this capability is relevant to the assigned stage and target stack."
---

# Skill: skill-scheduling

## Purpose
Implement `@Scheduled` background tasks for periodic backend jobs (imports, syncs, cleanup, etc.).

## Reads
- `docs/conventions/backend-conventions-general.md`
- `docs/conventions/backend-conventions-api-service.md`
- `docs/conventions/backend-conventions-quality-ops.md`

## Writes
- `@Scheduled` method implementations in relevant service classes
- scheduling configuration if needed
- scheduled task tests in scope
- decision notes in `docs/agent/runs/{story_id}/decision-log.md`

## Conventions

### Application Bootstrap
Enable scheduling on the main application class:
```java
@SpringBootApplication
@EnableScheduling
public class AiPipelineApplication { ... }
```

### Scheduled Task Pattern
```java
@Service
@Slf4j
@RequiredArgsConstructor
public class DailyImportService {

    private final ImportService importService;

    /**
     * Runs daily at 02:00 Amsterdam time.
     * Imports fresh data from external source.
     */
    @Scheduled(cron = "0 0 2 * * *", zone = "Europe/Amsterdam")
    public void runDailyImport() {
        log.info("APP-SCHEDULER: Starting daily import");
        try {
            importService.runImport();
            log.info("APP-SCHEDULER: Daily import completed successfully");
        } catch (Exception e) {
            log.error("APP-SCHEDULER: Daily import failed: {}", e.getMessage(), e);
        }
    }
}
```

### Cron Format
```
┌─── second (0-59)
│  ┌─── minute (0-59)
│  │  ┌─── hour (0-23)
│  │  │  ┌─── day of month (1-31)
│  │  │  │  ┌─── month (1-12)
│  │  │  │  │  ┌─── day of week (0-7, 0 and 7 = Sunday)
│  │  │  │  │  │
"0  0  2  *  *  *"  = 02:00 every day
"0  */30 * *  *  *"  = every 30 minutes
"0  0  6  *  *  MON-FRI" = 06:00 on weekdays
```

### Fixed Rate / Fixed Delay
```java
// Run every 5 minutes, measured from start of last execution
@Scheduled(fixedRate = 5 * 60 * 1000)
public void syncPeriodically() { ... }

// Run 5 minutes after last execution completes
@Scheduled(fixedDelay = 5 * 60 * 1000)
public void syncWithDelay() { ... }
```

### Externalize Schedule Configuration
```yaml
# application.yml
scheduler:
  daily-import:
    cron: "0 0 2 * * *"
    zone: "Europe/Amsterdam"
```

```java
@Scheduled(cron = "${scheduler.daily-import.cron}", zone = "${scheduler.daily-import.zone}")
public void runDailyImport() { ... }
```

## Error Handling
- Always wrap scheduled logic in try/catch.
- Log errors with structured prefix (e.g., `APP-SCHEDULER:`).
- Define and test the scheduler’s error handling and recurrence behaviour. Do not assume every thrown exception stops every Spring scheduler; behaviour depends on the task and error handler.

## History / Audit Tracking
Record scheduled job outcomes in a history table:
```java
historyService.recordJobRun("daily-import", totalProcessed, successCount, failCount);
```

## Testing
Scheduled methods should be tested by calling them directly (not by waiting for the schedule):
```java
@Test
void runDailyImport_withValidData_shouldComplete() {
    when(importService.runImport()).thenReturn(true);
    dailyImportService.runDailyImport();
    verify(importService, times(1)).runImport();
}
```

## Guardrails
- Externalize cron expressions to config — never hardcode in production.
- Report failures through the configured error handler or an explicit catch; test subsequent execution and avoid silently swallowing failures.
- Log entry and exit of every scheduled job.
- Document schedule rationale and timezone in decision log.
- Test scheduled logic directly (unit), not by triggering schedule timer.




## Library and authority

Resolve `docs/`, `agents/` and `skills/` references from the Forge library root. Resolve `{project_root}` against the selected target. Read `AGENTS.md` and `skills/README.md`; load only relevant references. Inherit the caller's stage, tool permissions and write scope; read-only reviewers report findings. Return control to the caller.
