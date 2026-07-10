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
        """Create static suite under parent suite."""
        payload = {
            "suiteType": "StaticTestSuite",
            "name": suite_name,
        }
        endpoint = f"/testplan/Plans/{plan_id}/suites/{parent_suite_id}"
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

    @staticmethod
    def suite_name_set(suites: list[dict[str, Any]]) -> set[str]:
        """Return a set of suite names for duplicate detection."""
        return {
            str(suite.get("name", "")).strip()
            for suite in suites
            if str(suite.get("name", "")).strip()
        }

    def _flatten_suites(self, suites: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flattened: list[dict[str, Any]] = []
        for suite in suites:
            flattened.append(suite)
            children = suite.get("children", [])
            if children:
                flattened.extend(self._flatten_suites(children))
        return flattened

