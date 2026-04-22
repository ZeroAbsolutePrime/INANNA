# NAMMU Intent Test Results

## Scope

This record captures the Phase 8.3b evidence for the NAMMU Intent Engine.
It combines:

- the confirmed model-validation examples embedded in `docs/implementation/CURRENT_PHASE.md`
- the implemented offline proof suite in `inanna/tests/test_nammu_intent.py`

## Model Targets

- Primary model: `qwen2.5-14b-instruct`
- Fallback model: `qwen2.5-7b-instruct-1m`
- Endpoint: `http://localhost:1234/v1/chat/completions`
- Timeout strategy:
  - primary `8s`
  - fallback `5s`

## Confirmed Intent Examples

These examples are the authoritative Phase 8.3b validation cases supplied in the active phase document and implemented against the same prompt contract in `inanna/core/nammu_intent.py`.

1. Input: `summarize my last 5 emails`
   Output: `intent=email_read_inbox`, `max_emails=5`, `output_format=summary`
   Confidence: `1.00`
   Expected latency class: primary model path

2. Input: `do I have anything urgent in my inbox?`
   Output: `intent=email_read_inbox`, `urgency_only=true`, `period=today`
   Confidence: `1.00`
   Expected latency class: primary model path

3. Input: `quick overview of yesterday's emails`
   Output: `intent=email_read_inbox`, `period=yesterday`, `output_format=summary`
   Confidence: `1.00`
   Expected latency class: primary model path

## Multilingual Expectations

Phase 8.3b explicitly requires the prompt and parser to support multilingual operator phrasing for this bridge layer. The active phase and Cycle 9 master plan name:

- English
- Spanish
- Catalan

The offline suite verifies the signal and comprehension path for non-English phrasing, including Spanish detection such as `correo urgente`. The prompt contract itself is language-agnostic and preserved verbatim in `NAMMU_EMAIL_PROMPT`.

## Offline Proof Suite

Implemented in: [test_nammu_intent.py](/C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/INANNA/inanna/tests/test_nammu_intent.py)

Coverage includes:

- `IntentResult` construction and success semantics
- conversion to tool requests
- mocked LLM success and failure handling
- graceful fallback to `intent="none"`
- deterministic inbox comprehension
- urgency detection
- contact grouping
- no-hallucination comprehension output
- quick domain-signal checks for English and Spanish inputs

## Notes

- Unit tests do not call the live LLM endpoint; they mock the HTTP layer by design.
- This preserves deterministic CI behavior while still proving the prompt contract, parser behavior, and fallback logic.
- Live model behavior remains grounded in the active phase’s confirmed validation examples above.
