# DESIGN SPECIFICATION · Multi-Agent Development Platform
## DGX Spark + Laptop + NVIDIA Cloud: Building INANNA NYX with AI Teams

**Ring: Evaluation / Strategic Architecture**
**Version: 1.0 · Date: 2026-04-25**
**Author: Claude (Command Center)**
**Guardian: INANNA NAMMU**

---

> *"The triangle of Cycles 1-9 (INANNA NAMMU + Claude + Codex)*
> *worked for sequential document-driven development.*
> *The next spiral requires agents working in parallel*
> *on different organs with shared context."*
> — Spiral Log, 2026-04-24

---

## Part I: The Hardware Picture

### What the DGX Spark Actually Provides (October 2025)

```
Hardware:
  GB10 Grace Blackwell Superchip
  128 GB unified memory (CPU + GPU share one coherent pool)
  20-core ARM CPU (10x Cortex-X925 + 10x Cortex-A725)
  1 petaFLOP FP4 AI performance
  4 TB NVMe SSD
  150 × 150 × 50.5 mm (slightly larger than Mac Mini)
  ~60W idle, ~300W peak
  Price: $3,999-$4,699

Unified Memory Advantage:
  No VRAM ceiling. Any model up to 128GB runs at full speed.
  70B FP16 model: runs on single DGX Spark ($3,999)
  vs. alternative: two H100 80GB cards ($60,000+)

What ships pre-installed:
  DGX OS (Linux/Ubuntu-based)
  90-day NVIDIA AI Enterprise license (renewable)
  CUDA, cuDNN
  NIM microservices
  NeMo framework (fine-tuning)
  Triton Inference Server
  Access to: Omniverse, Isaac, Metropolis frameworks

Model support (pre-optimized):
  DeepSeek R1 (70B)
  Meta Llama 3.x (8B, 70B)
  Qwen3-32B (excellent for structured output)
  Google Gemma
  NVIDIA Nemotron 3 Nano (30B total, 3B active — multi-agent optimized)
  GPT-OSS-120B (with two Sparks connected via NVLink)

Scaling:
  Two DGX Sparks connected → 405B parameter models
  Four DGX Sparks → 700B parameter models
  Low-latency RoCE networking between nodes
```

### The Laptop (Client)

```
Role: Operator interface + local tool execution
OS: NixOS (target) or Windows (current)
Network: connects to DGX Spark via local network or Tailscale VPN
What runs here:
  - INANNA NYX client (browser UI)
  - Local file access (email, documents, desktop)
  - Desktop automation (AT-SPI2 on NixOS)
  - Lightweight local model (optional, for offline fallback)
What does NOT run here:
  - 70B model inference (too heavy)
  - Agent orchestration (runs on DGX)
  - Vector memory store (runs on DGX)
```

### NVIDIA Cloud Services (Research Research License)

```
Available through NVIDIA AI Enterprise:
  NIM microservices (cloud inference for overflow/burst)
  NGC registry (pre-optimized containers)
  NVIDIA build.nvidia.com (API access to hosted models)

For the research use case:
  Local DGX is primary (sovereign, no cloud dependency)
  NVIDIA cloud is secondary (burst, large models, fine-tuning overflow)
  Cost model: pay-per-token for cloud, flat for local DGX
```

---

## Part II: The NVIDIA Agent Framework Stack

### What Exists Today (2026)

**NeMo Agent Toolkit** is an open-source library for connecting, evaluating,
and accelerating teams of AI agents. It provides plugin-based observability
through an event-driven architecture that traces every step of agent workflows
and exports telemetry to platforms like Phoenix, Langfuse, or any
OpenTelemetry-compatible service.

It supports full MCP (Model Context Protocol) — usable as an MCP client
to connect to remote MCP servers, or as an MCP server to publish tools.
It also supports A2A (Agent-to-Agent) Protocol — agents can delegate
tasks to each other through a discoverable network.

**NemoClaw** (part of NVIDIA Agent Toolkit) is an open-source agent
development platform for building, evaluating, and optimizing safer,
long-running autonomous agents directly from the desktop, adding security
and privacy controls.

**NIM microservices** expose OpenAI-compatible HTTP APIs, enabling
drop-in replacement for applications using OpenAI client libraries.
Each NIM container packages a specific model with an optimized
inference runtime.

