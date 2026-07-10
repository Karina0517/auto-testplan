"""Entity and report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class UserStory:
    """Represents an Azure DevOps user story."""

    id: int
    title: str

    @property
    def suite_name(self) -> str:
        """Return suite name in required format."""
        return f"{self.id} : {self.title.strip()}"


@dataclass(slots=True)
class ReportRecord:
    """Represents one CSV report row."""

    id: int
    titulo: str
    suite_creada: str
    resultado: str
    fecha: str
    mensaje: str

    @classmethod
    def from_outcome(
        cls,
        work_item_id: int,
        title: str,
        suite_created: bool,
        result: str,
        message: str,
    ) -> "ReportRecord":
        """Create a report record from processing outcome."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return cls(
            id=work_item_id,
            titulo=title,
            suite_creada="Sí" if suite_created else "No",
            resultado=result,
            fecha=timestamp,
            mensaje=message,
        )

    def to_dict(self) -> dict[str, str | int]:
        """Serialize record for pandas dataframe."""
        return asdict(self)

