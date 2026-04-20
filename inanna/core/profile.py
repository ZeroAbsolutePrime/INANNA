from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UserProfile:
    user_id: str
    version: str = "1.0"
    created_at: str = field(default_factory=utc_now)
    last_updated: str = field(default_factory=utc_now)

    # Identity
    preferred_name: str = ""
    pronouns: str = ""
    gender: str = ""
    sex: str = ""
    languages: list[str] = field(default_factory=list)
    timezone: str = ""
    location_city: str = ""
    location_region: str = ""
    location_country: str = ""

    # Organizational
    departments: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    notification_scope: str = "realm"

    # Communication (observed by INANNA)
    communication_style: str = ""
    preferred_length: str = ""
    formality: str = ""
    observed_patterns: list[str] = field(default_factory=list)

    # Interests (observed by INANNA)
    domains: list[str] = field(default_factory=list)
    recurring_topics: list[str] = field(default_factory=list)
    named_projects: list[str] = field(default_factory=list)

    # Trust patterns
    session_trusted_tools: list[str] = field(default_factory=list)
    persistent_trusted_tools: list[str] = field(default_factory=list)

    # Onboarding
    onboarding_completed: bool = False
    onboarding_completed_at: str = ""
    survey_responses: dict[str, Any] = field(default_factory=dict)

    # INANNA's observations (proposal-governed)
    inanna_notes: list[str] = field(default_factory=list)