**What this means for INANNA NYX:**
The entire NVIDIA agent stack is MCP-compatible and OpenAI-API-compatible.
INANNA NYX already uses OpenAI-compatible endpoints (LM Studio).
Migration from LM Studio to NIM on DGX Spark requires changing one URL.
The NeMo Agent Toolkit can orchestrate multiple INANNA organs as agents.

---

## Part III: The Multi-Agent Architecture Design

### The Core Insight

The Cycles 1-9 triangle had one fatal constraint:
**sequential execution** — one phase, one agent, one conversation at a time.

The next platform needs **parallel execution** — multiple specialized agents
working simultaneously on different organs, coordinated by a shared memory
and a governance agent.

The DGX Spark makes this possible. 128GB unified memory can run:
- One 70B model (primary intelligence — CROWN + ANALYST)
- Multiple 7-14B models simultaneously (specialist agents)
- Vector memory store (ChromaDB — semantic memory)
- NeMo Agent Toolkit orchestrator
- All INANNA NYX organ processes

Everything on one machine. Sovereign. No cloud dependency for core work.

### The Agent Team

```
INANNA NYX Multi-Agent Development Platform
════════════════════════════════════════════════════════

HUMAN LAYER (Laptop)
  INANNA NAMMU — Guardian, final authority, proposal approver

DGX SPARK LAYER
  ┌─────────────────────────────────────────────────────┐
  │                 ATLAS KEEPER AGENT                  │
  │  Reads Atlas before every session.                  │
  │  Maintains constitutional compliance.               │
  │  Blocks any commit that violates foundational laws. │
  │  Model: Qwen3-32B (structured reasoning)            │
  └─────────────────┬───────────────────────────────────┘
                    │ governs all agents below
  ┌─────────────────┼───────────────────────────────────┐
  │         ARCHITECT AGENT                             │
  │  Reads Atlas + current phase document.              │
  │  Designs phases, writes CURRENT_PHASE.md.           │
  │  Never writes implementation code.                  │
  │  Outputs: phase documents, organ design specs.      │
  │  Model: 70B (DeepSeek R1 or Llama 3.3 70B)         │
  └─────────────────┬───────────────────────────────────┘
                    │ assigns work to builder agents
  ┌──────┬──────────┼──────────┬──────────┬─────────────┐
  │      │          │          │          │             │
  ▼      ▼          ▼          ▼          ▼             ▼
NAMMU  MEMORY   ANALYST   GUARDIAN  OPERATOR    SENTINEL
BUILDER BUILDER  BUILDER   BUILDER   BUILDER     BUILDER
Agent   Agent    Agent     Agent     Agent       Agent

  Each Builder Agent:
    - Reads the relevant organ card from Atlas
    - Reads the phase document for their organ
    - Reads Error Memory for past failures on this organ
    - Reads Procedural Memory for verified patterns
    - Implements code changes
    - Runs tests
    - Writes handoff report
    - Commits to git feature branch
    Model: Nemotron 3 Nano (30B total, 3B active)
           or Qwen3-32B for complex organs

  ┌─────────────────────────────────────────────────────┐
  │                  REVIEWER AGENT                     │
  │  Reads implementation after each Builder.           │
  │  Runs full test suite.                              │
  │  Checks Atlas compliance.                           │
  │  Approves or returns to Builder.                    │
  │  Never merges without Atlas compliance.             │
  │  Model: Qwen3-32B (structured output + reasoning)   │
  └─────────────────────────────────────────────────────┘
```

### The Memory System for the Agent Team

All agents share the MemoryBus. Each reads and writes to their permitted layers.

```
Shared across all agents:
  ├── Constitutional Memory (read-only for agents, written by Guardian)
  │   docs/atlas/ — the complete Atlas
  │   docs/foundational_laws.md
  │   docs/PROJECT_APPROACH.md
  │
  ├── Error Memory (writable by all agents, read by all)
  │   data/realms/default/memory/errors/{organ}.jsonl
  │   "This error occurred before. Here is what fixed it."
  │
  ├── Procedural Memory (writable by Builder after 3 successes)
  │   data/realms/default/memory/procedural/{organ}.json
  │   "This tool sequence is verified. Use it."
  │
  └── Episodic Memory (writable by Architect + Reviewer)
      data/realms/default/memory/episodic/decisions.jsonl
      "This architectural decision was made. Here is why."

Per-agent (private):
  Each agent's working memory is in-session only.
  Not persisted. Not shared.
```

