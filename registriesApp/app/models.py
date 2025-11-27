from sqlalchemy import Column, Integer, String, JSON, DateTime, func, Index
from .database import Base

class RegistryEntry(Base):
    __tablename__ = "registry_entries"

    id = Column(Integer, primary_key=True, index=True)
    
    # Source: COMMODITY_PRODUCER, QUALIFIED_SUPPLIER, ACCREDITED_SOFTWARE, UNTRUSTWORTHY
    source_registry = Column(String, index=True)
    
    # Normalized fields for person search
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    
    # Company/Software name for records that aren't strictly persons or lack separate fields
    general_name = Column(String, nullable=True)
    
    # Unique identifier from the source (bin, iin, or id)
    external_id = Column(String, nullable=True)
    
    # Unified description of goods, software functions, or qualification categories
    specialty_description = Column(String, nullable=True)
    
    # Store the complete original JSON response for reference
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Create an index to speed up the full name search
    # We index the concatenation for performance in large datasets
    __table_args__ = (
        Index('idx_fullname', last_name, first_name, middle_name),
    )