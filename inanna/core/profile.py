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
