from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base

class Task(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    schedule = Column(String)
    enabled = Column(Boolean, default=True) 