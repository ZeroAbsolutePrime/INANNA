from __future__ import annotations

import asyncio
import http.client
import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.auth import AuthStore, hash_password, verify_password
import ui.server as ui_server


ROLES_PAYLOAD = {
    "roles": {
        "guardian": {
            "description": "Full system access - assigned directly only",
            "privileges": ["all"],
        },
        "operator": {
            "description": "Realm-scoped admin",
            "privileges": [
                "manage_users_in_realm",
                "approve_proposals_in_realm",
                "read_realm_audit_log",
                "invite_users",
            ],
        },
        "user": {
            "description": "Standard interaction",
            "privileges": [
                "converse",
                "approve_own_memory",
                "read_own_log",
                "forget_own_memory",
            ],
        },
    }
}


def write_roles_config(app_root: Path) -> None:
    config_dir = app_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "roles.json").write_text(
        json.dumps(ROLES_PAYLOAD, indent=2),
        encoding="utf-8",
    )


class DummyRequest:
    def __init__(self, path: str = "/app", cookie: str = "") -> None:
        self.path = path
        self.headers = {"Cookie": cookie} if cookie else {}


class DummyConnection:
    def __init__(self, path: str = "/app", cookie: str = "") -> None:
        self.request = DummyRequest(path=path, cookie=cookie)
        self.messages: list[dict[str, object]] = []
        self.closed: tuple[int | None, str | None] | None = None

    async def send(self, payload: str) -> None:
        self.messages.append(json.loads(payload))

    async def close(self, code: int | None = None, reason: str | None = None) -> None:
        self.closed = (code, reason)


class AuthStoreTests(unittest.TestCase):
    def make_store(self) -> tuple[TemporaryDirectory[str], AuthStore]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        return temp_dir, AuthStore(root)

    def seed_zaera(self, store: AuthStore):
        return store.seed_user("zaera", "ZAERA", "ETERNALOVE", "guardian")

    def test_auth_store_instantiates(self) -> None:
        _, store = self.make_store()
        self.assertIsInstance(store, AuthStore)

    def test_hash_password_returns_salt_hash_format(self) -> None:
        hashed = hash_password("ETERNALOVE")
        salt, digest = hashed.split(":", 1)
        self.assertTrue(salt)
        self.assertTrue(digest)

    def test_verify_password_returns_true_for_correct_password(self) -> None:
        hashed = hash_password("ETERNALOVE")
        self.assertTrue(verify_password("ETERNALOVE", hashed))

    def test_verify_password_returns_false_for_wrong_password(self) -> None:
        hashed = hash_password("ETERNALOVE")
        self.assertFalse(verify_password("wrong", hashed))

    def test_seed_user_creates_a_user(self) -> None:
        _, store = self.make_store()
        record = store.seed_user("zaera", "ZAERA", "ETERNALOVE", "guardian")
        self.assertEqual("zaera", record.user_id)
        self.assertIsNotNone(store.get_by_id("zaera"))

    def test_seed_user_is_idempotent(self) -> None:
        _, store = self.make_store()
        first = store.seed_user("zaera", "ZAERA", "ETERNALOVE", "guardian")
        second = store.seed_user("zaera", "ZAERA", "CHANGED", "guardian")
        self.assertEqual(first.password_hash, second.password_hash)

    def test_authenticate_returns_record_for_correct_credentials(self) -> None:
        _, store = self.make_store()
        self.seed_zaera(store)
        record = store.authenticate("ZAERA", "ETERNALOVE")
        self.assertIsNotNone(record)
        self.assertEqual("ZAERA", record.username if record else "")

    def test_authenticate_returns_none_for_wrong_password(self) -> None:
        _, store = self.make_store()
        self.seed_zaera(store)
        self.assertIsNone(store.authenticate("ZAERA", "wrong"))

    def test_authenticate_returns_none_for_unknown_username(self) -> None:
        _, store = self.make_store()
        self.seed_zaera(store)
        self.assertIsNone(store.authenticate("UNKNOWN", "ETERNALOVE"))

    def test_authenticate_is_case_insensitive_for_username(self) -> None:
        _, store = self.make_store()
        self.seed_zaera(store)
        record = store.authenticate("zaera", "ETERNALOVE")
        self.assertIsNotNone(record)
        self.assertEqual("ZAERA", record.username if record else "")

    def test_change_password_verifies_with_new_password(self) -> None:
        _, store = self.make_store()
        record = self.seed_zaera(store)
        store.change_password(record.user_id, "FOREVER")
        self.assertIsNotNone(store.authenticate("ZAERA", "FOREVER"))

    def test_password_is_stored_as_hash_never_plaintext(self) -> None:
        temp_dir, store = self.make_store()
        self.seed_zaera(store)
        contents = (Path(temp_dir.name) / "auth.json").read_text(encoding="utf-8")
        self.assertNotIn("ETERNALOVE", contents)
        self.assertIn("password_hash", contents)


