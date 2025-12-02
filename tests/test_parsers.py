import os
import unittest
from unittest import mock
from datetime import datetime

from bot.config import load_config
from bot.handlers.start import parse_date, parse_float


class ParseFloatTests(unittest.TestCase):
    def test_parses_dot_decimal(self) -> None:
        self.assertEqual(parse_float("12.5"), 12.5)

    def test_parses_comma_decimal(self) -> None:
        self.assertEqual(parse_float("3,14"), 3.14)

    def test_invalid_number_returns_none(self) -> None:
        self.assertIsNone(parse_float("abc"))


class ParseDateTests(unittest.TestCase):
    def test_parses_day_first_format(self) -> None:
        self.assertEqual(parse_date("31.12.2020"), datetime(2020, 12, 31))

    def test_parses_iso_format(self) -> None:
        self.assertEqual(parse_date("2020-12-31"), datetime(2020, 12, 31))

    def test_invalid_date_returns_none(self) -> None:
        self.assertIsNone(parse_date("31/12/2020"))


class ConfigTests(unittest.TestCase):
    def test_missing_token_raises_error(self) -> None:
        env = {"DATABASE_URL": "sqlite+aiosqlite:///test.db"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_config()


if __name__ == "__main__":
    unittest.main()
