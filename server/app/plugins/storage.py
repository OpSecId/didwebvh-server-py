"""SQLAlchemy Storage Manager."""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from config import settings
from app.db.base import Base
from app.db.models import (
    DidControllerRecord,
    AttestedResourceRecord,
    VerifiableCredentialRecord,
    AdminBackgroundTask,
    ServerPolicy,
    KnownWitnessRegistry,
    TestLogEntry,
    TestResource,
)
from app.db.explorer_models import (
    ExplorerDIDRecord,
    ExplorerResourceRecord,
    AskarGenericRecord,
)

logger = logging.getLogger(__name__)


class StorageManager:
    """
    SQLAlchemy-based storage manager for the DID WebVH server.
    
    Manages the database engine, sessions, and provides CRUD operations
    for all database entities including log entries, resources, tasks,
    policies, and registries.
    
    This class owns the database connection and session factory.
    """
    
    _instance = None
    _engine = None
    _SessionLocal = None
    
    def __new__(cls):
        """Singleton pattern to ensure single engine instance."""
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the storage manager."""
        # Only initialize once
        if self._engine is not None:
            return
            
        self.db_url = settings.DATABASE_URL
        self.db_type = 'sqlite' if 'sqlite' in self.db_url else 'postgres'

        # Create engine with appropriate settings
        if self.db_type == 'sqlite':
            # SQLite specific configuration
            self._engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        elif self.db_type == 'postgres':
            # PostgreSQL configuration
            self._engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=False
            )
        else:
            raise ValueError(f"Invalid database type: {self.db_type}")
        
        # Create session factory
        self._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        
        logger.info(f"StorageManager initialized with {self.db_type} database at {self.db_url}")
    
    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        return self._engine
    
    @property
    def SessionLocal(self):
        """Get the session factory."""
        return self._SessionLocal

    async def provision(self, recreate: bool = False):
        """
        Provision the database schema.
        
        Similar to AskarStorage.provision(), this creates all database tables.
        
        Args:
            recreate: If True, drop all tables before creating them (useful for tests)
        """
        logger.warning("DB provisioning started.")
        try:
            if recreate:
                logger.warning("Dropping all existing tables...")
                Base.metadata.drop_all(bind=self._engine)
                logger.warning("All tables dropped.")
            
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=self._engine)
            logger.warning("DB provisioning finished.")
        except Exception as e:
            logger.error(f"DB provisioning failed: {str(e)}")
            raise Exception(f"DB provisioning failed: {str(e)}")

    def init_db(self):
        """
        Initialize the database schema (sync version of provision).
        
        This is a synchronous wrapper around provision for convenience.
        Use provision() for async contexts.
        """
        import asyncio
        asyncio.run(self.provision())

    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            Session: SQLAlchemy database session
        """
        return self._SessionLocal()
    
    def get_db(self):
        """
        Dependency injection helper for FastAPI endpoints.
        
        Yields:
            Session: SQLAlchemy database session
            
        Example:
            @router.get("/items")
            async def get_items(db: Session = Depends(StorageManager().get_db)):
                items = db.query(Item).all()
                return items
        """
        db = self.get_session()
        try:
            yield db
        finally:
            db.close()

    # ========== Log Entry Operations ==========

    # ========== DID Controller Operations ==========

    def create_did_controller(self, logs: List[Dict],
                             witness_file: Optional[List[Dict]] = None, 
                             whois_presentation: Optional[Dict] = None) -> DidControllerRecord:
        """Create a new DID controller record - extracts all data from logs.
        
        Args:
            logs: Log entries (required - contains all DID info)
            witness_file: Optional witness file
            whois_presentation: Optional WHOIS presentation
            
        Returns:
            DidControllerRecord: The created record
        """
        from app.plugins import DidWebVH
        
        with self.get_session() as session:
            # Extract DID information from logs
            webvh = DidWebVH()
            state = webvh.get_document_state(logs)
            
            # Parse DID components
            did = state.document_id
            _, _, scid, domain, namespace, alias = did.split(":")
            
            # Extract deactivated status from parameters
            params = state.params if hasattr(state, 'params') else state.parameters
            deactivated = params.get("deactivated", False) if params else False
            
            # Create controller
            controller = DidControllerRecord(
                scid=scid,
                did=did,
                domain=domain,
                namespace=namespace,
                alias=alias,
                deactivated=deactivated,
                logs=logs,
                witness_file=witness_file,
                whois_presentation=whois_presentation,
                parameters=params,
                document_state=state.document if isinstance(state.document, dict) else state.document.model_dump() if hasattr(state.document, 'model_dump') else dict(state.document)
            )
            session.add(controller)
            session.commit()
            session.refresh(controller)
            return controller

    def update_did_controller(self, scid: str, logs: Optional[List[Dict]] = None,
                             witness_file: Optional[List[Dict]] = None,
                             whois_presentation: Optional[Dict] = None) -> Optional[DidControllerRecord]:
        """Update an existing DID controller record - re-extracts data from logs if provided.
        
        Args:
            scid: The SCID of the controller to update
            logs: Optional new log entries (if provided, re-extracts state/parameters/deactivated)
            witness_file: Optional witness file
            whois_presentation: Optional WHOIS presentation
            
        Returns:
            Optional[DidControllerRecord]: The updated record or None if not found
        """
        from app.plugins import DidWebVH
        
        with self.get_session() as session:
            controller = session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            if controller:
                # Update logs and re-extract derived data
                if logs is not None:
                    controller.logs = logs
                    
                    # Re-extract state and parameters from updated logs
                    webvh = DidWebVH()
                    state = webvh.get_document_state(logs)
                    params = state.params if hasattr(state, 'params') else state.parameters
                    
                    controller.parameters = params
                    controller.document_state = state.document if isinstance(state.document, dict) else state.document.model_dump() if hasattr(state.document, 'model_dump') else dict(state.document)
                    controller.deactivated = params.get("deactivated", False) if params else False
                
                # Update optional fields
                if witness_file is not None:
                    controller.witness_file = witness_file
                if whois_presentation is not None:
                    controller.whois_presentation = whois_presentation
                    
                session.commit()
                session.refresh(controller)
            return controller
    def get_did_controllers(self, filters: Optional[Dict[str, Any]] = None, 
                           limit: Optional[int] = None, offset: int = 0) -> List[DidControllerRecord]:
        """Get DID controllers with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(DidControllerRecord)
            
            if filters:
                if 'scid' in filters:
                    query = query.filter(DidControllerRecord.scid == filters['scid'])
                if 'did' in filters:
                    query = query.filter(DidControllerRecord.did == filters['did'])
                if 'domain' in filters:
                    query = query.filter(DidControllerRecord.domain == filters['domain'])
                if 'namespace' in filters:
                    query = query.filter(DidControllerRecord.namespace == filters['namespace'])
                if 'alias' in filters:
                    query = query.filter(DidControllerRecord.alias == filters['alias'])
                if 'deactivated' in filters:
                    query = query.filter(DidControllerRecord.deactivated == filters['deactivated'])
            
            if limit is not None:
                query = query.offset(offset).limit(limit)
            
            return query.all()

    def count_did_controllers(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count DID controllers with optional filters."""
        with self.get_session() as session:
            query = session.query(DidControllerRecord)
            
            if filters:
                if 'scid' in filters:
                    query = query.filter(DidControllerRecord.scid == filters['scid'])
                if 'did' in filters:
                    query = query.filter(DidControllerRecord.did == filters['did'])
                if 'domain' in filters:
                    query = query.filter(DidControllerRecord.domain == filters['domain'])
                if 'namespace' in filters:
                    query = query.filter(DidControllerRecord.namespace == filters['namespace'])
                if 'alias' in filters:
                    query = query.filter(DidControllerRecord.alias == filters['alias'])
                if 'deactivated' in filters:
                    query = query.filter(DidControllerRecord.deactivated == filters['deactivated'])
            
            return query.count()



    def create_log_entry(self, scid: str, did: str, domain: str, namespace: str, 
                        identifier: str, logs: List[Dict], deactivated: bool = False) -> DidControllerRecord:
        """Create a new log entry."""
        with self.get_session() as session:
            log_entry = DidControllerRecord(
                scid=scid,
                did=did,
                domain=domain,
                namespace=namespace,
                identifier=identifier,
                logs=logs,
                deactivated=deactivated
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            return log_entry

    def get_log_entry(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a log entry by SCID."""
        with self.get_session() as session:
            return session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()

    def get_log_entries(self, filters: Optional[Dict[str, Any]] = None) -> List[DidControllerRecord]:
        """Get log entries with optional filters."""
        with self.get_session() as session:
            query = session.query(DidControllerRecord)
            
            if filters:
                if 'did' in filters:
                    query = query.filter(DidControllerRecord.did == filters['did'])
                if 'domain' in filters:
                    query = query.filter(DidControllerRecord.domain == filters['domain'])
                if 'namespace' in filters:
                    query = query.filter(DidControllerRecord.namespace == filters['namespace'])
                if 'identifier' in filters:
                    query = query.filter(DidControllerRecord.identifier == filters['identifier'])
                if 'deactivated' in filters:
                    query = query.filter(DidControllerRecord.deactivated == filters['deactivated'])
            
            return query.all()

    def update_log_entry(self, scid: str, logs: List[Dict], 
                        deactivated: Optional[bool] = None) -> Optional[DidControllerRecord]:
        """Update an existing log entry."""
        with self.get_session() as session:
            log_entry = session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            if log_entry:
                log_entry.logs = logs
                if deactivated is not None:
                    log_entry.deactivated = deactivated
                session.commit()
                session.refresh(log_entry)
            return log_entry

    def delete_log_entry(self, scid: str) -> bool:
        """Delete a log entry."""
        with self.get_session() as session:
            log_entry = session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            if log_entry:
                session.delete(log_entry)
                session.commit()
                return True
            return False

    # ========== AttestedResourceRecord Operations ==========

    def create_resource(self, scid: str, attested_resource: Dict) -> AttestedResourceRecord:
        """Create a new resource - extracts metadata from attested_resource.
        
        Args:
            scid: The SCID from the parent DidControllerRecord (FK relationship)
            attested_resource: The full attested resource object
            
        Returns:
            AttestedResourceRecord: The created record
        """
        with self.get_session() as session:
            # Extract metadata
            metadata = attested_resource.get("metadata", {})
            resource_id = metadata.get("resourceId")
            resource_type = metadata.get("resourceType", "")
            resource_name = metadata.get("resourceName", "")
            
            # Extract DID from proof
            proof = attested_resource.get("proof", {})
            verification_method = proof.get("verificationMethod", "")
            did = verification_method.split("#")[0]
            
            resource = AttestedResourceRecord(
                resource_id=resource_id,
                scid=scid,
                did=did,
                resource_type=resource_type,
                resource_name=resource_name,
                attested_resource=attested_resource
            )
            session.add(resource)
            session.commit()
            session.refresh(resource)
            return resource


    def get_resource(self, resource_id: str) -> Optional[AttestedResourceRecord]:
        """Get a resource by ID."""
        with self.get_session() as session:
            return session.query(AttestedResourceRecord).filter(AttestedResourceRecord.resource_id == resource_id).first()

    def get_resources(self, filters: Optional[Dict[str, Any]] = None,
                     limit: Optional[int] = None, offset: int = 0) -> List[AttestedResourceRecord]:
        """Get resources with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(AttestedResourceRecord)
            
            if filters:
                if 'scid' in filters:
                    query = query.filter(AttestedResourceRecord.scid == filters['scid'])
                if 'did' in filters:
                    query = query.filter(AttestedResourceRecord.did == filters['did'])
                if 'resource_type' in filters:
                    query = query.filter(AttestedResourceRecord.resource_type == filters['resource_type'])
                if 'resource_id' in filters:
                    query = query.filter(AttestedResourceRecord.resource_id == filters['resource_id'])
            
            if limit is not None:
                query = query.offset(offset).limit(limit)
            
            return query.all()

    def count_resources(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count resources with optional filters."""
        with self.get_session() as session:
            query = session.query(AttestedResourceRecord)
            
            if filters:
                if 'scid' in filters:
                    query = query.filter(AttestedResourceRecord.scid == filters['scid'])
                if 'did' in filters:
                    query = query.filter(AttestedResourceRecord.did == filters['did'])
                if 'resource_type' in filters:
                    query = query.filter(AttestedResourceRecord.resource_type == filters['resource_type'])
                if 'resource_id' in filters:
                    query = query.filter(AttestedResourceRecord.resource_id == filters['resource_id'])
            
            return query.count()

    def update_resource(self, attested_resource: Dict) -> Optional[AttestedResourceRecord]:
        """Update an existing resource - extracts resource_id from attested_resource.
        
        Args:
            attested_resource: The full attested resource object
            
        Returns:
            Optional[AttestedResourceRecord]: The updated record or None if not found
        """
        with self.get_session() as session:
            # Extract resource_id from metadata
            resource_id = attested_resource.get("metadata", {}).get("resourceId")
            
            resource = session.query(AttestedResourceRecord).filter(AttestedResourceRecord.resource_id == resource_id).first()
            if resource:
                resource.attested_resource = attested_resource
                session.commit()
                session.refresh(resource)
            return resource


    def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource."""
        with self.get_session() as session:
            resource = session.query(AttestedResourceRecord).filter(AttestedResourceRecord.resource_id == resource_id).first()
            if resource:
                session.delete(resource)
                session.commit()
                return True
            return False

    # ========== Credential Operations ==========

    def create_credential(self, scid: str, verifiable_credential: Dict) -> VerifiableCredentialRecord:
        """Create a new verifiable credential - extracts metadata from verifiable_credential.
        
        Args:
            scid: The SCID from the parent DidControllerRecord (FK relationship)
            verifiable_credential: The full verifiable credential object
            
        Returns:
            VerifiableCredentialRecord: The created record
        """
        from dateutil import parser as date_parser
        
        with self.get_session() as session:
            # Extract credential ID
            credential_id = verifiable_credential.get("id")
            if not credential_id:
                raise ValueError("Credential must have an 'id' field")
            
            # Extract issuer DID
            issuer = verifiable_credential.get("issuer")
            if isinstance(issuer, dict):
                issuer_did = issuer.get("id")
            else:
                issuer_did = issuer
            
            # Extract credential type
            credential_type = verifiable_credential.get("type", [])
            if isinstance(credential_type, str):
                credential_type = [credential_type]
            
            # Extract subject ID if present
            subject = verifiable_credential.get("credentialSubject", {})
            if isinstance(subject, list):
                subject_id = subject[0].get("id") if subject and len(subject) > 0 else None
            elif isinstance(subject, dict):
                subject_id = subject.get("id")
            else:
                subject_id = None
            
            # Parse validity dates if present
            valid_from = None
            valid_until = None
            if verifiable_credential.get("validFrom"):
                try:
                    valid_from = date_parser.parse(verifiable_credential["validFrom"])
                except Exception:
                    pass
            if verifiable_credential.get("validUntil"):
                try:
                    valid_until = date_parser.parse(verifiable_credential["validUntil"])
                except Exception:
                    pass
            
            credential = VerifiableCredentialRecord(
                credential_id=credential_id,
                scid=scid,
                issuer_did=issuer_did,
                credential_type=credential_type,
                subject_id=subject_id,
                verifiable_credential=verifiable_credential,
                valid_from=valid_from,
                valid_until=valid_until,
                revoked=False
            )
            session.add(credential)
            session.commit()
            session.refresh(credential)
            return credential

    def get_credential(self, credential_id: str) -> Optional[VerifiableCredentialRecord]:
        """Get a credential by ID."""
        with self.get_session() as session:
            return session.query(VerifiableCredentialRecord).filter(
                VerifiableCredentialRecord.credential_id == credential_id
            ).first()

    def get_credentials(self, filters: Optional[Dict[str, Any]] = None, 
                       limit: Optional[int] = None, offset: int = 0) -> List[VerifiableCredentialRecord]:
        """Get credentials with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(VerifiableCredentialRecord)
            
            # Join with DidControllerRecord if filtering by namespace or alias
            needs_join = filters and ('namespace' in filters or 'alias' in filters)
            if needs_join:
                query = query.join(
                    DidControllerRecord,
                    VerifiableCredentialRecord.scid == DidControllerRecord.scid
                )
            
            if filters:
                if 'scid' in filters:
                    query = query.filter(VerifiableCredentialRecord.scid == filters['scid'])
                if 'issuer_did' in filters:
                    query = query.filter(VerifiableCredentialRecord.issuer_did == filters['issuer_did'])
                if 'subject_id' in filters:
                    query = query.filter(VerifiableCredentialRecord.subject_id == filters['subject_id'])
                if 'revoked' in filters:
                    query = query.filter(VerifiableCredentialRecord.revoked == filters['revoked'])
                if 'namespace' in filters:
                    query = query.filter(DidControllerRecord.namespace == filters['namespace'])
                if 'alias' in filters:
                    query = query.filter(DidControllerRecord.alias == filters['alias'])
            
            if limit is not None:
                query = query.offset(offset).limit(limit)
            
            return query.all()

    def count_credentials(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count credentials with optional filters."""
        with self.get_session() as session:
            query = session.query(VerifiableCredentialRecord)
            
            # Join with DidControllerRecord if filtering by namespace or alias
            needs_join = filters and ('namespace' in filters or 'alias' in filters)
            if needs_join:
                query = query.join(
                    DidControllerRecord,
                    VerifiableCredentialRecord.scid == DidControllerRecord.scid
                )
            
            if filters:
                if 'scid' in filters:
                    query = query.filter(VerifiableCredentialRecord.scid == filters['scid'])
                if 'issuer_did' in filters:
                    query = query.filter(VerifiableCredentialRecord.issuer_did == filters['issuer_did'])
                if 'subject_id' in filters:
                    query = query.filter(VerifiableCredentialRecord.subject_id == filters['subject_id'])
                if 'revoked' in filters:
                    query = query.filter(VerifiableCredentialRecord.revoked == filters['revoked'])
                if 'namespace' in filters:
                    query = query.filter(DidControllerRecord.namespace == filters['namespace'])
                if 'alias' in filters:
                    query = query.filter(DidControllerRecord.alias == filters['alias'])
            
            return query.count()

    def update_credential(self, verifiable_credential: Dict) -> Optional[VerifiableCredentialRecord]:
        """Update an existing credential - extracts credential_id from verifiable_credential.
        
        Args:
            verifiable_credential: The full verifiable credential object
            
        Returns:
            Optional[VerifiableCredentialRecord]: The updated record or None if not found
        """
        with self.get_session() as session:
            credential_id = verifiable_credential.get("id")
            if not credential_id:
                raise ValueError("Credential must have an 'id' field")
            
            credential = session.query(VerifiableCredentialRecord).filter(
                VerifiableCredentialRecord.credential_id == credential_id
            ).first()
            
            if credential:
                credential.verifiable_credential = verifiable_credential
                session.commit()
                session.refresh(credential)
            
            return credential

    def revoke_credential(self, credential_id: str) -> bool:
        """Mark a credential as revoked."""
        with self.get_session() as session:
            credential = session.query(VerifiableCredentialRecord).filter(
                VerifiableCredentialRecord.credential_id == credential_id
            ).first()
            
            if credential:
                credential.revoked = True
                session.commit()
                return True
            return False

    def delete_credential(self, credential_id: str) -> bool:
        """Delete a credential."""
        with self.get_session() as session:
            credential = session.query(VerifiableCredentialRecord).filter(
                VerifiableCredentialRecord.credential_id == credential_id
            ).first()
            
            if credential:
                session.delete(credential)
                session.commit()
                return True
            return False

    # ========== Task Operations ==========

    def create_task(self, task_id: str, task_type: str, status: str,
                   progress: Optional[Dict] = None, message: Optional[str] = None) -> AdminBackgroundTask:
        """Create a new task."""
        with self.get_session() as session:
            task = AdminBackgroundTask(
                task_id=task_id,
                task_type=task_type,
                status=status,
                progress=progress or {},
                message=message
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task

    def get_task(self, task_id: str) -> Optional[AdminBackgroundTask]:
        """Get a task by ID."""
        with self.get_session() as session:
            return session.query(AdminBackgroundTask).filter(AdminBackgroundTask.task_id == task_id).first()

    def get_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[AdminBackgroundTask]:
        """Get tasks with optional filters."""
        with self.get_session() as session:
            query = session.query(AdminBackgroundTask)
            
            if filters:
                if 'task_type' in filters:
                    query = query.filter(AdminBackgroundTask.task_type == filters['task_type'])
                if 'status' in filters:
                    query = query.filter(AdminBackgroundTask.status == filters['status'])
            
            return query.all()

    def update_task(self, task_id: str, status: Optional[str] = None,
                   progress: Optional[Dict] = None, message: Optional[str] = None) -> Optional[AdminBackgroundTask]:
        """Update an existing task."""
        with self.get_session() as session:
            task = session.query(AdminBackgroundTask).filter(AdminBackgroundTask.task_id == task_id).first()
            if task:
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if message is not None:
                    task.message = message
                session.commit()
                session.refresh(task)
            return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        with self.get_session() as session:
            task = session.query(AdminBackgroundTask).filter(AdminBackgroundTask.task_id == task_id).first()
            if task:
                session.delete(task)
                session.commit()
                return True
            return False

    # ========== Policy Operations ==========

    def create_or_update_policy(self, policy_id: str, policy_data: Dict) -> ServerPolicy:
        """Create or update a policy."""
        with self.get_session() as session:
            policy = session.query(ServerPolicy).filter(ServerPolicy.policy_id == policy_id).first()
            
            if policy:
                # Update existing
                for key, value in policy_data.items():
                    setattr(policy, key, value)
            else:
                # Create new
                policy = ServerPolicy(policy_id=policy_id, **policy_data)
                session.add(policy)
            
            session.commit()
            session.refresh(policy)
            return policy

    def get_policy(self, policy_id: str) -> Optional[ServerPolicy]:
        """Get a policy by ID."""
        with self.get_session() as session:
            return session.query(ServerPolicy).filter(ServerPolicy.policy_id == policy_id).first()

    # ========== Registry Operations ==========

    def create_or_update_registry(self, registry_id: str, registry_type: str,
                                  registry_data: Dict, meta: Optional[Dict] = None) -> KnownWitnessRegistry:
        """Create or update a registry."""
        with self.get_session() as session:
            registry = session.query(KnownWitnessRegistry).filter(KnownWitnessRegistry.registry_id == registry_id).first()
            
            if registry:
                # Update existing
                registry.registry_type = registry_type
                registry.registry_data = registry_data
                if meta is not None:
                    registry.meta = meta
            else:
                # Create new
                registry = KnownWitnessRegistry(
                    registry_id=registry_id,
                    registry_type=registry_type,
                    registry_data=registry_data,
                    meta=meta
                )
                session.add(registry)
            
            session.commit()
            session.refresh(registry)
            return registry

    def get_registry(self, registry_id: str) -> Optional[KnownWitnessRegistry]:
        """Get a registry by ID."""
        with self.get_session() as session:
            return session.query(KnownWitnessRegistry).filter(KnownWitnessRegistry.registry_id == registry_id).first()

    # ========== Witness File Operations ==========

    def create_or_update_witness_file(self, scid: str, witness_proofs: List[Dict]) -> DidControllerRecord:
        """Create or update a witness file."""
        with self.get_session() as session:
            witness_file = session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            
            if witness_file:
                witness_file.witness_proofs = witness_proofs
            else:
                witness_file = DidControllerRecord(scid=scid, witness_proofs=witness_proofs)
                session.add(witness_file)
            
            session.commit()
            session.refresh(witness_file)
            return witness_file

    def get_witness_file(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a witness file by SCID."""
        with self.get_session() as session:
            return session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()

    # ========== WHOIS Presentation Operations ==========

    def create_or_update_whois(self, scid: str, presentation: Dict) -> DidControllerRecord:
        """Create or update a WHOIS presentation."""
        with self.get_session() as session:
            whois = session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            
            if whois:
                whois.presentation = presentation
            else:
                whois = DidControllerRecord(scid=scid, presentation=presentation)
                session.add(whois)
            
            session.commit()
            session.refresh(whois)
            return whois

    def get_whois(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a WHOIS presentation by SCID."""
        with self.get_session() as session:
            return session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()

    # ========== Helper Methods (Query by Namespace and Identifier) ==========

    def get_did_controller_by_alias(self, namespace: str, identifier: str) -> Optional[DidControllerRecord]:
        """Get a log entry by namespace and identifier (alias)."""
        with self.get_session() as session:
            return session.query(DidControllerRecord).filter(
                DidControllerRecord.namespace == namespace,
                DidControllerRecord.alias == identifier
            ).first()

    def get_witness_file_by_identifier(self, namespace: str, identifier: str) -> Optional[DidControllerRecord]:
        """Get a witness file by namespace and identifier (alias)."""
        with self.get_session() as session:
            return session.query(DidControllerRecord).filter(
                DidControllerRecord.namespace == namespace,
                DidControllerRecord.alias == identifier
            ).first()

    def get_whois_by_identifier(self, namespace: str, identifier: str) -> Optional[DidControllerRecord]:
        """Get a WHOIS presentation by namespace and identifier (alias)."""
        with self.get_session() as session:
            return session.query(DidControllerRecord).filter(
                DidControllerRecord.namespace == namespace,
                DidControllerRecord.alias == identifier
            ).first()


    # ========== Test Data Operations (for load testing) ==========

    def create_test_log_entry(self, scid: str, logs: List[Dict], tags: Optional[Dict] = None) -> TestLogEntry:
        """Create a test log entry."""
        with self.get_session() as session:
            test_entry = TestLogEntry(scid=scid, logs=logs, tags=tags)
            session.add(test_entry)
            session.commit()
            session.refresh(test_entry)
            return test_entry

    def create_test_resource(self, resource_id: str, resource_data: Dict, 
                           tags: Optional[Dict] = None) -> TestResource:
        """Create a test resource."""
        with self.get_session() as session:
            test_resource = TestResource(
                resource_id=resource_id,
                resource_data=resource_data,
                tags=tags
            )
            session.add(test_resource)
            session.commit()
            session.refresh(test_resource)
            return test_resource

    def delete_test_log_entry(self, scid: str) -> bool:
        """Delete a test log entry."""
        with self.get_session() as session:
            test_entry = session.query(TestLogEntry).filter(TestLogEntry.scid == scid).first()
            if test_entry:
                session.delete(test_entry)
                session.commit()
                return True
            return False

    def delete_test_resource(self, resource_id: str) -> bool:
        """Delete a test resource."""
        with self.get_session() as session:
            test_resource = session.query(TestResource).filter(TestResource.resource_id == resource_id).first()
            if test_resource:
                session.delete(test_resource)
                session.commit()
                return True
            return False

    # ========== Explorer Record Operations (replaces Askar categories) ==========

    def create_explorer_did_record(self, record_id: str, data: Dict, tags: Optional[Dict] = None) -> ExplorerDIDRecord:
        """Create an explorer DID record."""
        with self.get_session() as session:
            record = ExplorerDIDRecord(
                id=record_id,
                data=data,
                scid=tags.get("scid") if tags else None,
                domain=tags.get("domain") if tags else None,
                namespace=tags.get("namespace") if tags else None,
                identifier=tags.get("identifier") if tags else None,
                did=tags.get("did") if tags else None,
                deactivated=tags.get("deactivated", "False") if tags else "False",
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_explorer_did_record(self, record_id: str, data: Dict, tags: Optional[Dict] = None) -> Optional[ExplorerDIDRecord]:
        """Update an explorer DID record."""
        with self.get_session() as session:
            record = session.query(ExplorerDIDRecord).filter(ExplorerDIDRecord.id == record_id).first()
            if record:
                record.data = data
                if tags:
                    record.scid = tags.get("scid")
                    record.domain = tags.get("domain")
                    record.namespace = tags.get("namespace")
                    record.identifier = tags.get("identifier")
                    record.did = tags.get("did")
                    record.deactivated = tags.get("deactivated", "False")
                session.commit()
                session.refresh(record)
                return record
            return None

    def get_explorer_did_records(self, filters: Optional[Dict] = None, limit: Optional[int] = None, offset: int = 0) -> List[ExplorerDIDRecord]:
        """Get explorer DID records with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(ExplorerDIDRecord)
            
            if filters:
                if filters.get("scid"):
                    query = query.filter(ExplorerDIDRecord.scid == filters["scid"])
                if filters.get("domain"):
                    query = query.filter(ExplorerDIDRecord.domain == filters["domain"])
                if filters.get("namespace"):
                    query = query.filter(ExplorerDIDRecord.namespace == filters["namespace"])
                if filters.get("identifier"):
                    query = query.filter(ExplorerDIDRecord.identifier == filters["identifier"])
                if filters.get("deactivated"):
                    query = query.filter(ExplorerDIDRecord.deactivated == filters["deactivated"])
            
            if limit is not None:
                query = query.offset(offset).limit(limit)
            
            return query.all()

    def count_explorer_did_records(self, filters: Optional[Dict] = None) -> int:
        """Count explorer DID records with optional filters."""
        with self.get_session() as session:
            query = session.query(ExplorerDIDRecord)
            
            if filters:
                if filters.get("scid"):
                    query = query.filter(ExplorerDIDRecord.scid == filters["scid"])
                if filters.get("domain"):
                    query = query.filter(ExplorerDIDRecord.domain == filters["domain"])
                if filters.get("namespace"):
                    query = query.filter(ExplorerDIDRecord.namespace == filters["namespace"])
                if filters.get("identifier"):
                    query = query.filter(ExplorerDIDRecord.identifier == filters["identifier"])
                if filters.get("deactivated"):
                    query = query.filter(ExplorerDIDRecord.deactivated == filters["deactivated"])
            
            return query.count()

    def create_explorer_resource_record(self, record_id: str, data: Dict, tags: Optional[Dict] = None) -> ExplorerResourceRecord:
        """Create an explorer resource record."""
        with self.get_session() as session:
            record = ExplorerResourceRecord(
                id=record_id,
                data=data,
                scid=tags.get("scid") if tags else None,
                resource_id=tags.get("resource_id") or tags.get("resourceId") if tags else None,
                resource_type=tags.get("resource_type") or tags.get("resourceType") if tags else None,
                did=tags.get("did") if tags else None,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def update_explorer_resource_record(self, record_id: str, data: Dict, tags: Optional[Dict] = None) -> Optional[ExplorerResourceRecord]:
        """Update an explorer resource record."""
        with self.get_session() as session:
            record = session.query(ExplorerResourceRecord).filter(ExplorerResourceRecord.id == record_id).first()
            if record:
                record.data = data
                if tags:
                    record.scid = tags.get("scid")
                    record.resource_id = tags.get("resource_id") or tags.get("resourceId")
                    record.resource_type = tags.get("resource_type") or tags.get("resourceType")
                    record.did = tags.get("did")
                session.commit()
                session.refresh(record)
                return record
            return None

    def get_explorer_resource_records(self, filters: Optional[Dict] = None, limit: Optional[int] = None, offset: int = 0) -> List[ExplorerResourceRecord]:
        """Get explorer resource records with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(ExplorerResourceRecord)
            
            if filters:
                if filters.get("scid"):
                    query = query.filter(ExplorerResourceRecord.scid == filters["scid"])
                if filters.get("resource_id") or filters.get("resourceId"):
                    rid = filters.get("resource_id") or filters.get("resourceId")
                    query = query.filter(ExplorerResourceRecord.resource_id == rid)
                if filters.get("resource_type") or filters.get("resourceType"):
                    rtype = filters.get("resource_type") or filters.get("resourceType")
                    query = query.filter(ExplorerResourceRecord.resource_type == rtype)
            
            if limit is not None:
                query = query.offset(offset).limit(limit)
            
            return query.all()

    def count_explorer_resource_records(self, filters: Optional[Dict] = None) -> int:
        """Count explorer resource records with optional filters."""
        with self.get_session() as session:
            query = session.query(ExplorerResourceRecord)
            
            if filters:
                if filters.get("scid"):
                    query = query.filter(ExplorerResourceRecord.scid == filters["scid"])
                if filters.get("resource_id") or filters.get("resourceId"):
                    rid = filters.get("resource_id") or filters.get("resourceId")
                    query = query.filter(ExplorerResourceRecord.resource_id == rid)
                if filters.get("resource_type") or filters.get("resourceType"):
                    rtype = filters.get("resource_type") or filters.get("resourceType")
                    query = query.filter(ExplorerResourceRecord.resource_type == rtype)
            
            return query.count()