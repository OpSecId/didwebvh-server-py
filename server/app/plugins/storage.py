"""SQLAlchemy Storage Manager."""

import asyncio
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
    AdminBackgroundTask,
    ServerPolicy,
    KnownWitnessRegistry,
    TailsFile,
)
from app.plugins import DidWebVH

logger = logging.getLogger(__name__)


class StorageManager:
    """SQLAlchemy-based storage manager for the DID WebVH server.

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
        self.db_type = "sqlite" if "sqlite" in self.db_url else "postgres"

        # Create engine with appropriate settings
        if self.db_type == "sqlite":
            # SQLite specific configuration
            self._engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )
        elif self.db_type == "postgres":
            # PostgreSQL configuration
            self._engine = create_engine(
                self.db_url, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False
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
        """Provision the database schema.

        Similar to AskarStorage.provision(), this creates all database tables.

        Args:
            recreate: If True, drop all tables before creating them (useful for tests)
        """
        logger.info(f"DB provisioning started for {self.db_url} .")
        try:
            if recreate:
                logger.info(f"Dropping all existing tables for {self.db_url}...")
                Base.metadata.drop_all(bind=self._engine)
                logger.info(f"All tables dropped for {self.db_url}.")

            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=self._engine)
            logger.info("DB provisioning finished.")
        except Exception as e:
            logger.error(f"DB provisioning failed: {str(e)}")
            raise Exception(f"DB provisioning failed: {str(e)}")

    def init_db(self):
        """Initialize the database schema (sync version of provision).

        This is a synchronous wrapper around provision for convenience.
        Use provision() for async contexts.
        """
        asyncio.run(self.provision())

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            Session: SQLAlchemy database session
        """
        return self._SessionLocal()

    def get_db(self):
        """Dependency injection helper for FastAPI endpoints.

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

    def create_did_controller(
        self,
        logs: List[Dict],
        witness_file: Optional[List[Dict]] = None,
        whois_presentation: Optional[Dict] = None,
    ) -> DidControllerRecord:
        """Create a new DID controller record - extracts all data from logs.

        Args:
            logs: Log entries (required - contains all DID info)
            witness_file: Optional witness file
            whois_presentation: Optional WHOIS presentation

        Returns:
            DidControllerRecord: The created record
        """

        session = self.get_session()
        try:
            # Create controller - let the model's __init__ derive all fields from logs
            controller = DidControllerRecord(
                logs=logs, witness_file=witness_file, whois_presentation=whois_presentation
            )
            session.add(controller)
            session.commit()
            session.refresh(controller)
            logger.info(f"Successfully committed DID controller {controller.scid} to database")
            return controller
        except Exception as e:
            logger.error(f"Error creating DID controller: {e}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()

    def update_did_controller(
        self,
        scid: str,
        logs: Optional[List[Dict]] = None,
        witness_file: Optional[List[Dict]] = None,
        whois_presentation: Optional[Dict] = None,
    ) -> Optional[DidControllerRecord]:
        """Update an existing DID controller record - re-extracts data from logs if provided.

        Args:
            scid: The SCID of the controller to update
            logs: Optional new log entries (if provided, re-extracts state/parameters/deactivated)
            witness_file: Optional witness file
            whois_presentation: Optional WHOIS presentation

        Returns:
            Optional[DidControllerRecord]: The updated record or None if not found
        """
        with self.get_session() as session:
            controller = (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )
            if controller:
                # Update logs and re-extract derived data
                if logs is not None:
                    controller.logs = logs

                    # Re-extract state and parameters from updated logs
                    webvh = DidWebVH()
                    state = webvh.get_document_state(logs)
                    params = state.params if hasattr(state, "params") else state.parameters

                    controller.parameters = params
                    controller.document = (
                        state.document
                        if isinstance(state.document, dict)
                        else state.document.model_dump()
                        if hasattr(state.document, "model_dump")
                        else dict(state.document)
                    )
                    controller.deactivated = params.get("deactivated", False) if params else False

                # Update optional fields
                if witness_file is not None:
                    controller.witness_file = witness_file
                if whois_presentation is not None:
                    controller.whois_presentation = whois_presentation

                session.commit()
                session.refresh(controller)
            return controller

    def get_did_controllers(
        self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, offset: int = 0
    ) -> List[DidControllerRecord]:
        """Get DID controllers with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(DidControllerRecord)

            if filters:
                if "scid" in filters:
                    query = query.filter(DidControllerRecord.scid == filters["scid"])
                if "did" in filters:
                    query = query.filter(DidControllerRecord.did == filters["did"])
                if "domain" in filters:
                    query = query.filter(DidControllerRecord.domain == filters["domain"])
                if "namespace" in filters:
                    query = query.filter(DidControllerRecord.namespace == filters["namespace"])
                if "alias" in filters:
                    query = query.filter(DidControllerRecord.alias == filters["alias"])
                if "deactivated" in filters:
                    query = query.filter(DidControllerRecord.deactivated == filters["deactivated"])

            if limit is not None:
                query = query.offset(offset).limit(limit)

            return query.all()

    def count_did_controllers(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count DID controllers with optional filters."""
        with self.get_session() as session:
            query = session.query(DidControllerRecord)

            if filters:
                if "scid" in filters:
                    query = query.filter(DidControllerRecord.scid == filters["scid"])
                if "did" in filters:
                    query = query.filter(DidControllerRecord.did == filters["did"])
                if "domain" in filters:
                    query = query.filter(DidControllerRecord.domain == filters["domain"])
                if "namespace" in filters:
                    query = query.filter(DidControllerRecord.namespace == filters["namespace"])
                if "alias" in filters:
                    query = query.filter(DidControllerRecord.alias == filters["alias"])
                if "deactivated" in filters:
                    query = query.filter(DidControllerRecord.deactivated == filters["deactivated"])

            return query.count()

    def create_log_entry(
        self,
        scid: str,
        did: str,
        domain: str,
        namespace: str,
        identifier: str,
        logs: List[Dict],
        deactivated: bool = False,
    ) -> DidControllerRecord:
        """Create a new log entry."""
        with self.get_session() as session:
            log_entry = DidControllerRecord(
                scid=scid,
                did=did,
                domain=domain,
                namespace=namespace,
                identifier=identifier,
                logs=logs,
                deactivated=deactivated,
            )
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            return log_entry

    def get_log_entry(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a log entry by SCID."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )

    def get_log_entries(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[DidControllerRecord]:
        """Get log entries with optional filters."""
        with self.get_session() as session:
            query = session.query(DidControllerRecord)

            if filters:
                if "did" in filters:
                    query = query.filter(DidControllerRecord.did == filters["did"])
                if "domain" in filters:
                    query = query.filter(DidControllerRecord.domain == filters["domain"])
                if "namespace" in filters:
                    query = query.filter(DidControllerRecord.namespace == filters["namespace"])
                if "identifier" in filters:
                    query = query.filter(DidControllerRecord.identifier == filters["identifier"])
                if "deactivated" in filters:
                    query = query.filter(DidControllerRecord.deactivated == filters["deactivated"])

            return query.all()

    def update_log_entry(
        self, scid: str, logs: List[Dict], deactivated: Optional[bool] = None
    ) -> Optional[DidControllerRecord]:
        """Update an existing log entry."""
        with self.get_session() as session:
            log_entry = (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )
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
            log_entry = (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )
            if log_entry:
                session.delete(log_entry)
                session.commit()
                return True
            return False

    # ========== Resource Operations ==========

    def create_resource(self, scid: str, attested_resource: Dict) -> AttestedResourceRecord:
        """Create a new resource - extracts metadata from attested_resource.

        Args:
            scid: The SCID from the parent DidControllerRecord (FK relationship)
            attested_resource: The full attested resource object

        Returns:
            AttestedResourceRecord: The created record
        """
        with self.get_session() as session:
            # The model's __init__ will extract all fields from attested_resource
            # Pass scid as kwarg to ensure FK relationship is correct (overrides extracted value)
            resource = AttestedResourceRecord(attested_resource=attested_resource, scid=scid)
            session.add(resource)
            session.commit()
            session.refresh(resource)
            return resource

    def get_resource(self, resource_id: str) -> Optional[AttestedResourceRecord]:
        """Get a resource by ID."""
        with self.get_session() as session:
            return (
                session.query(AttestedResourceRecord)
                .filter(AttestedResourceRecord.resource_id == resource_id)
                .first()
            )

    def get_resources(
        self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None, offset: int = 0
    ) -> List[AttestedResourceRecord]:
        """Get resources with optional filters and pagination."""
        with self.get_session() as session:
            query = session.query(AttestedResourceRecord)

            if filters:
                if "scid" in filters:
                    query = query.filter(AttestedResourceRecord.scid == filters["scid"])
                if "did" in filters:
                    query = query.filter(AttestedResourceRecord.did == filters["did"])
                if "resource_type" in filters:
                    query = query.filter(
                        AttestedResourceRecord.resource_type == filters["resource_type"]
                    )
                if "resource_id" in filters:
                    query = query.filter(
                        AttestedResourceRecord.resource_id == filters["resource_id"]
                    )

            if limit is not None:
                query = query.offset(offset).limit(limit)

            return query.all()

    def count_resources(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count resources with optional filters."""
        with self.get_session() as session:
            query = session.query(AttestedResourceRecord)

            if filters:
                if "scid" in filters:
                    query = query.filter(AttestedResourceRecord.scid == filters["scid"])
                if "did" in filters:
                    query = query.filter(AttestedResourceRecord.did == filters["did"])
                if "resource_type" in filters:
                    query = query.filter(
                        AttestedResourceRecord.resource_type == filters["resource_type"]
                    )
                if "resource_id" in filters:
                    query = query.filter(
                        AttestedResourceRecord.resource_id == filters["resource_id"]
                    )

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

            resource = (
                session.query(AttestedResourceRecord)
                .filter(AttestedResourceRecord.resource_id == resource_id)
                .first()
            )
            if resource:
                resource.attested_resource = attested_resource
                session.commit()
                session.refresh(resource)
            return resource

    def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource."""
        with self.get_session() as session:
            resource = (
                session.query(AttestedResourceRecord)
                .filter(AttestedResourceRecord.resource_id == resource_id)
                .first()
            )
            if resource:
                session.delete(resource)
                session.commit()
                return True
            return False

    # ========== Credential Operations ==========
    # TODO: VerifiableCredentialRecord operations temporarily removed

    # ========== Task Operations ==========

    def create_task(
        self,
        task_id: str,
        task_type: str,
        status: str,
        progress: Optional[Dict] = None,
        message: Optional[str] = None,
    ) -> AdminBackgroundTask:
        """Create a new task."""
        with self.get_session() as session:
            task = AdminBackgroundTask(
                task_id=task_id,
                task_type=task_type,
                status=status,
                progress=progress or {},
                message=message,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task

    def get_task(self, task_id: str) -> Optional[AdminBackgroundTask]:
        """Get a task by ID."""
        with self.get_session() as session:
            return (
                session.query(AdminBackgroundTask)
                .filter(AdminBackgroundTask.task_id == task_id)
                .first()
            )

    def get_tasks(self, filters: Optional[Dict[str, Any]] = None) -> List[AdminBackgroundTask]:
        """Get tasks with optional filters."""
        with self.get_session() as session:
            query = session.query(AdminBackgroundTask)

            if filters:
                if "task_type" in filters:
                    query = query.filter(AdminBackgroundTask.task_type == filters["task_type"])
                if "status" in filters:
                    query = query.filter(AdminBackgroundTask.status == filters["status"])

            return query.all()

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[Dict] = None,
        message: Optional[str] = None,
    ) -> Optional[AdminBackgroundTask]:
        """Update an existing task."""
        with self.get_session() as session:
            task = (
                session.query(AdminBackgroundTask)
                .filter(AdminBackgroundTask.task_id == task_id)
                .first()
            )
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
            task = (
                session.query(AdminBackgroundTask)
                .filter(AdminBackgroundTask.task_id == task_id)
                .first()
            )
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

    def create_or_update_registry(
        self, registry_id: str, registry_type: str, registry_data: Dict, meta: Optional[Dict] = None
    ) -> KnownWitnessRegistry:
        """Create or update a registry."""
        with self.get_session() as session:
            registry = (
                session.query(KnownWitnessRegistry)
                .filter(KnownWitnessRegistry.registry_id == registry_id)
                .first()
            )

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
                    meta=meta,
                )
                session.add(registry)

            session.commit()
            session.refresh(registry)
            return registry

    def get_registry(self, registry_id: str) -> Optional[KnownWitnessRegistry]:
        """Get a registry by ID."""
        with self.get_session() as session:
            return (
                session.query(KnownWitnessRegistry)
                .filter(KnownWitnessRegistry.registry_id == registry_id)
                .first()
            )

    # ========== Witness File Operations ==========

    def create_or_update_witness_file(
        self, scid: str, witness_proofs: List[Dict]
    ) -> DidControllerRecord:
        """Create or update a witness file."""
        with self.get_session() as session:
            controller = (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )

            if controller:
                controller.witness_file = witness_proofs
            else:
                # Can't create a witness file without an existing DID controller
                raise ValueError(f"No DID controller found with scid: {scid}")

            session.commit()
            session.refresh(controller)
            return controller

    def get_witness_file(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a witness file by SCID."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )

    # ========== WHOIS Presentation Operations ==========

    def create_or_update_whois(self, scid: str, presentation: Dict) -> DidControllerRecord:
        """Create or update a WHOIS presentation."""
        with self.get_session() as session:
            controller = (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )

            if controller:
                controller.whois_presentation = presentation
            else:
                # Can't create a whois without an existing DID controller
                raise ValueError(f"No DID controller found with scid: {scid}")

            session.commit()
            session.refresh(controller)
            return controller

    def get_whois(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a WHOIS presentation by SCID."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )

    # ========== Helper Methods (Query by Namespace and Identifier) ==========

    def get_did_controller_by_scid(self, scid: str) -> Optional[DidControllerRecord]:
        """Get a DID controller by SCID."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord).filter(DidControllerRecord.scid == scid).first()
            )

    def get_did_controller_by_alias(
        self, namespace: str, identifier: str
    ) -> Optional[DidControllerRecord]:
        """Get a log entry by namespace and identifier (alias)."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord)
                .filter(
                    DidControllerRecord.namespace == namespace,
                    DidControllerRecord.alias == identifier,
                )
                .first()
            )

    def get_witness_file_by_identifier(
        self, namespace: str, identifier: str
    ) -> Optional[DidControllerRecord]:
        """Get a witness file by namespace and identifier (alias)."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord)
                .filter(
                    DidControllerRecord.namespace == namespace,
                    DidControllerRecord.alias == identifier,
                )
                .first()
            )

    def get_whois_by_identifier(
        self, namespace: str, identifier: str
    ) -> Optional[DidControllerRecord]:
        """Get a WHOIS presentation by namespace and identifier (alias)."""
        with self.get_session() as session:
            return (
                session.query(DidControllerRecord)
                .filter(
                    DidControllerRecord.namespace == namespace,
                    DidControllerRecord.alias == identifier,
                )
                .first()
            )

    # ========== Tails File Operations ==========

    def create_tails_file(
        self, tails_hash: str, file_content_hex: str, file_size: int
    ) -> TailsFile:
        """Create a new tails file."""
        with self.get_session() as session:
            tails_file = TailsFile(
                tails_hash=tails_hash, file_content_hex=file_content_hex, file_size=file_size
            )
            session.add(tails_file)
            session.commit()
            session.refresh(tails_file)
            return tails_file

    def get_tails_file(self, tails_hash: str) -> Optional[TailsFile]:
        """Get a tails file by hash."""
        with self.get_session() as session:
            return session.query(TailsFile).filter(TailsFile.tails_hash == tails_hash).first()
