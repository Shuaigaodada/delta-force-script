import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import src.main as app


class MainWorkflowTest(unittest.TestCase):
    def test_add_and_delete_account(self):
        with tempfile.TemporaryDirectory() as directory:
            account_path = Path(directory) / "accounts.json"
            with (
                patch.object(app, "ACCOUNTS", []),
                patch.object(app, "data_path", return_value=account_path),
                patch("builtins.print"),
            ):
                self.assertTrue(app.add_account(lambda _: "1000000000"))
                self.assertEqual(json.loads(account_path.read_text(encoding="utf-8")), ["1000000000"])

                keys = iter(("confirm", "down", "confirm"))
                self.assertTrue(app.delete_account(lambda: next(keys)))
                self.assertEqual(json.loads(account_path.read_text(encoding="utf-8")), [])

    def test_skip_menu_accepts_multiple_platforms(self):
        keys = iter(("toggle", "down", "down", "toggle", "confirm"))
        with patch("builtins.print"):
            self.assertEqual(app.choose_skipped_platforms(lambda: next(keys)), frozenset({0, 2}))

    def test_stops_after_failed_step(self):
        with patch.object(app.workflow, "login_account", return_value=False), \
             patch.object(app.workflow, "open_game") as open_game:
            with self.assertRaisesRegex(RuntimeError, "登录账户失败"):
                app._workflow("test-account", s=0)
            open_game.assert_not_called()


if __name__ == "__main__":
    unittest.main()