class AuthServerFixture(unittest.TestCase):
    def make_interface_server(self) -> ui_server.InterfaceServer:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        original_app_root = ui_server.APP_ROOT
        ui_server.APP_ROOT = Path(temp_dir.name)
        self.addCleanup(lambda: setattr(ui_server, "APP_ROOT", original_app_root))
        write_roles_config(ui_server.APP_ROOT)
        patcher = patch.object(ui_server.Engine, "verify_connection", lambda _self: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        return ui_server.InterfaceServer()

    def start_http_server(self, server: ui_server.InterfaceServer) -> tuple[object, int]:
        httpd = ui_server.HTTPServer(("127.0.0.1", 0), ui_server.make_static_handler(server))
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 1)
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return httpd, int(httpd.server_address[1])

    def request(
        self,
        port: int,
        method: str,
        path: str,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        response_headers = {name: value for name, value in response.getheaders()}
        status = response.status
        connection.close()
        return status, response_headers, payload


class HttpAuthRouteTests(AuthServerFixture):
    def test_get_root_serves_login_when_unauthenticated(self) -> None:
        server = self.make_interface_server()
        _, port = self.start_http_server(server)

        status, headers, payload = self.request(port, "GET", "/")

        self.assertEqual(200, status)
        self.assertEqual("no-store", headers.get("Cache-Control"))
        self.assertIn("INANNA NYX", payload.decode("utf-8"))

    def test_post_login_returns_cookie_for_valid_credentials(self) -> None:
        server = self.make_interface_server()
        _, port = self.start_http_server(server)

        status, headers, payload = self.request(
            port,
            "POST",
            "/login",
            body=json.dumps({"username": "ZAERA", "password": "ETERNALOVE"}),
            headers={"Content-Type": "application/json"},
        )

        data = json.loads(payload.decode("utf-8"))
        self.assertEqual(200, status)
        self.assertEqual("ZAERA", data["username"])
        self.assertEqual("guardian", data["role"])
        self.assertIn("inanna_token=", headers.get("Set-Cookie", ""))

    def test_get_app_redirects_to_login_when_unauthenticated(self) -> None:
        server = self.make_interface_server()
        _, port = self.start_http_server(server)

        status, headers, _ = self.request(port, "GET", "/app")

        self.assertEqual(302, status)
        self.assertEqual("/login", headers.get("Location"))

    def test_get_app_serves_index_after_login_cookie(self) -> None:
        server = self.make_interface_server()
        _, port = self.start_http_server(server)

        _, login_headers, _ = self.request(
            port,
            "POST",
            "/login",
            body=json.dumps({"username": "ZAERA", "password": "ETERNALOVE"}),
            headers={"Content-Type": "application/json"},
        )
        cookie = login_headers.get("Set-Cookie", "").split(";", 1)[0]
        status, _, payload = self.request(
            port,
            "GET",
            "/app",
            headers={"Cookie": cookie},
        )

        self.assertEqual(200, status)
        self.assertIn("INANNA NYX", payload.decode("utf-8"))


class WebsocketAuthTests(AuthServerFixture):
    def test_websocket_initial_state_requires_authenticated_cookie(self) -> None:
        server = self.make_interface_server()

        unauthenticated = DummyConnection()
        allowed = asyncio.run(server.send_initial_state(unauthenticated))
        self.assertFalse(allowed)
        self.assertEqual((1008, "Authentication required."), unauthenticated.closed)
        self.assertEqual([], unauthenticated.messages)

        token = server.login_from_auth("ZAERA", "ETERNALOVE")
        self.assertIsNotNone(token)
        authenticated = DummyConnection(cookie=f"inanna_token={token.token}")
        allowed = asyncio.run(server.send_initial_state(authenticated))

        self.assertTrue(allowed)
        self.assertIsNone(authenticated.closed)
        self.assertTrue(any(message.get("type") == "status" for message in authenticated.messages))


if __name__ == "__main__":
    unittest.main()
