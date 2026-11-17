# Implement BirdFrame Midnight Reset — Orchestrated Multi-Agent Workflow

## Project

Repository: `AvianVisitors`  
Feature branch: `feature/birdframe-midnight-reset`

Implement a configurable midnight-reset feature for the BirdFrame (`birdpic`) e-ink display while preserving the BirdNET listening station's existing behavior.

## 1. Your Role: Parent Orchestrator

You are the **parent orchestrator**, not the primary implementation worker.

Your responsibilities are to:
- Own the overall plan, requirements, acceptance criteria, and final result.
- Discover and use the subagents actually available in this Pi.dev environment.
- Delegate bounded units of work to specialized child agents.
- Maintain an ordered task queue and track progress.
- Review child results and determine the next task.
- Coordinate implementation, testing, verification, and documentation.
- Perform final integration and report the outcome.

**Do not implement the feature yourself by default.** Delegate implementation to worker agents. Perform direct work only when necessary for coordination, integration, or when a suitable child agent is unavailable.

### Available agent roles

Discover the installed subagent system and its actual agent definitions before starting.

Prefer these roles when available:

| Agent | Responsibility |
|---|---|
| **Scout** | Explore repository, locate relevant code, trace existing behavior, identify dependencies |
| **Oracle** | Independently evaluate architecture, master plan, requirements coverage, and potential drift |
| **Worker** | Implement narrowly scoped code changes |
| **Reviewer** | Independently review code, tests, regressions, and requirement compliance |
| **Tester** | Execute tests and investigate failures, if available |

If a named role is unavailable, use the closest existing agent capability. Do not invent unavailable agents or tools.

### Critical concurrency constraint

**MAXIMUM ONE ACTIVE CHILD AGENT AT ANY TIME.**

The machine has limited resources. Parallel subagent execution is prohibited.

Rules:

1. Maintain a FIFO task queue, allowing deliberate reprioritization when dependencies require it.
2. Dispatch only one child agent at a time.
3. Wait for that child to finish and release its resources before dispatching another.
4. Never invoke parallel subagent calls, batch dispatch, or use `Promise.all` for child execution.
5. Do not allow a child to spawn its own subagents. Maximum delegation depth: 1.
6. Never overlap Scout, Oracle, Worker, Reviewer, or Tester execution.
7. If the subagent system supports asynchronous/background execution, you may use it, but **do not start another child until the currently running child has completed**.
8. Keep orchestration in the parent session and preserve child findings between assignments.
9. A failed or timed-out child must be resolved, canceled, or confirmed terminated before dispatching the next child.

Run the queue autonomously without asking for permission between routine stages.

## 2. Feature Requirements

Add the following BirdFrame-specific configuration option:

```toml
reset_at_midnight = true
```

Default to `false` for backward compatibility.

When enabled, BirdFrame should:

1. Use the BirdNET station's local calendar date to define today's detection window, starting at 00:00.
2. Display only today's detected bird species once today's collage becomes active.
3. At midnight, logically reset the detection window **without clearing or refreshing the e-ink display**.
4. If no birds have been detected today, continue displaying the previous collage.
5. Keep that previous collage visible for as many days as necessary until a new bird is detected.
6. On the first detection of a new day, replace the retained collage with one containing only today's birds.
7. Continue refreshing normally as additional species or relevant counts change.
8. Never combine yesterday's detections with today's once the first detection triggers the new collage.
9. Never overwrite the retained collage with a blank/no-birds screen just because the daily window is empty.
10. Ensure existing periodic/healing refresh logic cannot inadvertently clear the collage while awaiting the first detection.
11. Preserve the displayed image across process restarts whenever possible.
12. Preserve existing behavior when `reset_at_midnight = false`.

### Isolation requirements

- Do not change the BirdNET station's normal rolling 24-hour display.
- Do not enable or modify the global station `RESET_AT_MIDNIGHT` setting.
- Do not modify or delete historical detections.
- Preserve existing e-ink rendering, layout, change detection, quiet hours, and refresh behavior except where the new feature explicitly requires changes.
- If an API change is necessary, make it optional, request-scoped, and backward compatible.
- Handle midnight boundaries and timezone differences accurately.
- Do not approximate the detection window by rounding elapsed time to whole hours.

## 3. Execution Plan — Sequential Agent Queue

### Phase 1: Discovery — Scout

Delegate to Scout:

- Explore `frame/display.py`, `frame/shoot.py`, `frame/config.example.toml`, `frame/README.md`, and `avian/api/birdnet-api.php`.
- Trace the complete detection API → BirdFrame → e-ink rendering pipeline.
- Identify change-detection signatures, periodic refresh triggers, cache behavior, and time handling.
- Determine how to preserve the displayed collage when the API returns no detections.
- Identify existing tests and the smallest safe implementation surface.
- Report findings with exact files/functions and potential risks.

Parent: Review findings and record implementation constraints.

### Phase 2: Architecture — Oracle

Delegate to Oracle:

