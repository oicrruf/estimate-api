"""AT-264 contract tests using only fictional JSON fixtures."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, cast, get_args

from estimate_api.contracts.universal_v1 import (
    SCHEMA_PATH,
    SCHEMA_VERSION,
    EntityKind,
    validate_project_document,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
KINDS = {
    "ProjectGoal",
    "Requirement",
    "Capability",
    "Resource",
    "Task",
    "Deliverable",
    "Constraint",
    "SiteCondition",
    "Evidence",
    "Dependency",
    "BOMLine",
    "Rule",
    "Approval",
}


def fixture(group: str, name: str) -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads((FIXTURES / group / f"{name}.json").read_text(encoding="utf-8"))
    )


class ContractTests(unittest.TestCase):
    def test_three_domains_use_one_core(self) -> None:
        for name in ("cameras", "painting", "event"):
            with self.subTest(name=name):
                document = fixture("valid", name)
                result = validate_project_document(document)
                self.assertTrue(result.valid, result.issues)
                self.assertEqual(document["schemaVersion"], SCHEMA_VERSION)
                self.assertTrue(document["packages"])
                self.assertTrue(all(package["facts"] for package in document["packages"]))
                self.assertTrue(all("facts" not in entity for entity in document["entities"]))

    def test_all_thirteen_generic_kinds(self) -> None:
        self.assertEqual(
            {entity["kind"] for entity in fixture("valid", "cameras")["entities"]}, KINDS
        )

    def test_schema_and_python_types_share_version_and_kinds(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schemaVersion"]["const"], SCHEMA_VERSION)
        self.assertEqual(
            set(schema["$defs"]["entity"]["properties"]["kind"]["enum"]),
            set(get_args(EntityKind.__value__)),
        )

    def test_all_negative_fixtures(self) -> None:
        for path in sorted((FIXTURES / "invalid").glob("*.json")):
            with self.subTest(name=path.stem):
                result = validate_project_document(fixture("invalid", path.stem))
                self.assertFalse(result.valid)
                self.assertTrue(result.issues)
                self.assertIsNone(result.document)

    def test_reference_and_uniqueness_paths(self) -> None:
        cases = (
            ("duplicate-id", "/entities/1/id", "duplicate id"),
            ("broken-relation", "/entities/1/relations/0/targetId", "unknown entity id"),
            ("broken-package-subject", "/packages/0/subjectId", "unknown entity id"),
        )
        for name, path, message in cases:
            with self.subTest(name=name):
                result = validate_project_document(fixture("invalid", name))
                self.assertIn(
                    (path, message), {(issue.path, issue.message) for issue in result.issues}
                )

    def test_project_id_must_target_goal(self) -> None:
        document = fixture("valid", "event")
        document["projectId"] = "event:crew"
        result = validate_project_document(document)
        self.assertIn("/projectId", {issue.path for issue in result.issues})

    def test_package_id_shares_global_namespace(self) -> None:
        document = fixture("valid", "painting")
        document["packages"][0]["id"] = document["entities"][0]["id"]
        result = validate_project_document(document)
        self.assertIn("/packages/0/id", {issue.path for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
