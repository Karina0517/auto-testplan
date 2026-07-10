"""Test Plan service operations."""

from __future__ import annotations

from typing import Any

from services.azure_connection import AzureConnection


class TestPlansService:
    """Service for Test Plan retrieval and creation."""

    def __init__(self, connection: AzureConnection) -> None:
        self._connection = connection

    def find_plan_by_name(self, plan_name: str) -> dict[str, Any] | None:
        """Return test plan by exact name if it exists."""
        endpoint = "/testplan/plans"
        token = ""

        while True:
            paged_endpoint = endpoint
            if token:
                paged_endpoint = f"{endpoint}?continuationToken={token}"
            response = self._connection.request("GET", paged_endpoint, add_api_version=True)
            plans = response.get("value", [])
            for plan in plans:
                if str(plan.get("name", "")).strip() == plan_name:
                    return plan

            token = str(response.get("continuationToken", "")).strip()
            if not token:
                break

        return None

    def create_plan(self, name: str, area_path: str, iteration_path: str) -> dict[str, Any]:
        """Create a new test plan."""
        payload = {
            "name": name,
            "areaPath": area_path,
            "iteration": iteration_path,
        }
        return self._connection.request("POST", "/testplan/plans", payload=payload)

    def get_or_create_plan(
        self,
        plan_name: str,
        area_path: str,
        iteration_path: str,
    ) -> tuple[dict[str, Any], bool]:
        """Get existing plan or create it when missing."""
        existing = self.find_plan_by_name(plan_name)
        if existing:
            return existing, False
        created = self.create_plan(plan_name, area_path, iteration_path)
        return created, True

    def get_plan(self, plan_id: int) -> dict[str, Any]:
        """Get plan details by id."""
        return self._connection.request("GET", f"/testplan/plans/{plan_id}")

