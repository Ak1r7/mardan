from __future__ import annotations

import json
from pathlib import Path
import shutil
import socket
import subprocess
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ContactApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = free_port()
        cls.process = subprocess.Popen(
            ["php", "-S", f"127.0.0.1:{cls.port}", "-t", str(ROOT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(40):
            try:
                urlopen(cls.base + "/index.html", timeout=0.5).close()
                break
            except Exception:
                time.sleep(0.1)
        else:
            cls.process.terminate()
            raise RuntimeError("PHP test server did not start")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        cls.process.wait(timeout=5)
        for folder in [ROOT / "storage/rate", ROOT / "storage/submissions"]:
            for path in folder.glob("*"):
                if path.name != ".gitkeep":
                    path.unlink(missing_ok=True)
        log = ROOT / "storage/logs/contact.log"
        log.unlink(missing_ok=True)

    def post(self, payload: dict[str, str], origin: str | None = None) -> tuple[int, dict]:
        data = urlencode(payload).encode()
        headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
        if origin:
            headers["Origin"] = origin
        request = Request(self.base + "/api/contact.php", data=data, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=4) as response:
                return response.status, json.loads(response.read().decode())
        except HTTPError as error:
            return error.code, json.loads(error.read().decode())

    def valid_payload(self) -> dict[str, str]:
        return {
            "name": "Тестовый клиент",
            "phone": "+7 (962) 000-00-00",
            "message": "Квартира 60 м²",
            "formType": "contacts",
            "website": "",
            "form_started_at": str(int(time.time() * 1000) - 3000),
            "consent": "on",
        }

    def test_valid_submission(self) -> None:
        status, payload = self.post(self.valid_payload(), self.base)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])

    def test_invalid_phone_is_rejected(self) -> None:
        data = self.valid_payload()
        data["phone"] = "123"
        status, payload = self.post(data, self.base)
        self.assertEqual(status, 422)
        self.assertFalse(payload["ok"])

    def test_cross_origin_is_rejected(self) -> None:
        status, payload = self.post(self.valid_payload(), "https://example.com")
        self.assertEqual(status, 403)
        self.assertFalse(payload["ok"])

    def test_too_fast_submission_is_rejected(self) -> None:
        data = self.valid_payload()
        data["form_started_at"] = str(int(time.time() * 1000))
        status, payload = self.post(data, self.base)
        self.assertEqual(status, 422)
        self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
