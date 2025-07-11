import enum
from sqlalchemy import Column, Integer, String, Enum, JSON
from app.db.base import Base

class DataSourceType(str, enum.Enum):
    sql = "sql"
    csv = "csv"
    api = "api"

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True, nullable=False)
    source_type = Column(Enum(DataSourceType), nullable=False)
    
    # For 'sql' type
    db_query = Column(String, nullable=True)

    # For 'csv' type
    file_path = Column(String, nullable=True)

    # For 'api' type
    api_url = Column(String, nullable=True)
    api_method = Column(String, default="GET", nullable=True)
    api_headers = Column(JSON, nullable=True)
    api_body = Column(JSON, nullable=True) 