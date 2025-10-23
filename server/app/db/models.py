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
    
    def __init__(self, logs: list, witness_file: list = None, whois_presentation: dict = None, **kwargs):
        """
        Initialize DidControllerRecord from logs and associated data.
        All DID fields are derived from the document state in the logs.
        
        Args:
            logs: List of log entries
            witness_file: Optional witness file data
            whois_presentation: Optional whois presentation data
            **kwargs: Additional fields to override
        """
        from app.plugins import DidWebVH
        
        # Get document state from logs
        webvh = DidWebVH()
        state = webvh.get_document_state(logs)
        
        # Extract domain, namespace, alias from document_id
        # document_id format: did:webvh:{scid}:domain:namespace:alias
        did_parts = state.document_id.split(":")
        domain = did_parts[3] if len(did_parts) > 3 else ""
        namespace = did_parts[4] if len(did_parts) > 4 else ""
        alias = did_parts[5] if len(did_parts) > 5 else ""
        
        # Extract parameters from state
        params = state.params if hasattr(state, 'params') else (state.parameters if hasattr(state, 'parameters') else {})
        
        # Get document state - use state.document which is the actual DID document
        import logging
        logger = logging.getLogger(__name__)
        
        # Try to get the document from state
        if hasattr(state, 'document') and state.document:
            doc_state = state.document if isinstance(state.document, dict) else (state.document.model_dump() if hasattr(state.document, 'model_dump') else {})
        elif hasattr(state, 'portable') and state.portable:
            doc_state = state.portable if isinstance(state.portable, dict) else {}
        else:
            doc_state = {}
            logger.warning(f"Could not extract document_state for DID {state.document_id}")
        
        logger.info(f"Creating DID controller with document_state keys: {list(doc_state.keys()) if isinstance(doc_state, dict) else 'NOT A DICT'}")
        
        # Build the init data, only setting values not already in kwargs
        init_data = {
            "scid": state.scid,
            "did": state.document_id,
            "domain": domain,
            "namespace": namespace,
            "alias": alias,
            "deactivated": state.deactivated,
            "logs": logs,
            "witness_file": witness_file or [],
            "whois_presentation": whois_presentation or {},
            "parameters": params,
            "document_state": doc_state,
        }
        
        # Merge with kwargs, giving precedence to kwargs
        init_data.update(kwargs)
        
        # Call parent init
        super().__init__(**init_data)


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
    
    def __init__(self, attested_resource: dict, **kwargs):
        """
        Initialize AttestedResourceRecord from an attested_resource dict.
        All fields are derived from the attested_resource.
        """
        # Extract resource_id
        resource_id = attested_resource.get("id")
        if not resource_id:
            raise ValueError("attested_resource must have an 'id' field")
        
        # Extract scid from resource_id (last part after /)
        scid = resource_id.split("/")[-1] if "/" in resource_id else None
        
        # Extract metadata
        resource_metadata = attested_resource.get("resourceMetadata", {})
        resource_type = resource_metadata.get("type", "Unknown")
        resource_name = resource_metadata.get("name", "")
        
        # Extract DID from controller or issuer
        did = attested_resource.get("controller") or attested_resource.get("issuer")
        if isinstance(did, dict):
            did = did.get("id")
        
        # Extract media type
        media_type = attested_resource.get("mediaType") or kwargs.get("media_type", "application/jsonld")
        
        # Call parent init with all fields
        super().__init__(
            resource_id=resource_id,
            scid=scid,
            resource_type=resource_type,
            resource_name=resource_name,
            did=did,
            attested_resource=attested_resource,
            media_type=media_type,
            **kwargs
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
    
    # Verification (stored at creation time)
    verified = Column(Boolean, default=False, nullable=False)
    verification_method = Column(String(500), nullable=True)  # VM used for verification
    verification_error = Column(Text, nullable=True)  # Error message if verification failed
    
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

