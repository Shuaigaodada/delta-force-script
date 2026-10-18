import unittest
from unittest.mock import patch

from src.core import capture
from src.core import processes


class ProcessesTest(unittest.TestCase):
    def test_enum_callback_continues_and_collects_matching_window(self):
        def enumerate_one(callback, _):
            self.assertIs(callback(123, None), True)

        with patch.object(processes.win32gui, "EnumWindows", side_effect=enumerate_one), \
             patch.object(processes.win32gui, "IsWindowVisible", return_value=True), \
             patch.object(processes.win32process, "GetWindowThreadProcessId", return_value=(1, 456)):
            self.assertEqual(processes.find_hwnds_by_pid(456), [123])

    def test_capture_uses_the_process_window_bounds(self):
        expected_region = {"left": 10, "top": 20, "width": 100, "height": 200}
        with patch.object(capture.processes, "find_hwnds_by_pid", return_value=[123]), \
             patch.object(capture.win32gui, "GetWindowText", return_value="三角洲行动"), \
             patch.object(capture.win32gui, "GetWindowRect", return_value=(10, 20, 110, 220)), \
             patch.object(capture, "region", return_value=("image", expected_region)):
            self.assertEqual(capture.window_by_pid(456), ("image", expected_region, 123))


if __name__ == "__main__":
    unittest.main()
