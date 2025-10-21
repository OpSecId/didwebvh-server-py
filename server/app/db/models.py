"""SQLAlchemy database models."""

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func

from .base import Base


# Type aliases for cleaner code (defined after classes below)
# These are forward references, actual assignments are at the end of this file


class LogFileRecord(Base):
    """DID log entries table."""

    __tablename__ = "log_files"

    # Primary key
    scid = Column(String(255), primary_key=True, index=True)
    
    # DID information
    did = Column(String(500), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    namespace = Column(String(255), nullable=False, index=True)
    identifier = Column(String(255), nullable=False, index=True)
    
    # Status
    deactivated = Column(Boolean, default=False, index=True)
    
    # Data
    logs = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite indexes
    __table_args__ = (
        Index('idx_namespace_identifier', 'namespace', 'identifier'),
    )


class WitnessFileRecord(Base):
    """Witness files table."""

    __tablename__ = "witness_files"

    # Primary key (scid of the DID)
    scid = Column(String(255), primary_key=True, index=True)
    
    # Data
    witness_proofs = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WhoisVpRecord(Base):
    """WHOIS presentations table."""

    __tablename__ = "whois_presentations"

    # Primary key (scid of the DID)
    scid = Column(String(255), primary_key=True, index=True)
    
    # Data
    presentation = Column(JSON, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AttestedResourceRecord(Base):
    """Attested resources table."""

    __tablename__ = "attested_resources"

    # Primary key
    resource_id = Column(String(255), primary_key=True, index=True)
    
    # DID information
    scid = Column(String(255), nullable=False, index=True)
    did = Column(String(500), nullable=False, index=True)
    
    # Resource information
    resource_type = Column(String(100), nullable=False, index=True)
    resource_name = Column(String(255), nullable=False)
    
    # Resource data
    content = Column(JSON, nullable=False)
    resource_metadata = Column('metadata', JSON, nullable=False)
    proof = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite indexes
    __table_args__ = (
        Index('idx_scid_resource_type', 'scid', 'resource_type'),
        Index('idx_did_resource_type', 'did', 'resource_type'),
    )


class AdminBackgroundTask(Base):
    """Background tasks table."""

    __tablename__ = "admin_background_tasks"

    # Primary key
    task_id = Column(String(36), primary_key=True, index=True)
    
    # Task information
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    
    # Task data
    progress = Column(JSON, default={})
    message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite index
    __table_args__ = (
        Index('idx_task_type_status', 'task_type', 'status'),
    )


class ServerPolicy(Base):
    """Server policies table."""

    __tablename__ = "server_policies"

    # Primary key
    policy_id = Column(String(50), primary_key=True)
    
    # Policy data
    version = Column(String(20))
    witness = Column(Boolean, default=False)
    watcher = Column(String(500))
    portability = Column(Boolean, default=False)
    prerotation = Column(Boolean, default=False)
    endorsement = Column(Boolean, default=False)
    witness_registry_url = Column(String(500))
    
    # Full policy as JSON (for extensibility)
    policy_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class KnownWitnessRegistry(Base):
    """Registries table (e.g., known witnesses)."""

    __tablename__ = "known_witness_registries"

    # Primary key
    registry_id = Column(String(50), primary_key=True)
    
    # Registry data
    registry_type = Column(String(50), nullable=False, index=True)
    registry_data = Column(JSON, nullable=False)
    
    # Metadata
    meta = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# For test data (used by load testing)
class TestLogEntry(Base):
    """Test log entries table (for load testing)."""

    __tablename__ = "test_log_entries"

    # Primary key
    scid = Column(String(255), primary_key=True, index=True)
    
    # Test data
    logs = Column(JSON, nullable=False)
    tags = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TestResource(Base):
    """Test resources table (for load testing)."""

    __tablename__ = "test_resources"

    # Primary key
    resource_id = Column(String(255), primary_key=True, index=True)
    
    # Test data
    resource_data = Column(JSON, nullable=False)
    tags = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Type aliases for backward compatibility and cleaner code
LogEntry = LogFileRecord
Resource = AttestedResourceRecord
WitnessFile = WitnessFileRecord
WhoisPresentation = WhoisVpRecord
Task = AdminBackgroundTask
Policy = ServerPolicy
Registry = KnownWitnessRegistry

