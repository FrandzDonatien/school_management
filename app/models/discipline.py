from dataclasses import dataclass
from typing import Optional

from app.models import row_to


@dataclass
class Discipline:
    student_id: Optional[int] = None
    periode: str = ""
    absences: str = ""
    sanctions: str = ""
    merites: str = ""
    exclusions: str = ""

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
