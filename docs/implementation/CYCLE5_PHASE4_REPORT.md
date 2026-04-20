## Cycle 5 Phase 5.4 Report

Phase 5.4 completed in two parts.

Part A removed routine memory proposals from normal conversation turns. Memory now auto-writes through the existing memory store at the 20-turn threshold and again at session end, while explicit memory actions such as `remember this`, `forget`, and related governed flows remain proposal-based.

Part B adds the Process Monitor surface. `inanna/core/process_monitor.py` now reports INANNA server and LM Studio status, `process-status` is available in both CLI and WebSocket paths, and the Processes panel in `console.html` loads live records and refreshes every 30 seconds while visible.

Validation included updated command, state, and identity expectations, a new `test_process_monitor.py`, and a full `py -3 -m unittest discover -s tests` run before push.
