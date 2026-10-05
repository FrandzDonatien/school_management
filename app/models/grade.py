from dataclasses import dataclass
from typing import Optional

from app.models import row_to


@dataclass
class Grade:
    id: Optional[int] = None
    student_id: Optional[int] = None
    subject_id: Optional[int] = None
    periode: str = ""
    interro: Optional[float] = None
    devoir: Optional[float] = None
    compo: Optional[float] = None

    @classmethod
    def from_row(cls, row):
        return row_to(cls, row)
