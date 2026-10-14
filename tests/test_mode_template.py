"""Run from repository root: python -m unittest discover -s tests -p test_mode_template.py"""
from pathlib import Path
import unittest
from unittest import mock

from src.core import vision, workflow

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "data/screenshots/2026-09-06-login"
RUN_SHOTS = ROOT / "data/screenshots/2026-09-07-run"
LATEST_SHOTS = ROOT / "data/screenshots/2026-09-08-run"


class ModeTemplateTest(unittest.TestCase):
    def test_larger_template_does_not_call_opencv(self):
        import numpy as np

        found, score, top_left, bottom_right = vision.find_template(
            np.zeros((10, 10, 3), dtype=np.uint8),
            np.zeros((20, 20, 3), dtype=np.uint8),
        )
        self.assertEqual((found, score, top_left, bottom_right), (False, -1.0, None, None))

    def test_fenghuo_matches_only_the_mode_entry(self):
        template = vision.image_read(str(ROOT / "data/templates/delta_force/fenghuo1.png"))
        self.assertIsNotNone(template)
        screen = vision.image_read(str(SHOTS / "02-mode-selection.png"))
        self.assertIsNotNone(screen)
        found, score, top_left, bottom_right = vision.find_template(screen, template, 0.75)
        self.assertTrue(found, f"Fenghuo entry score: {score:.4f}")
        x, y = vision.box_center(top_left, bottom_right)
        self.assertTrue(88 <= x < 605 and 812 <= y < 996, (x, y))
        for name in ("01-launcher.png", "03-fenghuo-entry.png", "04-qq-password-login.png"):
            with self.subTest(screen=name):
                other = vision.image_read(str(SHOTS / name))
                self.assertIsNotNone(other)
                self.assertFalse(vision.find_template(other, template, 0.75)[0])

    def test_join_game_matches_fenghuo_intro(self):
        template = vision.image_read(str(ROOT / "data/templates/delta_force/join_game.png"))
        screen = vision.image_read(str(RUN_SHOTS / "05-fenghuo-intro.png"))
        found, score, top_left, bottom_right = vision.find_template(screen, template, 0.8)
        self.assertTrue(found, f"Join game score: {score:.4f}")
        x, y = vision.box_center(top_left, bottom_right)
        self.assertTrue(810 <= x < 1110 and 634 <= y < 693, (x, y))

    def test_hovered_fenghuo_template_matches_stuck_page(self):
        template = vision.image_read(str(ROOT / "data/templates/delta_force/fenghuo_hovered.png"))
        screen = vision.image_read(str(LATEST_SHOTS / "08-mode-selection-hovered-stuck.png"))
        found, score, top_left, bottom_right = vision.find_template(screen, template, 0.8)
        self.assertTrue(found, f"Hovered Fenghuo score: {score:.4f}")
        x, y = vision.box_center(top_left, bottom_right)
        self.assertTrue(88 <= x < 605 and 774 <= y < 1000, (x, y))

    def test_qq_authorization_button_matches_latest_popup(self):
        template = vision.image_read(str(ROOT / "data/templates/delta_force/shouquan.png"))
        screen = vision.image_read(str(LATEST_SHOTS / "07-qq-authorization.png"))
        found, score, top_left, bottom_right = vision.find_template(screen, template, 0.8)
        self.assertTrue(found, f"Authorization score: {score:.4f}")
        x, y = vision.box_center(top_left, bottom_right)
        self.assertTrue(710 <= x < 895 and 444 <= y < 490, (x, y))

    def test_open_game_retries_start_after_authorization(self):
        region = {"left": 0, "top": 0, "width": 100, "height": 100}
        matches = [
            (True, 1.0, (0, 0), (10, 10)),
            (True, 1.0, (20, 20), (30, 30)),
            (True, 1.0, (0, 0), (10, 10)),
            *[(False, 0.0, None, None)] * 10,
        ]
        with (
            mock.patch.object(workflow, "available_delta_force_window", return_value={"pid": 1}),
            mock.patch.object(workflow, "load_template", side_effect=[object(), object()]),
            mock.patch.object(workflow.capture, "window_by_pid", return_value=(object(), region, 1)),
            mock.patch.object(workflow.vision, "find_template", side_effect=matches),
            mock.patch.object(workflow.input, "click") as click,
            mock.patch.object(workflow.time, "sleep"),
        ):
            self.assertTrue(workflow.open_game())

        self.assertEqual(
            [call.args for call in click.call_args_list],
            [(5, 5), (25, 25), (5, 5)],
        )


if __name__ == "__main__":
    unittest.main()