- Review Scout's findings and all feature requirements.
- Recommend the smallest reliable implementation.
- Determine whether BirdFrame-only changes are sufficient or an optional API enhancement is needed.
- Evaluate midnight rollover, empty-day handling, timezone boundaries, healing refreshes, and application restarts.
- Identify risks, hidden assumptions, and acceptance criteria.
- Check whether the implementation plan introduces unnecessary complexity or deviates from the requested behavior.

Parent: Finalize the master plan and break it into independently verifiable worker tasks.

### Phase 3: Implementation — Worker

Delegate tasks to Worker sequentially, using separate assignments where beneficial:

**Task A — Data-window logic**
- Implement accurate today-only detection filtering when enabled.
- Keep existing rolling-window behavior when disabled.

**Task B — Refresh and collage retention**
- Prevent midnight alone from triggering a screen refresh.
- Retain the previous collage while today's detection set is empty.
- Switch to today's collage on the first detection.
- Ensure periodic refreshes and restarts do not blank the screen.

**Task C — Configuration and documentation**
- Update `config.example.toml`.
- Update `frame/README.md`.
- Document enabled and disabled behavior, configuration, deployment, and restart requirements.

Each worker assignment must:
- Have narrow scope and explicit acceptance criteria.
- Identify files it may change.
- Preserve unrelated behavior.
- Report modifications, assumptions, and outstanding issues.

Parent: Validate results after each assignment before dispatching the next.

### Phase 4: Independent Review — Reviewer

Delegate to Reviewer:

- Inspect the complete implementation and diff.
- Compare results against every requirement.
- Find potential regressions or unintended changes.
- Check API compatibility and correct timezone handling.
- Look for blank-screen paths, midnight refresh bugs, and signature-change edge cases.
- Review maintainability, error handling, and test coverage.
- Report findings by severity with file/line references.

Parent: Queue any necessary fixes to Worker, sequentially.

### Phase 5: Testing — Tester or Worker

Run existing tests and add focused coverage for:

1. Midnight with no new detections → screen unchanged.
2. Several hours without detections → screen unchanged.
3. First bird after midnight → today-only collage appears.
4. Additional birds during the day → normal updates.
5. Multiple days without detections → previous collage retained.
6. Periodic/healing refresh before first detection → no blank display.
7. Application restart before first detection → retained display preserved.
8. Empty API results → no destructive refresh.
9. Station and BirdFrame timezone differences.
10. `reset_at_midnight = false` → existing behavior unchanged.
11. API requests from other clients → unchanged behavior.

Where physical e-ink hardware is unavailable, use mocked display operations and verify whether a refresh would have been triggered. Clearly identify what still requires hardware testing.

### Phase 6: Final Oracle Audit

Return to Oracle after implementation, review, and testing.

Provide:
- Original requirements and acceptance criteria.
- Master plan.
- Scout findings.
- Implementation summary and diff.
- Reviewer findings and resolutions.
- Test results.

Ask Oracle to independently determine:
- Did the implementation drift from the original intent?
- Is every acceptance criterion satisfied?
- Did we accidentally change station-wide behavior?
- Is anything overengineered?
- Are there unresolved edge cases or regressions?
- Is the result ready for a pull request?

If Oracle identifies material issues, queue targeted fixes followed by another review/test cycle.

## 4. Parent Orchestration Rules

Maintain a concise task ledger containing:

- Task ID and phase
- Assigned agent
- Status: queued / running / completed / failed / blocked
- Dependencies
- Key findings and artifacts
- Remaining work

Keep the master requirements unchanged unless new evidence makes an adjustment necessary. Record and explain any adjustment.

Pass relevant findings to each subsequent agent so context is not lost.

Avoid unnecessary repeated repository exploration.

Favor small, focused changes over broad refactoring.

Do not have multiple agents editing files simultaneously.

Never allow child agents to recursively delegate.

Use existing project conventions, tooling, and test infrastructure.

Do not discard unrelated local changes.

Do not commit, push, or open a pull request without explicit authorization.

## 5. Completion Criteria

The feature is complete when:

- All stated requirements are implemented.
- The BirdNET station's existing display is unaffected.
- The physical BirdFrame display retains yesterday's collage until the first new bird of today.
- The first new detection replaces yesterday's collage with today's detections only.
- The existing rolling-window behavior works when the feature is disabled.
- Tests pass, or remaining hardware-dependent tests are clearly identified.
- Reviewer findings have been resolved.
- Oracle confirms alignment with the master plan.
- Configuration and documentation are updated.

## 6. Final Report

Provide a concise report containing:

1. **Result:** Completed / Partially completed / Blocked.
2. **Changes:** Files modified and behavior implemented.
3. **Agent execution:** Which agents were used and for what.
4. **Verification:** Tests passed, failed, or not run.
5. **Risks:** Remaining issues and hardware checks.
6. **Deployment:** How to enable the feature on `birdpic`.
7. **PR readiness:** Whether the changes are suitable for submission upstream.

### Begin

Start by discovering the available subagent capabilities and examining repository status.

Then construct the sequential task queue and begin with Scout.

**You are the orchestrator. Delegate the work. Only one child agent may execute at a time. Continue through implementation, review, testing, and the final Oracle audit without unnecessary user interaction.**