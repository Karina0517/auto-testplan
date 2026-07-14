"""Test Suite service operations."""

from __future__ import annotations

from typing import Any

from services.azure_connection import AzureConnection


class SuitesService:
    """Service for test suite lookup and creation."""

    def __init__(self, connection: AzureConnection) -> None:
        self._connection = connection

    def list_suites(self, plan_id: int) -> list[dict[str, Any]]:
        """List suites in a test plan."""
        response = self._connection.request(
            "GET",
            f"/testplan/Plans/{plan_id}/suites?asTreeView=true",
        )
        raw_suites = response.get("value", [])
        return self._flatten_suites(raw_suites)

    def create_static_suite(
        self,
        plan_id: int,
        parent_suite_id: int,
        suite_name: str,
    ) -> dict[str, Any]:
        """Create static suite under parent suite.

        The testplan REST API (7.1) expects the parent suite in the request body
        (``parentSuite.id``), not in the URL path. Sending it only in the path
        leaves ``TestSuiteCreateParams.ParentSuite`` null and Azure rejects it.
        """
        payload = {
            "suiteType": "StaticTestSuite",
            "name": suite_name,
            "parentSuite": {"id": parent_suite_id},
        }
        endpoint = f"/testplan/Plans/{plan_id}/suites"
        return self._connection.request("POST", endpoint, payload=payload)

    @staticmethod
    def get_root_suite_id(plan_data: dict[str, Any], suites: list[dict[str, Any]]) -> int | None:
        """Resolve root suite id from plan payload or suites listing."""
        root_suite = plan_data.get("rootSuite")
        if isinstance(root_suite, dict) and root_suite.get("id") is not None:
            return int(root_suite["id"])

        for suite in suites:
            if suite.get("parentSuite") is None and suite.get("id") is not None:
                return int(suite["id"])
        return None

    def get_child_suite_names(self, plan_id: int, parent_suite_id: int) -> set[str]:
        """Return normalized names of the direct child suites under a parent suite.

        Scoping duplicate detection to the direct children of the sprint's main
        suite guarantees exactly one child suite per user story in that location,
        making re-runs idempotent regardless of suites that may exist elsewhere.
        """
        response = self._connection.request(
            "GET",
            f"/testplan/Plans/{plan_id}/suites?asTreeView=true",
        )
        raw_suites = response.get("value", [])
        parent_node = self._find_suite_node(raw_suites, parent_suite_id)
        children = parent_node.get("children", []) if parent_node else []
        return {
            self.normalize_name(child.get("name", ""))
            for child in children
            if self.normalize_name(child.get("name", ""))
        }

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a suite name for robust duplicate detection.

        Collapses surrounding/repeated whitespace and case-folds so that minor
        formatting differences do not lead to duplicate suites.
        """
        return " ".join(str(name).split()).casefold()

    def _find_suite_node(
        self,
        suites: list[dict[str, Any]],
        suite_id: int,
    ) -> dict[str, Any] | None:
        for suite in suites:
            if suite.get("id") == suite_id:
                return suite
            found = self._find_suite_node(suite.get("children", []), suite_id)
            if found is not None:
                return found
        return None

    def _flatten_suites(self, suites: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flattened: list[dict[str, Any]] = []
        for suite in suites:
            flattened.append(suite)
            children = suite.get("children", [])
            if children:
                flattened.extend(self._flatten_suites(children))
        return flattened

