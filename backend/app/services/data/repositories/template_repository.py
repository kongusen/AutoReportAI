from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from .base_repository import BaseRepository
from app.models.template import Template


class TemplateRepository(BaseRepository[Template]):
    def __init__(self, session: Session):
        super().__init__(session, Template)

    def find_by_name(self, name: str) -> List[Template]:
        return self.session.query(Template).filter(Template.name == name).all()


