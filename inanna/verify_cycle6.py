from __future__ import annotations

import inspect
import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from core.operator import OperatorFaculty
from core.profile import (
    CommunicationObserver,
    IdentityFormatter,
    NotificationStore,
    ProfileManager,
    UserProfile,
)
from core.reflection import ReflectiveMemory
from identity import CURRENT_PHASE, CYCLE6_SUMMARY
from main import (
    PROFILE_PROTECTED_CLEAR_FIELDS,
    build_admin_surface_payload,
    build_grounding_prefix,
    build_reflection_grounding,
    extract_reflection_proposal,
    needs_onboarding,
    sync_profile_grounding,
)


APP_ROOT = Path(__file__).resolve().parent
DOCS_ROOT = APP_ROOT.parent / "docs"
PROFILE_PATH = APP_ROOT / "core" / "profile.py"
REFLECTION_PATH = APP_ROOT / "core" / "reflection.py"
MAIN_PATH = APP_ROOT / "main.py"
SERVER_PATH = APP_ROOT / "ui" / "server.py"
IDENTITY_PATH = APP_ROOT / "identity.py"
VERIFY_CYCLE5_PATH = APP_ROOT / "verify_cycle5.py"
MEMORY_ARCHITECTURE_PATH = DOCS_ROOT / "memory_architecture.md"
CYCLE6_MASTER_PLAN_PATH = DOCS_ROOT / "cycle6_master_plan.md"
LLM_CONFIGURATION_PATH = DOCS_ROOT / "llm_configuration.md"


class CheckRunner:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        self.checks.append((label, condition, detail))

    def finish(self) -> int:
        print("INANNA NYX - Cycle 6 Integration Verification")
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
            print(f"All {total} checks passed. Cycle 6 architecture verified.")
            return 0

        print(f"{passed_count} of {total} checks passed. Cycle 6 verification failed.")
        return 1


