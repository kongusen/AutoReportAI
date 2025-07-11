from sqlalchemy import Column, Integer, String, JSON
from app.db.base import Base

class Template(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    description = Column(String, nullable=True)
    file_path = Column(String, unique=True)
    parsed_structure = Column(JSON) 