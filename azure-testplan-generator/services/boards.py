"""Boards service for WIQL queries and user story retrieval."""

from __future__ import annotations

from typing import Any

from models.entities import UserStory
from services.azure_connection import AzureConnection


class BoardsService:
    """Service for Azure Boards operations."""

    WORK_ITEM_TYPE = "Historia de Usuario"

    def __init__(self, connection: AzureConnection, project: str, area_path: str) -> None:
        self._connection = connection
        self._project = project
        self._area_path = area_path

    def get_user_stories_for_iteration(self, iteration_path: str) -> list[UserStory]:
        """Get all user stories from given iteration path."""
        wiql = self._build_wiql(iteration_path)
        query_result = self._connection.request("POST", "/wit/wiql", payload={"query": wiql})
        work_items = query_result.get("workItems", [])
        if not work_items:
            return []

        ids = [item["id"] for item in work_items if "id" in item]
        return self._get_work_items(ids)

    def _build_wiql(self, iteration_path: str) -> str:
        return (
            "SELECT [System.Id] "
            "FROM WorkItems "
            "WHERE [System.TeamProject] = @project "
            f"AND [System.WorkItemType] = '{self.WORK_ITEM_TYPE}' "
            f"AND [System.AreaPath] UNDER '{self._area_path}' "
            f"AND [System.IterationPath] = '{iteration_path}' "
            "ORDER BY [System.Id] ASC"
        )

    def _get_work_items(self, ids: list[int]) -> list[UserStory]:
        """Read work item details in batches to avoid URL size limits."""
        all_stories: list[UserStory] = []
        batch_size = 200
        for index in range(0, len(ids), batch_size):
            chunk = ids[index : index + batch_size]
            ids_param = ",".join(str(item_id) for item_id in chunk)
            endpoint = (
                "/wit/workitems"
                f"?ids={ids_param}"
                "&fields=System.Id,System.Title"
            )
            data = self._connection.request("GET", endpoint, add_api_version=True)
            all_stories.extend(self._to_user_stories(data.get("value", [])))
        return all_stories

    @staticmethod
    def _to_user_stories(items: list[dict[str, Any]]) -> list[UserStory]:
        stories: list[UserStory] = []
        for item in items:
            fields = item.get("fields", {})
            story_id = fields.get("System.Id", item.get("id"))
            title = fields.get("System.Title", "").strip()
            if story_id is None or not title:
                continue
            stories.append(UserStory(id=int(story_id), title=title))
        return stories

