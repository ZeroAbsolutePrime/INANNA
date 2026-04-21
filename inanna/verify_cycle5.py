from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from core.faculty_monitor import FacultyMonitor
from core.nammu import IntentClassifier
from core.operator import OperatorFaculty, ToolResult
from core.orchestration import OrchestrationEngine, OrchestrationPlan, OrchestrationStep
from core.process_monitor import ProcessMonitor
from identity import CURRENT_PHASE, CYCLE5_SUMMARY
from main import AUTO_MEMORY_TURN_THRESHOLD


APP_ROOT = Path(__file__).resolve().parent
TOOLS_CONFIG_PATH = APP_ROOT / "config" / "tools.json"
FACULTIES_CONFIG_PATH = APP_ROOT / "config" / "faculties.json"
GOVERNANCE_SIGNALS_PATH = APP_ROOT / "config" / "governance_signals.json"
INDEX_HTML_PATH = APP_ROOT / "ui" / "static" / "index.html"
CONSOLE_HTML_PATH = APP_ROOT / "ui" / "static" / "console.html"
LLM_DOC_PATH = APP_ROOT.parent / "docs" / "llm_configuration.md"
IDENTITY_PATH = APP_ROOT / "identity.py"
MAIN_PATH = APP_ROOT / "main.py"
SERVER_PATH = APP_ROOT / "ui" / "server.py"


class MockEngine:
    def __init__(self, connected: bool = False, reply: str = "crown") -> None:
        self._connected = connected
        self.reply = reply

    def _call_openai_compatible(self, messages) -> str:
        del messages
        return self.reply


class CheckRunner:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        self.checks.append((label, condition, detail))

    def finish(self) -> int:
        print("INANNA NYX - Cycle 5 Integration Verification")
        print("==============================================")
        for label, passed, detail in self.checks:
            marker = "PASS" if passed else "FAIL"
            if passed or not detail:
                print(f"[{marker}] {label}")
            else:
                print(f"[{marker}] {label} ({detail})")
        print("----------------------------------------------")

        passed_count = sum(1 for _, passed, _ in self.checks if passed)
        total = len(self.checks)
        if passed_count == total:
            print(f"All {total} checks passed. Cycle 5 architecture verified.")
            return 0

        print(f"{passed_count} of {total} checks passed. Cycle 5 verification failed.")
        return 1