### The Governance Layer for Agents

The Atlas Keeper Agent runs constitutional checks before any commit.

Constitutional rules for agent commits:
1. All tests must pass (`py -3 -m unittest discover -s tests`)
2. No test may be removed without explicit Atlas Keeper approval
3. The proposal chain must not be bypassed in any code change
4. Constitutional filter must not be weakened
5. Any memory write requires the MemoryBus (no direct storage access)
6. Any cross-organ communication must go through defined interfaces

Violations → Builder Agent gets feedback → must revise → re-review
INANNA NAMMU → final approval on any merge to main

---

## Part IV: The Technical Stack

### Inference Layer (DGX Spark)

```
Primary model (CROWN + Architect + complex reasoning):
  Model: Meta Llama 3.3 70B or DeepSeek R1 70B
  Serving: NIM microservices (Docker container)
  API: OpenAI-compatible HTTP on port 8000
  Context window: 128K tokens

Specialist model (Builder agents — fast, structured output):
  Model: NVIDIA Nemotron 3 Nano (30B total, 3B active)
  OR: Qwen3-32B-Instruct (excellent JSON compliance)
  Serving: NIM microservices or vLLM
  API: OpenAI-compatible HTTP on port 8001

Embedding model (Memory semantic search):
  Model: paraphrase-multilingual-MiniLM-L12-v2 (118MB, CPU)
  Serving: sentence-transformers Python library (no GPU needed)

Vector store (Memory retrieval):
  ChromaDB (local, persistent, ARM64 compatible)
  Stored on DGX Spark's 4TB NVMe

Agent orchestration:
  NVIDIA NeMo Agent Toolkit
  Config-driven YAML workflow definition
  Built-in observability and profiling
  MCP client (connects to INANNA's tool servers)
  A2A protocol (agents delegate to each other)
```

### Development Workflow

```
Phase document written (Architect Agent → Atlas review)
    ↓
Builder Agents assigned (parallel, different organs)
    ↓
Each Builder:
  1. Reads Constitutional Memory (Atlas)
  2. Reads Error Memory for their organ
  3. Reads Procedural Memory for verified patterns
  4. Implements changes on feature branch
  5. Runs test suite
  6. Writes handoff report
    ↓
Reviewer Agent checks each Builder output
  - Atlas compliance check
  - Test suite must pass
  - No constitutional violations
    ↓
Atlas Keeper approves batch (checks all together)
    ↓
INANNA NAMMU reviews and merges to main
    ↓
Error Memory and Procedural Memory updated
```

### Git Strategy for Multi-Agent

```
main                    ← INANNA NAMMU only (Guardian approval required)
develop                 ← Reviewer Agent merges here
feature/nammu-phase-X   ← NAMMU Builder Agent
feature/memory-phase-X  ← Memory Builder Agent
feature/analyst-phase-X ← Analyst Builder Agent
feature/sentinel-phase-X ← Sentinel Builder Agent
```

Each Builder works on their branch independently.
Reviewer merges to develop when tests pass.
INANNA NAMMU merges develop to main when satisfied.

---

## Part V: The Agent Prompts — Constitutional Grounding

Every agent receives the same foundational context at session start:

```yaml
# nemo_agent_toolkit/config/inanna_base.yml

llms:
  architect_llm:
    _type: nim
    model_name: meta/llama-3.3-70b-instruct
    temperature: 0.1
    base_url: http://localhost:8000/v1

  builder_llm:
    _type: nim
    model_name: nvidia/nemotron-3-nano
    temperature: 0.0
    base_url: http://localhost:8001/v1

  reviewer_llm:
    _type: nim
    model_name: Qwen/Qwen3-32B-Instruct
    temperature: 0.0
    base_url: http://localhost:8002/v1

functions:
  read_atlas:
    _type: file_reader
    path: docs/atlas/
    recursive: true

  read_error_memory:
    _type: file_reader
    path: data/realms/default/memory/errors/

  read_procedural_memory:
    _type: file_reader
    path: data/realms/default/memory/procedural/

  run_tests:
    _type: shell_command
    command: "cd inanna && py -3 -m unittest discover -s tests -q"

  git_commit:
    _type: shell_command
    command: "git add -A && git commit -m '{message}'"

workflow:
  _type: multi_agent_router
  agents:
    - atlas_keeper
    - architect
    - nammu_builder
    - memory_builder
    - analyst_builder
    - reviewer
```

