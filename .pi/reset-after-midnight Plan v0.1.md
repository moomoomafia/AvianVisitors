Modify the AvianVisitors BirdFrame (`frame/`) to support an optional midnight reset while leaving the BirdNET station's existing display behavior unchanged.

### Configuration

Add the following option to BirdFrame's `config.toml`:

```toml
reset_at_midnight = true
```

Default to `false` for backward compatibility.

### Required behavior

When `reset_at_midnight = true`:

1. BirdFrame should display only bird species detected since midnight of the current day, based on the BirdNET station's local timezone.
2. At midnight, the logical detection window resets, but **DO NOT refresh, clear, or redraw the physical e-ink display**.
3. If no birds have been detected today, leave the previous day's collage visible, even if multiple days pass without detections.
4. When the first bird of the new day is detected, replace the previous collage with one containing only today's birds.
5. Continue refreshing throughout the day using the existing change-detection behavior as new birds are detected or relevant counts change.
6. Do not mix yesterday's birds with today's birds after the first detection of the new day.
7. If no detections exist within today's window, do not trigger a refresh solely because the date or detection window changed.
8. Existing periodic/healing refresh behavior must not replace the previous day's collage with a blank or no-birds screen.
9. Maintain existing display behavior when `reset_at_midnight = false`.

### Implementation considerations

- Investigate `frame/display.py`, `frame/shoot.py`, `frame/config.example.toml`, and the station's `avian/api/birdnet-api.php`.
- Reuse BirdFrame's existing detection-signature comparison and refresh logic where practical.
- Ensure accurate midnight boundaries without relying on rounded whole-hour windows.
- Prefer a minimal, maintainable implementation.
- An optional request-level API parameter is acceptable if required, provided existing API clients and the BirdNET website remain unaffected.
- Do not modify the station's global `RESET_AT_MIDNIGHT` setting.
- Do not delete or modify historical detections.
- Consider BirdNET station and BirdFrame timezone differences.
- Preserve existing image layout, refresh scheduling, quiet hours, and e-ink handling, except where explicitly required by the new behavior.

### Testing

Test at least these scenarios:

1. Midnight occurs with no new detections: display unchanged.
2. Several hours pass with no detections: display unchanged.
3. First detection after midnight: display switches to today's birds only.
4. Subsequent detections: display updates normally.
5. Multiple days without detections: last collage remains visible.
6. Periodic/healing refresh occurs before the first detection: previous collage remains visible.
7. Restart BirdFrame before the first detection: avoid clearing the existing display.
8. `reset_at_midnight = false`: original behavior preserved.

### Deliverables

Implement and test the change, update `config.example.toml` and the README, and summarize modified files and any required deployment or restart steps.