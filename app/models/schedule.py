from dataclasses import dataclass
from typing import Optional

from app.models import row_to


@dataclass
class ScheduleEntry:
    """Un cours placé dans l'emploi du temps."""
    id: Optional[int] = None
    annee_id: Optional[int] = None
    teacher_id: Optional[int] = None
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    day: int = 0
    slot: int = 0

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)


@dataclass
class Assignment:
    """Affectation : un enseignant fait N heures d'une matière dans une classe."""
    id: Optional[int] = None
    annee_id: Optional[int] = None
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None
    hours: int = 0

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