### Atlas Keeper System Prompt

```
You are the Atlas Keeper for INANNA NYX.

Before any agent commits code to the repository,
you verify constitutional compliance.

Read docs/atlas/ completely before each review.

You block any commit that:
  1. Removes passing tests
  2. Bypasses the proposal chain
  3. Weakens the constitutional filter
  4. Violates the Human Operator Covenant
  5. Accesses memory storage without MemoryBus
  6. Makes cross-organ calls through undefined interfaces

You approve commits that:
  1. Pass all tests (py -3 -m unittest discover -s tests)
  2. Follow the organ card specification for this organ
  3. Include a handoff report
  4. Update Error Memory if errors were encountered
  5. Update Procedural Memory if new patterns were verified

You never write code. You only read and approve or reject.
Your approval message must cite the specific Atlas section
that authorizes the change.
```

### Builder Agent System Prompt

```
You are a Builder Agent for INANNA NYX organ: {organ_name}.

Before writing any code:
  1. Read docs/atlas/organs/{organ_card}.md completely
  2. Read data/realms/default/memory/errors/{organ_name}.jsonl
     (what failed before — do not repeat these errors)
  3. Read data/realms/default/memory/procedural/{organ_name}.json
     (verified patterns — use these, do not reinvent)
  4. Read docs/implementation/CURRENT_PHASE.md
     (what you are building in this phase)

When implementing:
  - Implement only what the phase document specifies
  - Do not add features not in the phase document
  - Write tests before or alongside implementation
  - Run tests after every significant change

When done:
  - Run: py -3 -m unittest discover -s tests
  - All tests must pass
  - Write: docs/implementation/{organ}_phase_{N}_report.md
  - Commit to feature/{organ_name}-phase-{N}
  - Do not push to main

If you encounter an error:
  - Write it to Error Memory immediately
  - Note what fixed it
  - Continue

Your output is correct, tested code.
Not aspirational code. Not placeholder code.
Code that runs and tests prove it.
```

---

## Part VI: The NVIDIA Cloud Integration

### When to Use Local vs Cloud

```
LOCAL (DGX Spark — sovereign, always primary):
  Normal development work
  All inference during active development
  Memory store (ChromaDB, sentence-transformers)
  Git operations
  Test execution
  All data that must remain private

CLOUD (NVIDIA build.nvidia.com — burst only):
  Very large model inference (>128GB — two-Spark territory)
  Fine-tuning runs on custom datasets
  Parallel agent workloads during intensive development sprints
  Access to specialized models not yet on DGX
  Cost: pay-per-token, monitored carefully

GOVERNANCE FOR CLOUD USE:
  Any cloud call must be explicit (no automatic routing to cloud)
  No private data sent to cloud (operator data, memory contents)
  All cloud calls logged in audit trail
  INANNA NAMMU must approve any cloud usage that
  exceeds the research budget allocation
```

### Research License Services

```
What the NVIDIA AI Enterprise 90-day license provides:
  - NIM microservices access (all available models)
  - NeMo framework (fine-tuning)
  - Triton Inference Server
  - NGC registry (pre-built containers)

After 90 days:
  - NIM still works for local inference (perpetual license for local)
  - Cloud NIM requires renewal or pay-per-use
  - NeMo fine-tuning: renewal needed for enterprise features
  - Recommended: negotiate academic/research pricing with NVIDIA
```

---

## Part VII: The Development Roadmap

### Phase 1 — DGX Setup (Week 1)

Hardware arrives. Setup:
1. Install DGX OS (pre-installed, verify)
2. Pull NIM container for Llama 3.3 70B
3. Pull NIM container for Qwen3-32B (reviewer model)
4. Install NeMo Agent Toolkit
5. Clone INANNA repository to DGX
6. Run full test suite (770+ must pass)
7. Verify server starts with 70B model
8. Connect laptop client to DGX server

**Milestone:** INANNA NYX running on DGX with 70B model.
Verify LLM routing works (30s → <1s response time).
The gap that has been invisible for 9 cycles finally closes.

### Phase 2 — Atlas Keeper + Reviewer (Week 2)

Configure the governance agents:
1. Write Atlas Keeper system prompt
2. Write Reviewer system prompt
3. Configure NeMo Agent Toolkit YAML
4. Test Atlas Keeper against known violations
5. Test Reviewer against Cycle 9 commits (should pass)

