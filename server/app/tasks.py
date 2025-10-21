"""Background Tasks."""

import logging
import json
import asyncio
import time
import uuid
from hashlib import sha256
from typing import Dict, List

from enum import Enum

from config import settings

from aries_askar import Key
from multiformats import multibase

from app.models.policy import ActivePolicy
from app.models.task import TaskInstance
from app.models.resource import AttestedResource, ResourceMetadata
from app.plugins import AskarStorage, AskarStorageKeys, DidWebVH
from app.utilities import (
    timestamp,
    sync_resource,
    sync_did_info,
)

logger = logging.getLogger(__name__)

askar = AskarStorage()
webvh = DidWebVH()


class TaskType(str, Enum):
    """Types of tasks."""

    SetPolicy = "set_policy"
    SyncRecords = "sync_records"
    LoadTest = "load_test"
    MigrateAskarToPostgres = "migrate_askar_to_postgres"


class TaskStatus(str, Enum):
    """Statuses of tasks."""

    started = "started"
    finished = "finished"
    abandonned = "abandonned"


class TaskManager:
    """TaskManager."""

    def __init__(self, task_id: str = None):
        """Initialize TaskManager."""
        self.task_id = task_id
        self.task = None
        self.workers = 10

    def task_tags(self):
        """Return current task tags."""
        return {"status": self.task.status, "task_type": self.task.type}

    async def start_task(self, task_type):
        """Start new task."""
        logger.info(f"Task {task_type} started: {self.task_id}")
        self.task = TaskInstance(
            id=self.task_id,
            type=task_type,
            created=timestamp(),
            updated=timestamp(),
            status=TaskStatus.started,
            progress={},
        )
        await askar.store("task", self.task_id, self.task.model_dump(), self.task_tags())

    async def update_task_progress(self, progress):
        """Update task progress."""
        logger.debug(f"Task {self.task_id} updated: {json.dumps(progress)}")
        self.task.progress.update(progress)
        self.task.updated = timestamp()
        await askar.update("task", self.task_id, self.task.model_dump(), self.task_tags())

    async def finish_task(self):
        """Finish existing task."""
        logger.info(f"Task {self.task_id} finished.")
        self.task.status = TaskStatus.finished
        self.task.updated = timestamp()
        await askar.update("task", self.task_id, self.task.model_dump(), self.task_tags())

    async def abandon_task(self, message=None):
        """Abandon existing task."""
        logger.error(f"Task {self.task_id} abandonned: {message}")
        self.task.status = TaskStatus.abandonned
        self.task.message = message
        self.task.updated = timestamp()
        await askar.update("task", self.task_id, self.task.model_dump(), self.task_tags())

    async def set_policies(self, force=False):
        """Provision DB with policies."""

        await self.start_task(TaskType.SetPolicy)

        try:
            if not (policy := await askar.fetch("policy", "active")):
                logger.info("Creating server policies.")
                policy = ActivePolicy(
                    version=settings.WEBVH_VERSION,
                    witness=settings.WEBVH_WITNESS,
                    watcher=settings.WEBVH_WATCHER,
                    portability=settings.WEBVH_PORTABILITY,
                    prerotation=settings.WEBVH_PREROTATION,
                    endorsement=settings.WEBVH_ENDORSEMENT,
                    witness_registry_url=settings.KNOWN_WITNESS_REGISTRY,
                ).model_dump()
                await askar.store("policy", "active", policy)
            else:
                logger.info("Skipping server policies.")

            await self.update_task_progress({"policy": json.dumps(policy)})

            if not (witness_registry := await askar.fetch("registry", "knownWitnesses")):
                logger.info("Creating known witness registry.")
                witness_registry = {
                    "meta": {"created": timestamp(), "updated": timestamp()},
                    "registry": {},
                }
                if settings.KNOWN_WITNESS_KEY:
                    witness_did = f"did:key:{settings.KNOWN_WITNESS_KEY}"
                    witness_registry["registry"][witness_did] = {"name": "Default Server Witness"}
                await askar.store("registry", "knownWitnesses", witness_registry)
            else:
                logger.info("Skipping known witness registry.")

            await self.update_task_progress({"knownWitnessRegistry": json.dumps(witness_registry)})

            await self.finish_task()

        except Exception as e:
            await self.abandon_task(str(e))

    async def sync_explorer_records(self, force=False):
        """Sync explorer records."""

        await self.start_task(TaskType.SyncRecords)

        try:
            entries = await askar.get_category_entries("resource")
            for idx, entry in enumerate(entries):
                await self.update_task_progress({"resourceRecords": f"{idx + 1}/{len(entries)}"})

                if not force and await askar.fetch("resourceRecord", entry.name):
                    continue

                resource_record, tags = sync_resource(entry.value_json)
                await askar.update("resource", entry.name, entry.value_json, tags)
                await askar.store_or_update("resourceRecord", entry.name, resource_record, tags)

            entries = await askar.get_category_entries("logEntries")
            for idx, entry in enumerate(entries):
                await self.update_task_progress({"didRecords": f"{idx + 1}/{len(entries)}"})

                if not force and await askar.fetch("didRecord", entry.name):
                    continue

                logs = entry.value_json
                state = webvh.get_document_state(logs)
                did_record, tags = sync_did_info(
                    state=state,
                    logs=logs,
                    did_resources=[
                        resource.value_json
                        for resource in await askar.get_category_entries(
                            "resource", {"scid": state.scid}
                        )
                    ],
                    witness_file=(await askar.fetch("witnessFile", entry.name) or []),
                    whois_presentation=(await askar.fetch("whois", entry.name) or {}),
                )
                await askar.update("logEntries", entry.name, entry.value_json, tags=tags)
                await askar.store_or_update("didRecord", entry.name, did_record, tags=tags)

            await self.finish_task()

        except Exception as e:
            await self.abandon_task(str(e))

    async def load_test(self, entries: int = 100):
        """Create mock DIDs for load testing."""

        await self.start_task(TaskType.LoadTest)

        try:
            logger.info(f"Creating {entries} mock DID entries for load testing...")
            created_dids = []
            
            for i in range(entries):
                # Generate unique identifier for this DID
                identifier = str(uuid.uuid4())[:8]
                namespace = "loadtest"
                
                # Create 3 witnesses for this DID with threshold of 2
                witnesses = []
                for w in range(3):
                    # Generate a real ed25519 key pair
                    key = Key.generate("ed25519")
                    public_key_bytes = key.get_public_bytes()
                    
                    # Create multibase encoding (base58btc) with ed25519-pub multicodec prefix
                    # Prefix: 0xed 0x01 for ed25519-pub
                    multicodec_prefix = bytes([0xed, 0x01])
                    multikey = multibase.encode(multicodec_prefix + public_key_bytes, "base58btc")
                    
                    # Create did:key (multikey format)
                    witnesses.append({"id": f"did:key:{multikey}"})
                
                # Build params with witnesses and watchers
                params = {
                    "method": "did:webvh:1.0",
                    "witness": {
                        "witnesses": witnesses,
                        "threshold": 2
                    },
                    "watchers": [
                        "https://watcher1.example.com",
                        "https://watcher2.example.com"
                    ]
                }
                
                # Create mock DID log entries with params
                test_logs = webvh.new_test_entry_logs(identifier, params=params)
                
                # Create witness file with proper structure for UI display
                witness_file = []
                for log in test_logs:
                    for witness in witnesses:
                        witness_did = witness['id']
                        multikey = witness_did.split(':')[-1]
                        
                        # Create witness proof
                        witness_proof = {
                            "type": "DataIntegrityProof",
                            "cryptosuite": "eddsa-jcs-2022",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": f"{witness_did}#{multikey}",
                            "proofValue": f"z{uuid.uuid4().hex}",  # Mock proof value
                            "created": timestamp()
                        }
                        
                    witness_file.append({
                        "versionId": log['versionId'],
                        "proof": witness_proof,
                    })
                
                # Get the document state from the logs
                state = webvh.get_document_state(test_logs)
                
                # Debug: Print what parameters are in the state
                logger.info(f"State params: {state.params}")
                logger.info(f"State witness: {state.witness if hasattr(state, 'witness') else 'No witness attribute'}")
                logger.info(f"State has witness attr: {hasattr(state, 'witness')}")
                
                # Parse DID components
                did = state.document_id
                _, _, scid, domain, ns, alias = did.split(":")
                
                # Create client_id for storage (namespace:identifier format)
                client_id = f"{namespace}:{identifier}"
                
                tags = {
                    "scid": scid,
                    "domain": domain,
                    "namespace": namespace,
                    "alias": identifier,
                    "did": did,
                    "deactivated": "False",
                    "created": timestamp(),
                    "updated": timestamp()
                }
                
                # Create whois credentials - each witness signs a different one
                whois_credentials = []
                credential_types = [
                    ("WhoisCredential", {
                        "id": did,
                        "name": f"Load Test Entity {i}",
                        "organization": "DID WebVH Test Organization",
                        "email": f"loadtest{i}@example.com",
                        "country": "CA",
                        "role": "Test Controller"
                    }),
                    ("OrganizationCredential", {
                        "id": did,
                        "legalName": "DID WebVH Test Organization",
                        "taxId": f"TX-{uuid.uuid4().hex[:12]}",
                        "jurisdiction": "Canada",
                        "registrationDate": "2024-01-01"
                    }),
                    ("ContactCredential", {
                        "id": did,
                        "phone": "+1-555-0100",
                        "address": "123 Test Street, Test City, TC 12345",
                        "website": "https://test.example.com"
                    })
                ]
                
                for w, witness in enumerate(witnesses):
                    witness_did = witness['id']
                    witness_multikey = witness_did.split(':')[-1]
                    cred_type, cred_subject = credential_types[w]
                    
                    whois_credential = {
                        "@context": [
                            "https://www.w3.org/2018/credentials/v1"
                        ],
                        "type": ["VerifiableCredential", cred_type],
                        "issuer": witness_did,
                        "issuanceDate": timestamp(),
                        "credentialSubject": cred_subject,
                        "proof": {
                            "type": "DataIntegrityProof",
                            "cryptosuite": "eddsa-jcs-2022",
                            "proofPurpose": "assertionMethod",
                            "verificationMethod": f"{witness_did}#{witness_multikey}",
                            "proofValue": f"z{uuid.uuid4().hex}{uuid.uuid4().hex[:16]}",
                            "created": timestamp()
                        }
                    }
                    whois_credentials.append(whois_credential)
                
                # Create whois presentation with all credentials
                whois_presentation = {
                    "@context": [
                        "https://www.w3.org/2018/credentials/v1"
                    ],
                    "type": ["VerifiablePresentation"],
                    "holder": did,
                    "verifiableCredential": whois_credentials,
                    "proof": {
                        "type": "DataIntegrityProof",
                        "cryptosuite": "eddsa-jcs-2022",
                        "proofPurpose": "authentication",
                        "verificationMethod": f"{did}#mockkey",
                        "proofValue": f"z{uuid.uuid4().hex}{uuid.uuid4().hex[:16]}",
                        "created": timestamp(),
                        "challenge": "whois-presentation"
                    }
                }
                
                # Create a mock resource for this DID
                content = {
                    'name': 'LoadTestSchema',
                    'version': '1.0.0',
                    'issuerId': did,
                    'attrNames': ['name', 'age', 'timestamp', 'loadtest_id']
                }
                
                # Generate resource ID from content hash
                content_hash = sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]
                resource_id = f"loadtest-{content_hash}"
                
                metadata = ResourceMetadata(
                    resourceId=resource_id,
                    resourceType='anonCredsSchema',
                    resourceName=f'LoadTestSchema{i}'
                )
                
                # Create attested resource with mock proof
                attested_resource = {
                    "@context": [
                        "https://identity.foundation/did-attested-resources/context/v0.1",
                        "https://w3id.org/security/data-integrity/v2"
                    ],
                    "type": ["AttestedResource"],
                    "id": f'{did}/resources/{resource_id}',
                    "content": content,
                    "metadata": metadata.model_dump(),
                    "proof": {
                        "type": "DataIntegrityProof",
                        "cryptosuite": "eddsa-jcs-2022",
                        "proofPurpose": "assertionMethod",
                        "verificationMethod": f"{did}#mockkey",
                        "proofValue": "zmockedproofvalue1234567890"  # Mock proof
                    }
                }
                
                # Create resource record for explorer
                resource_record, resource_tags = sync_resource(attested_resource)
                
                # Merge tags
                resource_tags.update(tags)
                resource_tags.update({
                    "resourceType": metadata.resourceType,
                    "resourceName": metadata.resourceName,
                    "resourceId": resource_id
                })
                
                # Store resource in proper categories
                resource_store_id = f"{namespace}:{identifier}:{resource_id}"
                await askar.store("resource", resource_store_id, attested_resource, resource_tags)
                await askar.store("resourceRecord", resource_store_id, resource_record, resource_tags)
                # Create DID record for explorer (with witness file, resources, and whois)
                did_record, _ = sync_did_info(
                    state=state,
                    logs=test_logs,
                    did_resources=[attested_resource],
                    witness_file=witness_file,
                    whois_presentation=whois_presentation
                )
                
                # Store in real categories (not test categories)
                await askar.store("logEntries", client_id, test_logs, tags)
                await askar.store("didRecord", client_id, did_record, tags)
                await askar.store("witnessFile", client_id, witness_file, tags)
                await askar.store("whoisPresentation", client_id, whois_presentation, tags)
                
                created_dids.append(did)
                
                await self.update_task_progress({
                    "status": "creating_dids",
                    "created": f"{i + 1}/{entries}",
                    "total": entries
                })
                
            
            # Mark task as complete
            await self.update_task_progress({
                "status": "completed",
                "created": entries,
                "total": entries,
                "sample_dids": created_dids[:5]  # Show first 5 DIDs as sample
            })
            await self.finish_task()
            logger.info(f"Load test completed: created {entries} mock DID entries")

        except Exception as e:
            logger.error(f"Load test failed: {str(e)}", exc_info=True)
            await self.abandon_task(str(e))


    async def migrate_askar_to_postgres(self, backup_enabled: bool = True):
        """Migrate data from Askar to PostgreSQL."""
        
        await self.start_task(TaskType.MigrateAskarToPostgres)
        
        try:
            logger.info("Starting Askar to PostgreSQL migration...")
            
            # Import migration dependencies
            from sqlalchemy.orm import Session
            from sqlalchemy import create_engine, select
            from aries_askar import Store
            from app.db.explorer_models import (
                ExplorerDIDRecord,
                ExplorerResourceRecord,
                AskarGenericRecord,
            )
            from app.db import Base, engine
            
            # Initialize migration stats
            stats = {
                "did_records": 0,
                "resource_records": 0,
                "generic_records": 0,
                "errors": []
            }
            
            # Step 1: Create PostgreSQL tables
            await self.update_task_progress({
                "status": "creating_tables",
                "message": "Creating PostgreSQL tables..."
            })
            
            Base.metadata.create_all(bind=engine)
            logger.info("PostgreSQL tables created successfully")
            
            # Step 2: Migrate explorer records
            await self.update_task_progress({
                "status": "migrating_explorer_records",
                "message": "Migrating explorer records..."
            })
            
            # Migrate DID records
            did_records = await askar.store_search("didRecord", {})
            with Session(engine) as session:
                for record in did_records:
                    try:
                        data = record.value
                        tags = record.tags
                        
                        explorer_record = ExplorerDIDRecord(
                            id=tags.get("did", ""),
                            data=data,
                            scid=tags.get("scid", ""),
                            domain=tags.get("domain", ""),
                            namespace=tags.get("namespace", ""),
                            identifier=tags.get("alias", ""),
                            did=tags.get("did", ""),
                            deactivated=tags.get("deactivated", "False")
                        )
                        session.add(explorer_record)
                        stats["did_records"] += 1
                    except Exception as e:
                        stats["errors"].append(f"DID record error: {str(e)}")
                
                # Migrate resource records
                resource_records = await askar.store_search("resource", {})
                for record in resource_records:
                    try:
                        data = record.value
                        tags = record.tags
                        
                        explorer_record = ExplorerResourceRecord(
                            id=tags.get("resourceId", ""),
                            data=data,
                            scid=tags.get("scid", ""),
                            resource_id=tags.get("resourceId", ""),
                            resource_type=tags.get("resourceType", ""),
                            did=tags.get("did", "")
                        )
                        session.add(explorer_record)
                        stats["resource_records"] += 1
                    except Exception as e:
                        stats["errors"].append(f"Resource record error: {str(e)}")
                
                session.commit()
            
            # Step 3: Migrate generic records
            await self.update_task_progress({
                "status": "migrating_generic_records",
                "message": "Migrating generic records..."
            })
            
            categories_to_migrate = [
                "logEntries", "resources", "witnessFiles", "whoisPresentations",
                "task", "policy", "registry", "testLogEntry", "testResource"
            ]
            
            with Session(engine) as session:
                for category in categories_to_migrate:
                    try:
                        records = await askar.store_search(category, {})
                        for record in records:
                            generic_record = AskarGenericRecord(
                                category=category,
                                key=record.name,
                                data=record.value,
                                tags=record.tags or {}
                            )
                            session.add(generic_record)
                            stats["generic_records"] += 1
                    except Exception as e:
                        stats["errors"].append(f"Generic record error ({category}): {str(e)}")
                
                session.commit()
            
            # Step 4: Create backup if requested
            if backup_enabled:
                await self.update_task_progress({
                    "status": "creating_backup",
                    "message": "Creating Askar backup..."
                })
                
                backup_path = f"app.db.backup.{int(time.time())}"
                try:
                    # Simple file copy for SQLite backup
                    import shutil
                    if os.path.exists("app.db"):
                        shutil.copy2("app.db", backup_path)
                        logger.info(f"Askar backup created: {backup_path}")
                except Exception as e:
                    stats["errors"].append(f"Backup error: {str(e)}")
            
            # Step 5: Finalize migration
            await self.update_task_progress({
                "status": "completed",
                "message": "Migration completed successfully",
                "stats": stats
            })
            
            logger.info("Migration completed successfully!")
            logger.info(f"Migrated {stats['did_records']} DID records")
            logger.info(f"Migrated {stats['resource_records']} resource records")
            logger.info(f"Migrated {stats['generic_records']} generic records")
            logger.info(f"Encountered {len(stats['errors'])} errors")
            
            await self.finish_task()
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}", exc_info=True)
            await self.abandon_task(str(e))
