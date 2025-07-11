from app.crud.base import CRUDBase
from app.models.placeholder_mapping import PlaceholderMapping
from app.schemas.placeholder_mapping import PlaceholderMappingCreate, PlaceholderMappingUpdate

class CRUDPlaceholderMapping(CRUDBase[PlaceholderMapping, PlaceholderMappingCreate, PlaceholderMappingUpdate]):
    pass

placeholder_mapping = CRUDPlaceholderMapping(PlaceholderMapping) 