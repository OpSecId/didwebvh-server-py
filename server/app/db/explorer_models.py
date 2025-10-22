"""
SQLAlchemy models for explorer data (previously stored in Askar).

These models store the explorer-specific data that was stored in Askar categories
like didRecords, resourceRecords, etc.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, JSON, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from config import settings

from app.db import Base

# Determine if we're using PostgreSQL
USE_JSONB = settings.DATABASE_URL.startswith("postgresql")


class ExplorerDIDRecord(Base):
    """Explorer DID record (previously stored in Askar 'didRecord' category)."""
    
    __tablename__ = "explorer_did_records"
    
    # Primary key - the DID SCID or identifier
    id = Column(String(255), primary_key=True)
    
    # The full DID record data (JSON blob)
    data = Column(JSONB if USE_JSONB else JSON, nullable=False)
    
    # Tags for searching/filtering (extracted from Askar tags)
    scid = Column(String(255), index=True)
    domain = Column(String(255), index=True)
    namespace = Column(String(255), index=True)
    identifier = Column(String(255), index=True)
    did = Column(String(512), index=True)
    deactivated = Column(String(10), index=True)  # "True" or "False" as string
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Common filters
        Index('idx_explorer_did_namespace_deactivated', 'namespace', 'deactivated'),
        Index('idx_explorer_did_domain_deactivated', 'domain', 'deactivated'),
        Index('idx_explorer_did_namespace_identifier', 'namespace', 'identifier'),
        Index('idx_explorer_did_scid_deactivated', 'scid', 'deactivated'),
        # Single column indexes
        Index('idx_explorer_did_scid', 'scid'),
        Index('idx_explorer_did_domain', 'domain'),
        Index('idx_explorer_did_namespace', 'namespace'),
        Index('idx_explorer_did_identifier', 'identifier'),
        Index('idx_explorer_did_status', 'deactivated'),
    )


class ExplorerResourceRecord(Base):
    """Explorer resource record (previously stored in Askar 'resourceRecord' category)."""
    
    __tablename__ = "explorer_resource_records"
    
    # Primary key - resource identifier
    id = Column(String(255), primary_key=True)
    
    # The full resource record data (JSON blob)
    data = Column(JSONB if USE_JSONB else JSON, nullable=False)
    
    # Tags for searching/filtering
    scid = Column(String(255), index=True)
    resource_id = Column(String(255), index=True)
    resource_type = Column(String(255), index=True)
    did = Column(String(512), index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Common filters
        Index('idx_explorer_resource_scid_type', 'scid', 'resource_type'),
        Index('idx_explorer_resource_did_type', 'did', 'resource_type'),
        # Single column indexes
        Index('idx_explorer_resource_scid', 'scid'),
        Index('idx_explorer_resource_type', 'resource_type'),
        Index('idx_explorer_resource_id', 'resource_id'),
        Index('idx_explorer_resource_did', 'did'),
    )


class AskarGenericRecord(Base):
    """Generic storage for other Askar categories not yet mapped to specific models."""
    
    __tablename__ = "askar_generic_records"
    
    # Composite primary key: category + key
    category = Column(String(255), primary_key=True)
    key = Column(String(512), primary_key=True)
    
    # Data and tags
    data = Column(JSONB if USE_JSONB else JSON, nullable=False)
    tags = Column(JSONB if USE_JSONB else JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_generic_category', 'category'),
    )

