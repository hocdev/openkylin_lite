from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import live_session_guard as guard


class LiveSessionGuardTests(unittest.TestCase):
    def test_repeated_crashes_have_a_recovery_limit(self):
        with patch.object(guard.time, 'sleep'), \
                patch.object(guard, 'running', side_effect=lambda name: name == 'ukui-session'), \
                patch.object(guard, 'run', return_value=CompletedProcess([], 0, '', '')), \
                patch.object(guard.subprocess, 'Popen') as launch:
            guard.watch_panel()
            self.assertEqual(launch.call_count, 3)

    def test_installed_system_does_nothing(self):
        with patch.object(Path, 'read_text', return_value='quiet splash'), patch.object(guard, 'configure') as configure:
            guard.main()
            configure.assert_not_called()

    def test_healthy_panel_is_never_restarted(self):
        with patch.object(guard.time, 'sleep'), patch.object(guard, 'running', side_effect=[True, True, False]), \
                patch.object(guard.subprocess, 'Popen') as launch:
            guard.watch_panel()
            launch.assert_not_called()

    def test_exited_panel_is_recovered_after_grace_period(self):
        states = [True, False, True, False, True, False, True, False, False]
        with patch.object(guard.time, 'sleep'), patch.object(guard, 'running', side_effect=states), \
                patch.object(guard, 'run', return_value=CompletedProcess([], 0, 'journal', '')), \
                patch.object(guard.subprocess, 'Popen') as launch:
            guard.watch_panel()
            launch.assert_called_once()
            self.assertEqual(launch.call_args.args[0], ['ukui-panel'])

    def test_native_recovery_wins_race(self):
        states = [True, False, True, False, True, False, True, True, False]
        with patch.object(guard.time, 'sleep'), patch.object(guard, 'running', side_effect=states), \
                patch.object(guard, 'run', return_value=CompletedProcess([], 0, '', '')), \
                patch.object(guard.subprocess, 'Popen') as launch:
            guard.watch_panel()
            launch.assert_not_called()
