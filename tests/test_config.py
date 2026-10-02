import os
import unittest
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError

from fortigate_8_0_0_copilot.config import Settings


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.env_file = Path(directory.name) / ".env"

    def test_defaults_without_env_file(self) -> None:
        settings = Settings(_env_file=None)
        self.assertEqual(settings.app_env, "development")
        self.assertEqual(settings.log_level, "INFO")

    def test_loads_env_file(self) -> None:
        self.env_file.write_text("APP_ENV=staging\nLOG_LEVEL=DEBUG\n", encoding="utf-8")
        settings = Settings(_env_file=self.env_file)
        self.assertEqual(settings.app_env, "staging")
        self.assertEqual(settings.log_level, "DEBUG")

    def test_environment_overrides_env_file(self) -> None:
        self.env_file.write_text(
            "APP_ENV=development\nLOG_LEVEL=INFO\n", encoding="utf-8"
        )
        with patch.dict(os.environ, {"APP_ENV": "production", "LOG_LEVEL": "ERROR"}):
            settings = Settings(_env_file=self.env_file)
        self.assertEqual(settings.app_env, "production")
        self.assertEqual(settings.log_level, "ERROR")

    def test_unrelated_env_file_keys_are_ignored(self) -> None:
        self.env_file.write_text(
            "APP_ENV=testing\nUNRELATED_KEY=value\n", encoding="utf-8"
        )
        settings = Settings(_env_file=self.env_file)
        self.assertEqual(settings.app_env, "testing")
        self.assertEqual(settings.log_level, "INFO")

    def test_invalid_log_level_is_rejected(self) -> None:
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            with self.assertRaises(ValidationError) as raised:
                Settings(_env_file=None)
        self.assertEqual(raised.exception.errors()[0]["loc"], ("log_level",))

    def test_supported_log_levels(self) -> None:
        for level in (
            "CRITICAL",
            "FATAL",
            "ERROR",
            "WARNING",
            "WARN",
            "INFO",
            "DEBUG",
            "NOTSET",
        ):
            with self.subTest(level=level):
                with patch.dict(os.environ, {"LOG_LEVEL": level}):
                    self.assertEqual(Settings(_env_file=None).log_level, level)

    def test_default_env_file_does_not_depend_on_working_directory(self) -> None:
        project_env_file = Path(__file__).resolve().parents[1] / ".env"
        with chdir(self.env_file.parent):
            self.assertEqual(Settings.model_config["env_file"], project_env_file)
            self.assertEqual(Settings.model_config["env_file_encoding"], "utf-8")
            self.assertEqual(
                Settings().model_dump(),
                Settings(_env_file=project_env_file).model_dump(),
            )


if __name__ == "__main__":
    unittest.main()