def run_script(path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=APP_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    detail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()
    return result.returncode == 0, detail


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    runner = CheckRunner()

    tools_payload = json.loads(TOOLS_CONFIG_PATH.read_text(encoding="utf-8"))
    tools = tools_payload.get("tools", {})
    tool_names = sorted(tools.keys()) if isinstance(tools, dict) else []
    operator = OperatorFaculty()

    runner.check("Tools config: config/tools.json exists", TOOLS_CONFIG_PATH.exists())
    runner.check(
        "Tools config: exactly four tools are registered",
        tool_names == ["ping", "resolve_host", "scan_ports", "web_search"],
        detail=str(tool_names),
    )
    runner.check(
        "Tools config: web_search is enabled",
        bool(tools.get("web_search", {}).get("enabled")),
    )
    runner.check(
        "Tools config: ping is enabled",
        bool(tools.get("ping", {}).get("enabled")),
    )
    runner.check(
        "Tools config: resolve_host is enabled",
        bool(tools.get("resolve_host", {}).get("enabled")),
    )
    runner.check(
        "Tools config: scan_ports is enabled",
        bool(tools.get("scan_ports", {}).get("enabled")),
    )
    runner.check(
        "Tools config: all tools require approval",
        all(
            isinstance(definition, dict) and bool(definition.get("requires_approval"))
            for definition in tools.values()
        ),
    )
    runner.check(
        "OperatorFaculty: can be instantiated",
        isinstance(operator, OperatorFaculty),
    )
    with TemporaryDirectory() as temp_dir:
        custom_tools_path = Path(temp_dir) / "tools.json"
        custom_tools_path.write_text(
            json.dumps(
                {
                    "tools": {
                        "custom_probe": {
                            "display_name": "Custom Probe",
                            "description": "Verifier-only tool",
                            "category": "test",
                            "requires_approval": True,
                            "parameters": ["target"],
                            "enabled": True,
                        }
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        custom_operator = OperatorFaculty(custom_tools_path)
        runner.check(
            "OperatorFaculty: PERMITTED_TOOLS are read from tools.json at runtime",
            custom_operator.PERMITTED_TOOLS == {"custom_probe"},
            detail=str(custom_operator.PERMITTED_TOOLS),
        )

    run_result = Mock(
        returncode=0,
        stdout="Ping statistics for 127.0.0.1:\nAverage = 12ms",
        stderr="",
    )
    with patch("core.operator.platform.system", return_value="Windows"), patch(
        "core.operator.subprocess.run",
        return_value=run_result,
    ):
        ping_result = operator.execute("ping", {"host": "127.0.0.1"})
    runner.check(
        "OperatorFaculty: ping executes and returns ToolResult",
        isinstance(ping_result, ToolResult),
    )
    runner.check(
        "OperatorFaculty: ping returns a successful ToolResult",
        ping_result.success and ping_result.tool == "ping" and ping_result.data.get("latency_ms") == 12.0,
        detail=str(ping_result),
    )

    resolve_result = operator.execute("resolve_host", {"host": "localhost"})
    runner.check(
        "OperatorFaculty: resolve_host(localhost) returns success",
        resolve_result.success,
        detail=resolve_result.error,
    )
    runner.check(
        'OperatorFaculty: resolve_host("localhost") returns ip 127.0.0.1',
        resolve_result.data.get("ip") == "127.0.0.1",
        detail=str(resolve_result.data),
    )

    with patch(
        "core.operator.socket.create_connection",
        side_effect=OSError("closed"),
    ) as create_connection:
        scan_result = operator.execute(
            "scan_ports",
            {"host": "127.0.0.1", "port_range": "80-500"},
        )
    runner.check(
        "OperatorFaculty: scan_ports caps to one hundred ports",
        scan_result.success and scan_result.data.get("scanned") == 100,
        detail=str(scan_result.data),
    )
    runner.check(
        "OperatorFaculty: scan_ports normalized range matches the cap",
        scan_result.data.get("port_range") == "80-179" and create_connection.call_count == 100,
        detail=f"range={scan_result.data.get('port_range')} calls={create_connection.call_count}",
    )
    runner.check(
        "Network tools: resolve_host is in PERMITTED_TOOLS",
        "resolve_host" in operator.PERMITTED_TOOLS,
    )
    runner.check(
        "Network tools: scan_ports is in PERMITTED_TOOLS",
        "scan_ports" in operator.PERMITTED_TOOLS,
    )

    faculties_payload = json.loads(FACULTIES_CONFIG_PATH.read_text(encoding="utf-8"))
    faculties = faculties_payload.get("faculties", {})
    active_faculties = {
        name: definition
        for name, definition in faculties.items()
        if isinstance(name, str) and isinstance(definition, dict) and bool(definition.get("active", False))
    }

    runner.check("Faculties config: config/faculties.json exists", FACULTIES_CONFIG_PATH.exists())
    runner.check(
        "Faculties config: exactly five Faculty definitions exist",
        len(faculties) == 5,
        detail=str(sorted(faculties.keys())),
    )
    runner.check(
        "Faculties config: crown, analyst, operator, and guardian are active",
        all(bool(faculties.get(name, {}).get("active")) for name in ("crown", "analyst", "operator", "guardian")),
    )
    runner.check(
        "Faculties config: sentinel is active",
        bool(faculties.get("sentinel", {}).get("active")),
    )
    runner.check(
        'Faculties config: sentinel model_name is "qwen2.5-14b-instruct"',
        faculties.get("sentinel", {}).get("model_name") == "qwen2.5-14b-instruct",
        detail=str(faculties.get("sentinel", {}).get("model_name")),
    )
    runner.check(
        "Faculties config: sentinel has three governance rules",
        len(faculties.get("sentinel", {}).get("governance_rules", [])) == 3,
    )
    runner.check(
        "Faculties config: all active Faculties have a domain",
        all(str(definition.get("domain", "")).strip() for definition in active_faculties.values()),
    )
    runner.check(
        "Faculties config: all active Faculties have a description",
        all(str(definition.get("description", "")).strip() for definition in active_faculties.values()),
    )
    runner.check(
        "Faculties config: all active Faculties have a charter_preview",
        all(str(definition.get("charter_preview", "")).strip() for definition in active_faculties.values()),
    )

    faculty_monitor = FacultyMonitor()
    faculty_records = faculty_monitor.all_records()
    runner.check(
        "Faculty monitor: FacultyMonitor loads from faculties.json",
        isinstance(faculty_monitor, FacultyMonitor),
    )
    runner.check(
        "Faculty monitor: all_records returns five active records",
        len(faculty_records) == 5,
        detail=str([record.name for record in faculty_records]),
    )
    runner.check(
        "Faculty monitor: each record has display_name",
        all(record.display_name for record in faculty_records),
    )
    runner.check(
        "Faculty monitor: each record has domain",
        all(record.domain for record in faculty_records),
    )
    runner.check(
        "Faculty monitor: each record has charter_preview",
        all(record.charter_preview for record in faculty_records),
    )
    faculty_report = faculty_monitor.format_report()
    runner.check(
        "Faculty monitor: format_report contains all five Faculty names",
        all(name in faculty_report for name in ("CROWN", "ANALYST", "OPERATOR", "GUARDIAN", "SENTINEL")),
        detail=faculty_report,
    )

    classifier = IntentClassifier(MockEngine(), faculties_path=FACULTIES_CONFIG_PATH)
    prompt = classifier._build_classification_prompt("Analyze this vulnerability and explain it simply.")
    runner.check(
        "NAMMU routing: IntentClassifier loads faculties from faculties.json",
        set(classifier.faculties.keys()) == {"crown", "analyst", "operator", "guardian", "sentinel"},
        detail=str(sorted(classifier.faculties.keys())),
    )
    runner.check(
        "NAMMU routing: SENTINEL is in the active faculties",
        "sentinel" in classifier.faculties and classifier.faculties["sentinel"]["domain"] == "security",
    )
    runner.check(
        "NAMMU routing: classification prompt includes sentinel",
        "sentinel:" in prompt,
        detail=prompt,
    )
    runner.check(
        "NAMMU routing: classification prompt includes crown",
        "crown:" in prompt,
        detail=prompt,
    )
    runner.check(
        "NAMMU routing: classification prompt includes analyst",
        "analyst:" in prompt,
        detail=prompt,
    )
    runner.check(
        "NAMMU routing: classification prompt includes operator",
        "operator:" in prompt,
        detail=prompt,
    )
    runner.check(
        "NAMMU routing: classification prompt includes guardian",
        "guardian:" in prompt,
        detail=prompt,
    )
    missing_classifier = IntentClassifier(
        MockEngine(),
        faculties_path=Path("C:/tmp/does-not-exist/faculties.json"),
    )
    runner.check(
        "NAMMU routing: missing config falls back to crown/analyst defaults",
        set(missing_classifier.faculties.keys()) == {"crown", "analyst"},
        detail=str(sorted(missing_classifier.faculties.keys())),
    )
    runner.check(
        "NAMMU routing: unknown Faculty response falls back to crown",
        classifier._normalize_route("mystery faculty") == "crown",
    )
    runner.check(
        "NAMMU routing: security domain hints are loaded for sentinel",
        "vulnerability" in classifier.domain_hints.get("security", []),
        detail=str(classifier.domain_hints.get("security", [])),
    )

    orchestration_engine = OrchestrationEngine(FACULTIES_CONFIG_PATH)
    plan = orchestration_engine.detect_orchestration("Analyze security and explain simply.")
    unrelated_plan = orchestration_engine.detect_orchestration("Tell me a short poem about spring.")
    synthesis_step = OrchestrationStep("crown", "synthesize", "sentinel", "user")
    synthesis_prompt = orchestration_engine.format_synthesis_prompt(
        "Analyze security and explain simply.",
        "SENTINEL found exposed services and weak segmentation.",
        synthesis_step,
    )
    runner.check(
        "Orchestration: OrchestrationEngine can be instantiated",
        isinstance(orchestration_engine, OrchestrationEngine),
    )
    runner.check(
        "Orchestration: detect_orchestration finds a plan for security+explain input",
        isinstance(plan, OrchestrationPlan),
    )
    runner.check(
        "Orchestration: detect_orchestration returns None for unrelated input",
        unrelated_plan is None,
    )
    runner.check(
        "Orchestration: plan has exactly two steps",
        plan is not None and len(plan.steps) == 2,
        detail=str(plan.steps if plan is not None else []),
    )
    runner.check(
        "Orchestration: first step is SENTINEL analyze user->crown",
        plan is not None
        and plan.steps[0].faculty == "sentinel"
        and plan.steps[0].purpose == "analyze"
        and plan.steps[0].input_from == "user"
        and plan.steps[0].output_to == "crown",
        detail=str(plan.steps[0] if plan is not None else None),
    )
    runner.check(
        "Orchestration: second step is CROWN synthesize sentinel->user",
        plan is not None
        and plan.steps[1].faculty == "crown"
        and plan.steps[1].purpose == "synthesize"
        and plan.steps[1].input_from == "sentinel"
        and plan.steps[1].output_to == "user",
        detail=str(plan.steps[1] if plan is not None else None),
    )
    runner.check(
        "Orchestration: plans require approval",
        plan is not None and plan.requires_approval,
    )
    runner.check(
        "Orchestration: format_synthesis_prompt includes previous Faculty output",
        "SENTINEL found exposed services and weak segmentation." in synthesis_prompt,
        detail=synthesis_prompt,
    )
    runner.check(
        "OrchestrationStep: fields preserve faculty, purpose, input_from, output_to",
        synthesis_step.faculty == "crown"
        and synthesis_step.purpose == "synthesize"
        and synthesis_step.input_from == "sentinel"
        and synthesis_step.output_to == "user",
    )

    governance_payload = json.loads(GOVERNANCE_SIGNALS_PATH.read_text(encoding="utf-8"))
    domain_hints = governance_payload.get("domain_hints", {})
    runner.check(
        "Network tools: governance_signals.json has domain_hints",
        isinstance(domain_hints, dict),
    )
    runner.check(
        "Network tools: domain_hints.security has at least five entries",
        len(domain_hints.get("security", [])) >= 5,
        detail=str(domain_hints.get("security", [])),
    )
    runner.check(
        "Network tools: domain_hints.reasoning has at least five entries",
        len(domain_hints.get("reasoning", [])) >= 5,
        detail=str(domain_hints.get("reasoning", [])),
    )

    process_monitor = ProcessMonitor(server_start_time=time.time() - 90)
    inanna_record = process_monitor.inanna_record()
    runner.check(
        "Process monitor: ProcessMonitor can be instantiated",
        isinstance(process_monitor, ProcessMonitor),
    )
    runner.check(
        'Process monitor: inanna_record returns status "running"',
        inanna_record.status == "running",
        detail=str(inanna_record),
    )
    runner.check(
        'Process monitor: format_uptime(3700) returns "1h 1m"',
        process_monitor.format_uptime(3700) == "1h 1m",
        detail=process_monitor.format_uptime(3700),
    )
    runner.check(
        "Process monitor: all_records returns at least two records",
        len(process_monitor.all_records()) >= 2,
    )

    main_source = source(MAIN_PATH)
    server_source = source(SERVER_PATH)
    console_source = source(CONSOLE_HTML_PATH)
    index_source = source(INDEX_HTML_PATH)
    identity_source = source(IDENTITY_PATH)
    llm_doc = source(LLM_DOC_PATH)

    routing_segment_start = main_source.index('if governance_result.faculty == "analyst":')
    routing_segment_end = main_source.index("\ndef main() -> None:")
    routing_segment = main_source[routing_segment_start:routing_segment_end]

    runner.check(
        "Auto-memory: AUTO_MEMORY_TURN_THRESHOLD constant exists",
        "AUTO_MEMORY_TURN_THRESHOLD" in main_source,
    )
    runner.check(
        "Auto-memory: AUTO_MEMORY_TURN_THRESHOLD is 20",
        AUTO_MEMORY_TURN_THRESHOLD == 20,
        detail=str(AUTO_MEMORY_TURN_THRESHOLD),
    )
    runner.check(
        "Auto-memory: no create_memory_request_proposal call remains in the standard routing path",
        "create_memory_request_proposal(" not in routing_segment,
    )

    runner.check(
        "Console surface: ui/static/console.html exists",
        CONSOLE_HTML_PATH.exists(),
    )
    runner.check(
        "Console surface: tools panel section exists",
        'id="panel-tools"' in console_source,
    )
    runner.check(
        "Console surface: network panel section exists",
        'id="panel-network"' in console_source,
    )
    runner.check(
        "Console surface: faculties panel section exists",
        'id="panel-faculties"' in console_source,
    )
    runner.check(
        "Console surface: processes panel section exists",
        'id="panel-processes"' in console_source,
    )
    runner.check(
        "Console surface: faculty-registry command is present",
        "faculty-registry" in console_source,
    )
    runner.check(
        "Console surface: process-status command is present",
        "process-status" in console_source,
    )
    runner.check(
        "Console surface: tool-registry command is present",
        "tool-registry" in console_source,
    )
    runner.check(
        "Console surface: orchestration rendering is present",
        "if (t === 'orchestration')" in console_source,
    )

    runner.check(
        "Main UI: ui/static/index.html exists",
        INDEX_HTML_PATH.exists(),
    )
    runner.check(
        "Main UI: entrance gate openGate function exists",
        "function openGate()" in index_source,
    )
    runner.check(
        "Main UI: sentinel message type handler exists",
        "if(t==='sentinel')" in index_source,
    )
    runner.check(
        "Main UI: orchestration message type handler exists",
        "if(t==='orchestration')" in index_source,
    )
    runner.check(
        "Main UI: arrow key history is wired to ArrowUp",
        "ArrowUp" in index_source,
    )
    runner.check(
        "Main UI: attach button exists",
        "attach-btn" in index_source and "handleAttach()" in index_source,
    )
    runner.check(
        "Main UI: governance suggestion logic exists",
        "showGovernanceSuggestion" in index_source and "governance-trust" in index_source,
    )

    runner.check(
        "LLM documentation: docs/llm_configuration.md exists",
        LLM_DOC_PATH.exists(),
    )
    runner.check(
        "LLM documentation: qwen2.5-7b-instruct-1m entry exists",
        "qwen2.5-7b-instruct-1m" in llm_doc,
    )
    runner.check(
        "LLM documentation: qwen2.5-14b-instruct entry exists",
        "qwen2.5-14b-instruct" in llm_doc,
    )
    runner.check(
        "LLM documentation: Faculty mapping table exists",
        "Faculty" in llm_doc and "Model Mapping" in llm_doc,
    )
    runner.check(
        "Identity: identity.py has an LLM configuration comment block",
        "# LLM configuration:" in identity_source,
    )
    runner.check(
        "Identity: CURRENT_PHASE remains defined under later phases",
        CURRENT_PHASE.startswith("Cycle "),
        detail=CURRENT_PHASE,
    )
    runner.check(
        "Identity: CYCLE5_SUMMARY exists and describes the Operator Console",
        "Operator Console" in CYCLE5_SUMMARY and "SENTINEL->CROWN" in CYCLE5_SUMMARY,
        detail=CYCLE5_SUMMARY,
    )

    runner.check(
        "Sentinel runtime: run_sentinel_response loads model settings from faculties.json",
        "load_faculty_definition(faculties_path, \"sentinel\")" in main_source
        and "effective_model_name" in main_source,
    )
    runner.check(
        "Orchestration order: main.py detects orchestration before NAMMU routing",
        main_source.index("plan = orchestration_engine.detect_orchestration(normalized)")
        < main_source.index("governance_result = classifier.route(normalized)"),
    )
    runner.check(
        "Orchestration order: server.py detects orchestration before NAMMU routing",
        server_source.index("plan = self.orchestration_engine.detect_orchestration(text)")
        < server_source.index("governance_result = self.classifier.route(text)"),
    )
    runner.check(
        'Orchestration broadcast: main.py emits response type "orchestration"',
        '"type": "orchestration"' in main_source,
    )
    runner.check(
        "Orchestration audit: append_audit_event records orchestration entries",
        len(re.findall(r'append_audit_event\(\s*session_audit,\s*"orchestration"', main_source)) >= 2,
    )

    cycle4_ok, cycle4_detail = run_script(APP_ROOT / "verify_cycle4.py")
    runner.check("Regression: verify_cycle4.py still passes", cycle4_ok, detail=cycle4_detail)

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