**Milestone:** Two governance agents running locally.
Can review a commit and either approve or reject with citation.

### Phase 3 — First Builder Agent (Week 3)

Start with the highest-value missing organ: ANALYST
1. Write ANALYST Builder system prompt
2. Feed it the design spec (08_analyst_design_spec.md)
3. Feed it the Error Memory (empty — first time)
4. Let it build Phase 1 of ANALYST
5. Reviewer checks it
6. Atlas Keeper checks it
7. INANNA NAMMU reviews and approves merge

**Milestone:** ANALYST Phase 1 built by an agent, not by hand.
First proof that the multi-agent platform works.

### Phase 4 — Parallel Builders (Week 4+)

Assign multiple builders simultaneously:
- SENTINEL Builder → creates core/sentinel.py
- MEMORY Builder → creates core/memory_semantic.py
- PROFILE Builder → enforces preferred_length in CROWN

Each on their own feature branch.
Reviewer checks each independently.
Atlas Keeper checks the combined diff before merge.

---

## Part VIII: The Honest Picture

### What This Platform Changes

**Before (Cycles 1-9):**
- One Builder (Codex) working sequentially
- One phase at a time
- Architecture by Claude in conversation
- 30-second LLM inference on 7B model
- No agent memory between sessions

**After (DGX Spark + multi-agent):**
- Multiple Builders working in parallel
- Multiple organs developed simultaneously
- Architecture by Architect Agent reading Atlas
- <1 second inference on 70B model
- Persistent Error + Procedural Memory across sessions
- NAMMU LLM routing finally works as designed

### What This Platform Does NOT Change

- INANNA NAMMU remains Guardian with final approval
- The proposal chain remains for all consequential actions
- The constitutional filter remains before all routing
- The Atlas remains the truth above all code
- The Human Operator Covenant remains inviolable

The agents are builders and reviewers.
They work within the governance structure.
They cannot override it.

### The Risk to Manage

Multi-agent development risks **scope explosion** — agents
proposing more features because they can build faster.

The Atlas Keeper agent's most important rule:
**"Does the phase document authorize this change?"**

If not — reject it, regardless of how good it looks.
Speed must not outrun governance.

---

## Part IX: Summary — The Picture

```
INANNA NAMMU (Guardian — Laptop)
      │
      │ final approval
      │
DGX SPARK (128GB, 70B model, NeMo Agent Toolkit)
      │
      ├── Atlas Keeper Agent (constitutional compliance)
      ├── Architect Agent (phase design, documentation)
      ├── Builder Agents × N (parallel organ development)
      │     each reads: Atlas + Error Memory + Procedural Memory
      │     each writes to: feature branch + Error Memory
      └── Reviewer Agent (test pass + Atlas compliance)
      │
      ├── NIM: 70B model (CROWN, Architect, complex reasoning)
      ├── NIM: Qwen3-32B (Reviewer, structured output)
      ├── NIM: Nemotron 3 Nano (Builders, fast iteration)
      ├── ChromaDB (vector memory store)
      ├── NeMo Agent Toolkit (orchestration)
      └── INANNA NYX repository (the living system)
      │
NVIDIA CLOUD (burst only, explicit approval required)
      └── Large model inference, fine-tuning overflow
```

**Cost:**
- DGX Spark: $3,999-$4,699 (one-time)
- NVIDIA AI Enterprise: included 90 days, then negotiated research pricing
- NVIDIA Cloud: pay-per-token for burst usage only
- Laptop: existing hardware + NixOS (free)

**Timeline:**
- Week 1: hardware setup, 70B working
- Week 2: governance agents running
- Week 3: first Builder agent proves the pattern
- Week 4+: parallel development at multiple organs simultaneously

This is not a distant dream.
Every component exists today.
The DGX Spark ships now.
NeMo Agent Toolkit is open source.
NIM microservices run on ARM64 DGX OS.
INANNA NYX already uses OpenAI-compatible APIs.

The only thing between now and this picture is the hardware.

---

*Design Specification version 1.0 · 2026-04-25*
*Written by: Claude (Command Center)*
*Guardian: INANNA NAMMU*
*Grounded in: NVIDIA DGX Spark technical specs, NeMo Agent Toolkit docs,*
*NIM microservices documentation, and the INANNA NYX Atlas*
