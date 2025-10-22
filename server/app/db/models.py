"""SQLAlchemy database models."""

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Index, ForeignKey
from sqlalchemy.sql import func

from .base import Base


# Type aliases for cleaner code (defined after classes below)
# These are forward references, actual assignments are at the end of this file


class DidControllerRecord(Base):
    """DID controller with all associated data."""
    
    __tablename__ = "did_controllers"
    
    # Primary key
    scid = Column(String(255), primary_key=True, index=True)
    
    # DID information
    did = Column(String(500), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    namespace = Column(String(255), nullable=False, index=True)
    alias = Column(String(255), nullable=False, index=True)
    
    # Status
    deactivated = Column(Boolean, default=False, index=True, nullable=False)
    

    # Log file (list of log entries)
    logs = Column(JSON, nullable=False)
    
    # Witness file
    witness_file = Column(JSON, nullable=True)
    
    # WHOIS presentation
    whois_presentation = Column(JSON, nullable=True)
    
    # WebVH state and parameters
    parameters = Column(JSON, nullable=False)   
    document_state = Column(JSON, nullable=False)
    
    # Metadata
    created = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_controller_namespace_alias', 'namespace', 'alias'),
        Index('idx_controller_namespace_deactivated', 'namespace', 'deactivated'),
        Index('idx_controller_domain_deactivated', 'domain', 'deactivated'),
        Index('idx_controller_alias_deactivated', 'alias', 'deactivated'),
    )


class AttestedResourceRecord(Base):
    """Attested resources table."""

    __tablename__ = "attested_resources"

    # Primary key
    resource_id = Column(String(255), primary_key=True, index=True)
    
    # Relationships
    
    scid = Column(String(255), ForeignKey('did_controllers.scid'), primary_key=False)
    
    # Resource information
    resource_type = Column(String(100), nullable=False, index=True)
    resource_name = Column(String(255), nullable=False)
    
    # DID reference (denormalized for queries)
    did = Column(String(500), nullable=False, index=True)
    
    # Resource data
    attested_resource = Column(JSON, nullable=False)
    
    # MediaType
    media_type = Column(String(255), nullable=False, default='application/jsonld')
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_attested_scid_resource_type', 'scid', 'resource_type'),
        Index('idx_attested_did_resource_type', 'did', 'resource_type'),
    )


class VerifiableCredentialRecord(Base):
    """Verifiable credentials table."""

    __tablename__ = "verifiable_credentials"

    # Primary key (credential ID)
    credential_id = Column(String(500), primary_key=True, index=True)
    
    # Relationships - FK to DID controller (issuer)
    scid = Column(String(255), ForeignKey('did_controllers.scid'), nullable=False, index=True)
    
    # DID reference (denormalized for queries)
    issuer_did = Column(String(500), nullable=False, index=True)
    
    # Credential information
    credential_type = Column(JSON, nullable=False)  # List of types
    subject_id = Column(String(500), nullable=True, index=True)  # credentialSubject.id if present
    
    # Credential data (full VC)
    verifiable_credential = Column(JSON, nullable=False)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    revoked = Column(Boolean, default=False, index=True, nullable=False)
    
    # Metadata
    created = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_credential_scid_revoked', 'scid', 'revoked'),
        Index('idx_credential_issuer_revoked', 'issuer_did', 'revoked'),
        Index('idx_credential_subject_revoked', 'subject_id', 'revoked'),
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


# Type aliases removed - use full model names directly

