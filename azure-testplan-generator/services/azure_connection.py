"""HTTP connection and Azure DevOps API communication."""

from __future__ import annotations

import base64
from typing import Any

import requests

from config.settings import Settings


class AzureApiError(Exception):
    """Base class for Azure API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AzureAuthError(AzureApiError):
    """Authentication/authorization error."""


class AzureNotFoundError(AzureApiError):
    """Resource not found error."""


class AzureServerError(AzureApiError):
    """Azure DevOps server side error."""


class AzureNetworkError(AzureApiError):
    """Network or timeout error."""


class AzureConnection:
    """Azure DevOps REST API client wrapper."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._org = settings.azure_organization
        self._project = settings.azure_project
        self._api_version = settings.api_version
        self._timeout = settings.request_timeout_seconds
        self._base_project_url = (
            f"https://dev.azure.com/{self._org}/{self._project}/_apis"
        )
        self._auth_header = self._build_auth_header(settings.azure_pat)

    @staticmethod
    def _build_auth_header(pat: str) -> str:
        token_bytes = f":{pat}".encode("utf-8")
        return base64.b64encode(token_bytes).decode("utf-8")

    @property
    def default_headers(self) -> dict[str, str]:
        """Return headers for Azure DevOps requests."""
        return {
            "Authorization": f"Basic {self._auth_header}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def validate_connection(self) -> None:
        """Validate organization, project and PAT access."""
        endpoint = f"https://dev.azure.com/{self._org}/_apis/projects/{self._project}"
        self.request("GET", endpoint, add_api_version=True)

    def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        add_api_version: bool = True,
    ) -> dict[str, Any]:
        """Execute HTTP request and map known errors."""
        url = endpoint if endpoint.startswith("http") else f"{self._base_project_url}{endpoint}"
        if add_api_version:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}api-version={self._api_version}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.default_headers,
                json=payload,
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise AzureNetworkError("Timeout al conectar con Azure DevOps.") from exc
        except requests.exceptions.ConnectionError as exc:
            raise AzureNetworkError("No se pudo establecer conexión con Azure DevOps.") from exc
        except requests.exceptions.RequestException as exc:
            raise AzureNetworkError("Error de red inesperado en la llamada REST.") from exc

        self._raise_for_status(response)

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError:
            return {"raw_response": response.text}

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        status_code = response.status_code
        if status_code < 400:
            return

        message = AzureConnection._extract_error_message(response)
        if status_code in (401, 403):
            raise AzureAuthError(message, status_code=status_code)
        if status_code == 404:
            raise AzureNotFoundError(message, status_code=status_code)
        if status_code >= 500:
            raise AzureServerError(message, status_code=status_code)
        raise AzureApiError(message, status_code=status_code)

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        fallback = f"Error HTTP {response.status_code}: {response.reason}"
        try:
            data = response.json()
        except ValueError:
            return fallback

        if isinstance(data, dict):
            for key in ("message", "errorMessage", "Message"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return fallback

