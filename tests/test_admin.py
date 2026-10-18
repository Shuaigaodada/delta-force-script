import os
import unittest
from unittest.mock import patch

from src.utils import admin


class AdminTest(unittest.TestCase):
    def test_does_not_relaunch_after_failed_elevation(self):
        with patch.dict(os.environ, {"DELTA_FORCE_ELEVATION_ATTEMPTED": "1"}), \
             patch.object(admin, "is_admin", return_value=False), \
             patch.object(admin, "relaunch_launcher_as_admin") as relaunch:
            self.assertFalse(admin.ensure_admin_or_relaunch_launcher())
            relaunch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
