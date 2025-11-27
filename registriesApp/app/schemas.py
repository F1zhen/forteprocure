from pydantic import BaseModel
from typing import Optional, Dict, Any

class RegistryEntryResponse(BaseModel):
    id: int
    source_registry: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    general_name: Optional[str] = None
    raw_data: Dict[str, Any]

    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    query: str
    match_count: int
    results: list[RegistryEntryResponse]

class SyncStatus(BaseModel):
    message: str
    status: str