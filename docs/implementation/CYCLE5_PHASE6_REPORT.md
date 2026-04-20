## Cycle 5 Phase 5.6 Report

Phase 5.6 completed the dynamic Faculty Router layer.

`IntentClassifier` in [nammu.py](/C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/INANNA/inanna/core/nammu.py) now loads active faculties from `faculties.json`, builds its classification prompt dynamically, reads optional domain hints from `governance_signals.json`, and falls back cleanly to `crown` when a route is unknown or config is missing.

The runtime routing path now carries the routed faculty name through the structured status payload as `last_routed_faculty`, and both CLI and WebSocket flows include a clear SENTINEL stub response instead of an error if that route is selected before deployment.

Validation included updated NAMMU routing tests, the phase identity update, and a full `py -3 -m unittest discover -s tests` run before push.