def run_script(path: Path) -> tuple[bool, str, str]:
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=APP_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = result.stdout.strip()
    detail = stdout.splitlines()[-1] if stdout else result.stderr.strip()
    return result.returncode == 0, detail, stdout


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    runner = CheckRunner()

    profile_source = source(PROFILE_PATH)
    reflection_source = source(REFLECTION_PATH)
    main_source = source(MAIN_PATH)
    server_source = source(SERVER_PATH)
    identity_source = source(IDENTITY_PATH)

    required_profile_fields = {
        "user_id",
        "preferred_name",
        "pronouns",
        "gender",
        "sex",
        "languages",
        "timezone",
        "location_city",
        "location_region",
        "location_country",
        "departments",
        "groups",
        "notification_scope",
        "communication_style",
        "preferred_length",
        "formality",
        "observed_patterns",
        "domains",
        "recurring_topics",
        "named_projects",
        "session_trusted_tools",
        "persistent_trusted_tools",
        "onboarding_completed",
        "onboarding_completed_at",
        "survey_responses",
        "inanna_notes",
    }

    runner.check("User Profile: core/profile.py exists", PROFILE_PATH.exists())
    runner.check(
        "User Profile: UserProfile dataclass has all required fields",
        required_profile_fields.issubset({field.name for field in fields(UserProfile)}),
        detail=str(sorted(required_profile_fields - {field.name for field in fields(UserProfile)})),
    )

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        profiles_dir = root / "profiles"
        profile_manager = ProfileManager(profiles_dir)
        runner.check(
            "User Profile: ProfileManager instantiation creates profiles directory",
            profiles_dir.exists(),
        )

        created = profile_manager.ensure_profile_exists("user-1")
        runner.check(
            "User Profile: ProfileManager.ensure_profile_exists() creates profile",
            isinstance(created, UserProfile) and (profiles_dir / "user-1.json").exists(),
        )
        loaded = profile_manager.load("user-1")
        runner.check(
            "User Profile: ProfileManager.load() returns UserProfile",
            isinstance(loaded, UserProfile),
        )

        custom = UserProfile(
            user_id="user-2",
            preferred_name="Zaera",
            pronouns="she/her",
            languages=["en", "es"],
            departments=["ops"],
            survey_responses={"purpose": "stewardship"},
        )
        profile_manager.save(custom)
        custom_path = profiles_dir / "user-2.json"
        custom_payload = json.loads(custom_path.read_text(encoding="utf-8"))
        runner.check(
            "User Profile: ProfileManager.save() writes JSON to disk",
            custom_path.exists() and custom_payload.get("preferred_name") == "Zaera",
        )
        runner.check(
            "User Profile: ProfileManager.update_field() updates string fields",
            profile_manager.update_field("user-2", "preferred_name", "Oracle")
            and profile_manager.load("user-2").preferred_name == "Oracle",
        )
        runner.check(
            "User Profile: ProfileManager.update_field() updates list fields",
            profile_manager.update_field("user-2", "departments", ["ops", "care"])
            and profile_manager.load("user-2").departments == ["ops", "care"],
        )
        runner.check(
            "User Profile: ProfileManager.update_field() rejects unknown fields",
            profile_manager.update_field("user-2", "not_a_field", "x") is False,
        )
        runner.check(
            "User Profile: ProfileManager.display_name_for() returns preferred_name",
            profile_manager.display_name_for("user-2", fallback="Fallback") == "Oracle",
        )
        runner.check(
            "User Profile: ProfileManager.pronouns_for() returns pronouns",
            profile_manager.pronouns_for("user-2") == "she/her",
            detail=profile_manager.pronouns_for("user-2"),
        )
        round_trip = profile_manager.load("user-2")
        runner.check(
            "User Profile: Profile JSON is valid after save/load round-trip",
            isinstance(round_trip, UserProfile)
            and round_trip.languages == ["en", "es"]
            and round_trip.departments == ["ops", "care"]
            and round_trip.survey_responses == {"purpose": "stewardship"},
        )
        runner.check(
            "User Profile: ProfileManager.delete() removes profile",
            profile_manager.delete("user-2") and not custom_path.exists(),
        )

        profile_manager.ensure_profile_exists("user-3")
        onboarding_profile = profile_manager.load("user-3")
        runner.check(
            "Onboarding: needs_onboarding() returns True for new profile",
            needs_onboarding(onboarding_profile),
        )
        profile_manager.update_field("user-3", "onboarding_completed", True)
        profile_manager.update_field("user-3", "onboarding_completed_at", "2026-04-21T10:00:00+00:00")
        profile_manager.update_field("user-3", "survey_responses", {"purpose": "proof"})
        completed_profile = profile_manager.load("user-3")
        runner.check(
            "Onboarding: needs_onboarding() returns False after completion",
            not needs_onboarding(completed_profile),
        )
        runner.check(
            "Onboarding: onboarding_completed field saves correctly",
            bool(completed_profile.onboarding_completed),
        )
        runner.check(
            "Onboarding: onboarding_completed_at field saves correctly",
            completed_profile.onboarding_completed_at == "2026-04-21T10:00:00+00:00",
            detail=completed_profile.onboarding_completed_at,
        )
        runner.check(
            "Onboarding: survey_responses field stores dict correctly",
            completed_profile.survey_responses == {"purpose": "proof"},
            detail=str(completed_profile.survey_responses),
        )

        runner.check(
            'Profile Commands: "my-profile" is routed in server.py',
            'elif command_name == "my-profile":' in server_source,
        )
        runner.check(
            'Profile Commands: "view-profile" is routed in server.py',
            'elif command_name == "view-profile":' in server_source,
        )
        runner.check(
            'Profile Commands: "my-profile edit" exists in main.py',
            'if lowered.startswith("my-profile edit")' in main_source,
        )
        runner.check(
            'Profile Commands: "my-profile clear" exists in main.py',
            'if lowered.startswith("my-profile clear")' in main_source,
        )
        runner.check(
            'Profile Commands: "my-profile clear communication" shortcut exists in main.py',
            'if field_name == "communication":' in main_source,
        )
        runner.check(
            "Profile Commands: protected fields include user_id and version",
            {"user_id", "version"}.issubset(PROFILE_PROTECTED_CLEAR_FIELDS),
            detail=str(sorted(PROFILE_PROTECTED_CLEAR_FIELDS)),
        )

        observer = CommunicationObserver(profile_manager)
        profile_manager.ensure_profile_exists("observer")

        observer.observe_session(
            user_id="observer",
            messages=["Short note.", "Quick follow-up."],
            topics=[],
        )
        runner.check(
            'Communication Learner: observe_session() with short messages -> preferred_length "short"',
            profile_manager.load("observer").preferred_length == "short",
            detail=profile_manager.load("observer").preferred_length,
        )

        observer.observe_session(
            user_id="observer",
            messages=["L" * 350, "M" * 320],
            topics=[],
        )
        runner.check(
            'Communication Learner: observe_session() with long messages -> preferred_length "long"',
            profile_manager.load("observer").preferred_length == "long",
            detail=profile_manager.load("observer").preferred_length,
        )

        observer.observe_session(
            user_id="observer",
            messages=[
                "Please review this draft. Would you consider the governance implications? Thank you.",
            ],
            topics=[],
        )
        runner.check(
            'Communication Learner: observe_session() with formal language -> formality "formal"',
            profile_manager.load("observer").formality == "formal",
            detail=profile_manager.load("observer").formality,
        )

        observer.observe_session(
            user_id="observer",
            messages=["hey yeah cool thanks btw this is great"],
            topics=[],
        )
        runner.check(
            'Communication Learner: observe_session() with casual language -> formality "casual"',
            profile_manager.load("observer").formality == "casual",
            detail=profile_manager.load("observer").formality,
        )

        observer.observe_session(
            user_id="observer",
            messages=["Please review the memory flow."],
            topics=["memory", "governance"],
        )
        runner.check(
            "Communication Learner: observe_session() updates recurring_topics",
            profile_manager.load("observer").recurring_topics == ["memory", "governance"],
            detail=str(profile_manager.load("observer").recurring_topics),
        )

        profile_manager.update_field("observer", "recurring_topics", ["memory"])
        observer.observe_session(
            user_id="observer",
            messages=["Memory again."],
            topics=["memory", "memory", "profile"],
        )
        runner.check(
            "Communication Learner: observe_session() deduplicates topics",
            profile_manager.load("observer").recurring_topics == ["memory", "profile"],
            detail=str(profile_manager.load("observer").recurring_topics),
        )

        profile_manager.update_field("observer", "recurring_topics", [])
        observer.observe_session(
            user_id="observer",
            messages=["Topic sweep."],
            topics=[f"topic-{index}" for index in range(25)],
        )
        recurring_topics = profile_manager.load("observer").recurring_topics
        runner.check(
            "Communication Learner: observe_session() caps topics at 20",
            len(recurring_topics) == 20 and recurring_topics[0] == "topic-5" and recurring_topics[-1] == "topic-24",
            detail=str(recurring_topics),
        )

        profile_manager.update_field("observer", "preferred_length", "medium")
        frozen_topics = list(profile_manager.load("observer").recurring_topics)
        observer.observe_session(user_id="observer", messages=[], topics=["ignored"])
        stable_profile = profile_manager.load("observer")
        runner.check(
            "Communication Learner: observe_session() handles empty messages gracefully",
            stable_profile.preferred_length == "medium" and stable_profile.recurring_topics == frozen_topics,
            detail=f"length={stable_profile.preferred_length} topics={stable_profile.recurring_topics}",
        )
        runner.check(
            "Communication Learner: CommunicationObserver class exists in profile.py",
            "class CommunicationObserver" in profile_source,
        )
        runner.check(
            "Communication Learner: CommunicationObserver is called at session end in server.py",
            server_source.count("observe_session_communication") >= 2,
            detail=str(server_source.count("observe_session_communication")),
        )

        notifications_dir = root / "notifications"
        notification_store = NotificationStore(notifications_dir)
        runner.check(
            "Organizational Layer: NotificationStore class exists in profile.py",
            "class NotificationStore" in profile_source,
        )
        notification_store.add(
            "observer",
            {
                "notification_id": "notif-1",
                "department": "ops",
                "message": "Check the ops realm.",
                "delivered": False,
            },
        )
        notification_path = notifications_dir / "observer.json"
        notification_payload = json.loads(notification_path.read_text(encoding="utf-8"))
        runner.check(
            "Organizational Layer: NotificationStore.add() stores notification",
            notification_path.exists() and len(notification_payload) == 1,
        )
        pending_notifications = notification_store.load_pending("observer")
        runner.check(
            "Organizational Layer: NotificationStore.load_pending() returns list",
            isinstance(pending_notifications, list) and len(pending_notifications) == 1,
            detail=str(pending_notifications),
        )
        runner.check(
            "Organizational Layer: NotificationStore.mark_delivered() marks correctly",
            notification_store.mark_delivered("observer", "notif-1")
            and json.loads(notification_path.read_text(encoding="utf-8"))[0]["delivered"] is True,
        )
        notification_store.clear_delivered("observer")
        runner.check(
            "Organizational Layer: NotificationStore.clear_delivered() clears delivered",
            not notification_path.exists(),
        )
        runner.check(
            'Organizational Layer: "assign-department" is routed in server.py',
            'elif command_name == "assign-department":' in server_source,
        )
        runner.check(
            'Organizational Layer: "unassign-department" is routed in server.py',
            'elif command_name == "unassign-department":' in server_source,
        )
        runner.check(
            'Organizational Layer: "assign-group" is routed in server.py',
            'elif command_name == "assign-group":' in server_source,
        )
        runner.check(
            'Organizational Layer: "unassign-group" is routed in server.py',
            'elif command_name == "unassign-group":' in server_source,
        )
        runner.check(
            'Organizational Layer: "my-departments" is routed in server.py',
            'elif command_name == "my-departments":' in server_source,
        )
        runner.check(
            'Organizational Layer: "notify-department" is routed in server.py',
            'elif command_name == "notify-department":' in server_source,
        )
        admin_payload_source = inspect.getsource(build_admin_surface_payload)
        runner.check(
            "Organizational Layer: departments appear in admin-surface payload",
            '"departments":' in admin_payload_source and '"groups":' in admin_payload_source,
        )

        formatter = IdentityFormatter(profile_manager)
        profile_manager.update_field("observer", "preferred_name", "Alicia")
        profile_manager.update_field("observer", "pronouns", "she/her")
        runner.check(
            "Identity Layer: IdentityFormatter class exists in profile.py",
            "class IdentityFormatter" in profile_source,
        )
        runner.check(
            "Identity Layer: IdentityFormatter.address() returns preferred_name",
            formatter.address("observer", fallback="Alice") == "Alicia",
        )
        runner.check(
            'Identity Layer: IdentityFormatter.subject() returns "she" for she/her',
            formatter.subject("observer") == "she",
            detail=formatter.subject("observer"),
        )
        profile_manager.update_field("observer", "pronouns", "he/him")
        runner.check(
            'Identity Layer: IdentityFormatter.subject() returns "he" for he/him',
            formatter.subject("observer") == "he",
            detail=formatter.subject("observer"),
        )
        profile_manager.update_field("observer", "pronouns", "they/them")
        runner.check(
            'Identity Layer: IdentityFormatter.subject() returns "they" for they/them',
            formatter.subject("observer") == "they",
            detail=formatter.subject("observer"),
        )
        profile_manager.update_field("observer", "pronouns", "unknown-set")
        runner.check(
            'Identity Layer: IdentityFormatter.subject() defaults to "they" for unknown',
            formatter.subject("observer") == "they",
            detail=formatter.subject("observer"),
        )
        profile_manager.update_field("observer", "pronouns", "she/her")
        runner.check(
            "Identity Layer: IdentityFormatter.object_pronoun() correct for she/her",
            formatter.object_pronoun("observer") == "her",
            detail=formatter.object_pronoun("observer"),
        )
        profile_manager.update_field("observer", "pronouns", "they/them")
        runner.check(
            "Identity Layer: IdentityFormatter.possessive() correct for they/them",
            formatter.possessive("observer") == "their",
            detail=formatter.possessive("observer"),
        )
        runner.check(
            "Identity Layer: IdentityFormatter.format_greeting() includes name",
            "Alicia" in formatter.format_greeting("observer", fallback="Alice"),
            detail=formatter.format_greeting("observer", fallback="Alice"),
        )
        profile_manager.update_field("observer", "timezone", "Europe/Madrid")
        formatted_time = formatter.format_time("2026-04-21T12:30:00+00:00", "observer")
        runner.check(
            "Identity Layer: IdentityFormatter.format_time() returns string",
            isinstance(formatted_time, str) and bool(formatted_time.strip()),
            detail=formatted_time,
        )
        profile_manager.update_field("observer", "timezone", "Not/A_Zone")
        invalid_timezone_time = formatter.format_time("2026-04-21T12:30:00+00:00", "observer")
        runner.check(
            "Identity Layer: IdentityFormatter.format_time() handles invalid timezone",
            isinstance(invalid_timezone_time, str) and invalid_timezone_time != "",
            detail=invalid_timezone_time,
        )
        runner.check(
            "Identity Layer: build_grounding_prefix() uses IdentityFormatter in main.py",
            "IdentityFormatter" in inspect.getsource(build_grounding_prefix),
        )
        profile_manager.update_field("observer", "timezone", "Europe/Madrid")
        profile_manager.update_field("observer", "pronouns", "she/her")
        grounding = build_grounding_prefix(
            profile_manager,
            SimpleNamespace(user_id="observer", display_name="Alice"),
            None,
        )
        runner.check(
            "Identity Layer: build_grounding_prefix() includes pronouns when set",
            "Alicia uses she/her pronouns." in grounding and "You are speaking with Alicia." in grounding,
            detail=grounding,
        )

        runner.check(
            "Trust Persistence: persistent_trusted_tools field exists in UserProfile",
            "persistent_trusted_tools" in {field.name for field in fields(UserProfile)},
        )
        runner.check(
            'Trust Persistence: "governance-trust" command exists in server.py',
            'elif command_name == "governance-trust":' in server_source,
        )
        runner.check(
            'Trust Persistence: "governance-revoke" command exists in server.py',
            'elif command_name == "governance-revoke":' in server_source,
        )
        runner.check(
            'Trust Persistence: "my-trust" command exists in server.py',
            'elif command_name == "my-trust":' in server_source,
        )
        operator = OperatorFaculty()
        runner.check(
            "Trust Persistence: OperatorFaculty.should_skip_proposal() exists",
            hasattr(operator, "should_skip_proposal"),
        )
        runner.check(
            "Trust Persistence: should_skip_proposal() returns True for trusted tool",
            operator.should_skip_proposal("web_search", ["web_search"]),
        )
        runner.check(
            "Trust Persistence: should_skip_proposal() returns False for untrusted tool",
            operator.should_skip_proposal("web_search", ["ping"]) is False,
        )
        runner.check(
            'Trust Persistence: "trust_granted" audit event exists in server.py',
            '"trust_granted"' in server_source,
        )
        runner.check(
            'Trust Persistence: "trust_revoked" audit event exists in server.py',
            '"trust_revoked"' in server_source,
        )

        reflective_memory = ReflectiveMemory(root / "self")
        runner.check(
            "Reflective Memory: core/reflection.py exists",
            REFLECTION_PATH.exists(),
        )
        runner.check(
            "Reflective Memory: ReflectiveMemory instantiates",
            isinstance(reflective_memory, ReflectiveMemory),
        )
        proposed = reflective_memory.propose("Pattern noticed", "during testing")
        runner.check(
            "Reflective Memory: propose() creates ReflectionEntry without writing to disk",
            proposed.entry_id.startswith("reflect-") and not reflective_memory.reflection_path.exists(),
        )
        reflective_memory.approve(proposed, approved_by="guardian")
        reflection_lines = reflective_memory.reflection_path.read_text(encoding="utf-8").splitlines()
        runner.check(
            "Reflective Memory: approve() writes to reflection.jsonl",
            len(reflection_lines) == 1,
            detail=str(reflection_lines),
        )
        reflective_memory.approve(
            reflective_memory.propose("Second pattern", "during proof"),
            approved_by="guardian",
        )
        appended_lines = reflective_memory.reflection_path.read_text(encoding="utf-8").splitlines()
        runner.check(
            "Reflective Memory: approve() appends (does not overwrite)",
            len(appended_lines) == 2,
            detail=str(appended_lines),
        )
        empty_reflective_memory = ReflectiveMemory(root / "self-empty")
        runner.check(
            "Reflective Memory: load_all() returns empty list for new store",
            empty_reflective_memory.load_all() == [],
        )
        runner.check(
            "Reflective Memory: load_all() returns entries after approval",
            len(reflective_memory.load_all()) == 2,
            detail=str([entry.observation for entry in reflective_memory.load_all()]),
        )
        runner.check(
            "Reflective Memory: count() returns 0 for empty store",
            empty_reflective_memory.count() == 0,
            detail=str(empty_reflective_memory.count()),
        )
        empty_display = empty_reflective_memory.format_for_display()
        runner.check(
            'Reflective Memory: format_for_display() returns "No reflections" for empty',
            "No reflections" in empty_display,
            detail=empty_display,
        )
        filled_display = reflective_memory.format_for_display()
        runner.check(
            "Reflective Memory: format_for_display() includes observation",
            "Pattern noticed" in filled_display,
            detail=filled_display,
        )
        observation, context = extract_reflection_proposal(
            "Answer. [REFLECT: I become steadier in governed review. | context: repeated approval flows]"
        )
        runner.check(
            "Reflective Memory: extract_reflection_proposal() extracts correctly",
            observation == "I become steadier in governed review."
            and context == "repeated approval flows",
            detail=f"observation={observation!r} context={context!r}",
        )
        missing_observation, missing_context = extract_reflection_proposal("No reflection tag here.")
        runner.check(
            "Reflective Memory: extract_reflection_proposal() returns None for no match",
            missing_observation is None and missing_context is None,
        )
        runner.check(
            "Reflective Memory: build_reflection_grounding() returns empty string for no entries",
            build_reflection_grounding(empty_reflective_memory) == "",
            detail=build_reflection_grounding(empty_reflective_memory),
        )
        runner.check(
            'Reflective Memory: "inanna-reflect" command exists in server.py',
            'elif command_name == "inanna-reflect":' in server_source,
        )
        runner.check(
            "Reflective Memory: ReflectiveMemory is instantiated in server.py",
            "self.reflective_memory = ReflectiveMemory" in server_source,
        )
        runner.check(
            "Reflective Memory: reflection grounding is appended in main.py",
            "build_reflection_grounding" in inspect.getsource(sync_profile_grounding),
        )

    cycle5_ok, cycle5_detail, cycle5_stdout = run_script(VERIFY_CYCLE5_PATH)
    runner.check(
        "Cycle 5 Regression: py -3 verify_cycle5.py still passes all 90 checks",
        cycle5_ok and "All 90 checks passed." in cycle5_stdout,
        detail=cycle5_detail,
    )

    runner.check(
        "Documentation: docs/memory_architecture.md exists",
        MEMORY_ARCHITECTURE_PATH.exists(),
    )
    runner.check(
        "Documentation: docs/cycle6_master_plan.md exists",
        CYCLE6_MASTER_PLAN_PATH.exists(),
    )
    runner.check(
        "Documentation: docs/llm_configuration.md exists",
        LLM_CONFIGURATION_PATH.exists(),
    )
    runner.check(
        "Documentation: identity.py has LLM comment block",
        "# LLM configuration:" in identity_source,
    )
    runner.check(
        'Identity: CURRENT_PHASE = "Cycle 6 - Phase 6.9 - The Relational Proof"',
        CURRENT_PHASE == "Cycle 6 - Phase 6.9 - The Relational Proof",
        detail=CURRENT_PHASE,
    )
    runner.check(
        "Identity: CYCLE6_SUMMARY exists and describes the Relational Memory",
        all(token in CYCLE6_SUMMARY for token in ("Relational Memory", "UserProfile", "IdentityFormatter", "reflection.jsonl")),
        detail=CYCLE6_SUMMARY,
    )

    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