class ProfileManager:
    def __init__(self, profiles_dir: Path) -> None:
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, user_id: str) -> Path:
        return self.profiles_dir / f"{user_id}.json"

    def ensure_profile_exists(self, user_id: str) -> UserProfile:
        if self._profile_path(user_id).exists():
            loaded = self.load(user_id)
            return loaded if loaded is not None else UserProfile(user_id=user_id)
        profile = UserProfile(user_id=user_id)
        self.save(profile)
        return profile

    def load(self, user_id: str) -> UserProfile | None:
        path = self._profile_path(user_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return UserProfile(user_id=user_id)
            known = set(UserProfile.__dataclass_fields__.keys())
            filtered = {key: value for key, value in data.items() if key in known}
            filtered.setdefault("user_id", user_id)
            return UserProfile(**filtered)
        except Exception:
            return UserProfile(user_id=user_id)

    def save(self, profile: UserProfile) -> None:
        profile.last_updated = utc_now()
        data = {key: getattr(profile, key) for key in profile.__dataclass_fields__}
        self._profile_path(profile.user_id).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def update_field(self, user_id: str, field_name: str, value: Any) -> bool:
        profile = self.load(user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
        if not hasattr(profile, field_name):
            return False
        setattr(profile, field_name, value)
        self.save(profile)
        return True

    def delete(self, user_id: str) -> bool:
        path = self._profile_path(user_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_profiles(self) -> list[UserProfile]:
        profiles: list[UserProfile] = []
        for path in sorted(self.profiles_dir.glob("*.json")):
            profile = self.load(path.stem)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def display_name_for(self, user_id: str, fallback: str = "") -> str:
        profile = self.load(user_id)
        if profile is not None and profile.preferred_name:
            return profile.preferred_name
        return fallback

    def pronouns_for(self, user_id: str) -> str:
        profile = self.load(user_id)
        if profile is not None:
            return profile.pronouns
        return ""


class NotificationStore:
    def __init__(self, notifications_dir: Path) -> None:
        self.notifications_dir = notifications_dir
        self.notifications_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: str) -> Path:
        return self.notifications_dir / f"{user_id}.json"

    def _load_all(self, user_id: str) -> list[dict[str, Any]]:
        path = self._path(user_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _save_all(self, user_id: str, notifications: list[dict[str, Any]]) -> None:
        self._path(user_id).write_text(
            json.dumps(notifications, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, user_id: str, notification: dict[str, Any]) -> None:
        notifications = self._load_all(user_id)
        notifications.append(dict(notification))
        self._save_all(user_id, notifications)

    def load_pending(self, user_id: str) -> list[dict[str, Any]]:
        return [
            dict(notification)
            for notification in self._load_all(user_id)
            if not bool(notification.get("delivered", False))
        ]

    def mark_delivered(self, user_id: str, notification_id: str) -> bool:
        notifications = self._load_all(user_id)
        changed = False
        for notification in notifications:
            if str(notification.get("notification_id", "")).strip() != notification_id:
                continue
            notification["delivered"] = True
            changed = True
        if changed:
            self._save_all(user_id, notifications)
        return changed

    def clear_delivered(self, user_id: str) -> None:
        path = self._path(user_id)
        notifications = [
            notification
            for notification in self._load_all(user_id)
            if not bool(notification.get("delivered", False))
        ]
        if notifications:
            self._save_all(user_id, notifications)
            return
        if path.exists():
            path.unlink()


class CommunicationObserver:
    """Observes conversation patterns and updates the user profile silently."""

    SHORT_MSG_CHARS = 80
    LONG_MSG_CHARS = 300
    FORMAL_INDICATORS = [
        "please",
        "would you",
        "could you",
        "kindly",
        "regard",
        "sincerely",
        "thank you",
        "appreciate",
        "request",
    ]
    CASUAL_INDICATORS = [
        "hey",
        "yeah",
        "ok",
        "cool",
        "awesome",
        "sure",
        "nope",
        "thanks",
        "thx",
        "lol",
        "btw",
        "idk",
    ]

    def __init__(self, profile_manager: ProfileManager) -> None:
        self.profile_manager = profile_manager

    def observe_session(
        self,
        user_id: str,
        messages: list[str],
        topics: list[str],
    ) -> None:
        if not messages or not user_id:
            return

        profile = self.profile_manager.load(user_id)
        if profile is None:
            return

        avg_len = sum(len(message) for message in messages) / len(messages)
        if avg_len < self.SHORT_MSG_CHARS:
            length_pref = "short"
        elif avg_len > self.LONG_MSG_CHARS:
            length_pref = "long"
        else:
            length_pref = "medium"

        all_text = " ".join(messages).lower()
        formal_score = sum(1 for word in self.FORMAL_INDICATORS if word in all_text)
        casual_score = sum(1 for word in self.CASUAL_INDICATORS if word in all_text)
        if formal_score > casual_score + 1:
            formality = "formal"
        elif casual_score > formal_score + 1:
            formality = "casual"
        else:
            formality = "mixed"

        self.profile_manager.update_field(user_id, "preferred_length", length_pref)
        self.profile_manager.update_field(user_id, "formality", formality)

        if topics:
            existing = profile.recurring_topics or []
            normalized_topics = [topic.strip().lower() for topic in topics if topic.strip()]
            merged = list(dict.fromkeys(existing + normalized_topics))[-20:]
            self.profile_manager.update_field(user_id, "recurring_topics", merged)


class IdentityFormatter:
    """
    Provides identity-aware formatting for INANNA's language.
    Used when INANNA refers to a person in third person,
    formats times, or constructs greetings.
    """

    PRONOUN_SETS: dict[str, dict[str, str]] = {
        "she/her":   {"subject": "she",  "object": "her",
                      "possessive": "her",   "reflexive": "herself"},
        "he/him":    {"subject": "he",   "object": "him",
                      "possessive": "his",   "reflexive": "himself"},
        "they/them": {"subject": "they", "object": "them",
                      "possessive": "their", "reflexive": "themselves"},
        "ze/zir":    {"subject": "ze",   "object": "zir",
                      "possessive": "zir",   "reflexive": "zirself"},
        "xe/xem":    {"subject": "xe",   "object": "xem",
                      "possessive": "xyr",   "reflexive": "xemself"},
    }
    _DEFAULT = "they/them"

    def __init__(self, profile_manager: ProfileManager) -> None:
        self.profile_manager = profile_manager

    def address(self, user_id: str, fallback: str = "") -> str:
        """Returns the name INANNA should use when addressing this person."""
        return self.profile_manager.display_name_for(user_id, fallback)

    def pronouns(self, user_id: str) -> dict[str, str]:
        """Returns the full pronoun set for a user, defaulting to they/them."""
        raw = self.profile_manager.pronouns_for(user_id).lower().strip()
        for key, pset in self.PRONOUN_SETS.items():
            if raw.startswith(key.split("/")[0]):
                return pset
        return self.PRONOUN_SETS[self._DEFAULT]

    def subject(self, user_id: str) -> str:
        """Returns the subject pronoun: she, he, they, ze, xe."""
        return self.pronouns(user_id)["subject"]

    def object_pronoun(self, user_id: str) -> str:
        """Returns the object pronoun: her, him, them, zir, xem."""
        return self.pronouns(user_id)["object"]

    def possessive(self, user_id: str) -> str:
        """Returns the possessive pronoun: her, his, their, zir, xyr."""
        return self.pronouns(user_id)["possessive"]

    def format_greeting(self, user_id: str, fallback: str = "") -> str:
        """Returns a natural greeting using the person's preferred name."""
        name = self.address(user_id, fallback)
        return f"Welcome back, {name}." if name else "Welcome back."

    def format_time(self, iso_timestamp: str, user_id: str) -> str:
        """Formats a timestamp in the user's timezone if set."""
        profile = self.profile_manager.load(user_id)
        tz_name = profile.timezone if profile else ""
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            if tz_name:
                try:
                    import zoneinfo
                    tz = zoneinfo.ZoneInfo(tz_name)
                    dt = dt.astimezone(tz)
                    return dt.strftime(f"%b %d %H:%M ({tz_name})")
                except Exception:
                    pass
            return dt.strftime("%b %d %H:%M")
        except Exception:
            return iso_timestamp[:16].replace("T", " ")
