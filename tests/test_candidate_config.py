"""Dependency-free safeguards for candidate API environment defaults.

Evaluate only the checked-in assignment expressions, without importing web
frameworks, starting a database client, or accessing any live credentials.
"""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = ("server.py", "api-service/main.py")


def assignment_value(entrypoint, name, variables):
    path = ROOT / entrypoint
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [
        node.value for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == name
    ]
    if len(matches) != 1:
        raise AssertionError(f"{entrypoint}: expected exactly one {name} assignment")
    fake_os = SimpleNamespace(getenv=lambda key, default=None: variables.get(key, default))
    expression = ast.Expression(body=matches[0])
    return eval(compile(expression, str(path), "eval"),
                {"__builtins__": {}}, {"os": fake_os})


class CandidateDefaultsTests(unittest.TestCase):
    def test_blank_database_name_uses_safe_default(self):
        for entry in ENTRYPOINTS:
            for value in (None, "", " ", "\t "):
                with self.subTest(entry=entry, value=value):
                    variables = {} if value is None else {"DB_NAME": value}
                    self.assertEqual(assignment_value(entry, "DB_NAME", variables), "wrenchrelay")

    def test_explicit_database_name_is_respected(self):
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                self.assertEqual(
                    assignment_value(entry, "DB_NAME", {"DB_NAME": " pilot_sandbox "}),
                    "pilot_sandbox",
                )

    def test_legal_entity_defaults_to_current_business(self):
        for entry in ENTRYPOINTS:
            for value in (None, "", " \t "):
                with self.subTest(entry=entry, value=value):
                    variables = {} if value is None else {"LEGAL_ENTITY_NAME": value}
                    self.assertEqual(
                        assignment_value(entry, "LEGAL_ENTITY_NAME", variables),
                        "WrenchRelay LLC",
                    )

    def test_explicit_legal_entity_is_preserved(self):
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                self.assertEqual(
                    assignment_value(entry, "LEGAL_ENTITY_NAME",
                                     {"LEGAL_ENTITY_NAME": " Approved Entity "}),
                    "Approved Entity",
                )

    def test_missing_database_connection_is_not_invented(self):
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                self.assertIsNone(assignment_value(entry, "MONGO_URL", {}))
                self.assertEqual(
                    assignment_value(entry, "MONGO_URL", {"MONGODB_URI": "mongo_fixture"}),
                    "mongo_fixture",
                )


if __name__ == "__main__":
    unittest.main()
