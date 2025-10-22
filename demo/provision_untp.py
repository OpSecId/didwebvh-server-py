import os
import requests
import uuid
import time
from loguru import logger

from operator import itemgetter

AGENT_ADMIN_API_URL = os.getenv("AGENT_ADMIN_API_URL", "http://witness-agent:8020")
AGENT_ADMIN_API_HEADERS = {"X-API-KEY": os.getenv("AGENT_ADMIN_API_KEY", "")}
WATCHER_API_HEADERS = {"X-API-KEY": os.getenv("WATCHER_API_KEY", "")}
WEBVH_SERVER_URL = os.getenv("WEBVH_SERVER_URL", None)
WATCHER_URL = os.getenv("WATCHER_URL", None)


class Agent:
    def __init__(self):
        self.admin_url = os.getenv("AGENT_ADMIN_API_URL", "http://witness-agent:8020")
        self.admin_headers = {"X-API-KEY": os.getenv("AGENT_ADMIN_API_KEY", "")}
        self.server_url = os.getenv("WEBVH_SERVER_URL", None)
        self.watcher_url = os.getenv("WATCHER_URL", None)
        self.watcher_headers = {"X-API-KEY": os.getenv("WATCHER_API_KEY", "")}

    def try_return(request):
        # Sleep to avoid rate limiting
        time.sleep(1)
        try:
            return request.json()
        except requests.exceptions.JSONDecodeError:
            logger.warning("Unexpected response from agent:")
            logger.warning(request.text)
            raise requests.exceptions.JSONDecodeError


    def configure_plugin(self, server_url=WEBVH_SERVER_URL):
        logger.info("Configuring plugin")
        r = requests.post(
            f"{self.admin_url}/did/webvh/configuration",
            headers=self.admin_headers,
            json={
                "server_url": server_url,
                "notify_watchers": True,
                "witness": True,
                "auto_attest": True,
                "endorsement": False,
            },
        )
        return self.try_return(r)


    def register_watcher(self,did):
        scid = itemgetter(2)(did.split(":"))
        logger.info(f"Registering watcher {scid}")
        r = requests.post(f"{self.watcher_url}/scid?did={did}", headers=self.watcher_headers)
        return self.try_return(r)


    def notify_watcher(self,did):
        scid = itemgetter(2)(did.split(":"))
        logger.info(f"Notifying watcher {scid}")
        r = requests.post(f"{self.watcher_url}/log?did={did}")
        return self.try_return(r)


    def create_did(self,namespace):
        logger.info(f"Creating DID in {namespace}")
        r = requests.post(
            f"{self.admin_url}/did/webvh/create",
            headers=self.admin_headers,
            json={
                "options": {
                    "apply_policy": 1,
                    "witnessThreshold": 1,
                    "watchers": [self.watcher_url],
                    "namespace": namespace,
                    "identifier": str(uuid.uuid4())[:6],
                }
            },
        )
        return self.try_return(r)


    def update_did(self,scid):
        logger.info(f"Updating DID {scid}")
        r = requests.post(
            f"{self.admin_url}/did/webvh/update?scid={scid}",
            headers=self.admin_headers,
            json={},
        )
        return self.try_return(r)


    def deactivate_did(self,scid):
        logger.info(f"Deactivating DID {scid}")
        r = requests.post(
            f"{self.admin_url}/did/webvh/deactivate?scid={scid}",
            headers=self.admin_headers,
            json={"options": {}},
        )
        return self.try_return(r)


    def sign_credential(self,issuer_id, subject_id):
        scid = itemgetter(2)(subject_id.split(":"))
        logger.info(f"Signing credential {scid}")
        issuer_key = issuer_id.split(":")[-1]
        r = requests.post(
            f"{self.admin_url}/vc/di/add-proof",
            headers=self.admin_headers,
            json={
                "document": {
                    "@context": [
                        "https://www.w3.org/ns/credentials/v2",
                        "https://www.w3.org/ns/credentials/examples/v2",
                    ],
                    "type": ["VerifiableCredential", "ExampleIdentityCredential"],
                    "issuer": {"id": issuer_id, "name": "Example Issuer"},
                    "credentialSubject": {
                        "id": subject_id,
                        "description": "Sample VC for WHOIS.vp",
                    },
                },
                "options": {
                    "type": "DataIntegrityProof",
                    "cryptosuite": "eddsa-jcs-2022",
                    "proofPurpose": "assertionMethod",
                    "verificationMethod": f"{issuer_id}#{issuer_key}",
                },
            },
        )
        return self.try_return(r)


    def sign_presentation(self,signing_key, credential):
        holder_id = credential.get("credentialSubject").get("id")
        scid = itemgetter(2)(holder_id.split(":"))
        logger.info(f"Signing presentation {scid}")
        r = requests.post(
            f"{self.admin_url}/vc/di/add-proof",
            headers=self.admin_headers,
            json={
                "document": {
                    "@context": ["https://www.w3.org/ns/credentials/v2"],
                    "type": ["VerifiablePresentation"],
                    "holder": holder_id,
                    "verifiableCredential": [credential],
                },
                "options": {
                    "type": "DataIntegrityProof",
                    "cryptosuite": "eddsa-jcs-2022",
                    "proofPurpose": "authentication",
                    "verificationMethod": f"{holder_id}#{signing_key}",
                },
            },
        )
        return self.try_return(r)


    def upload_whois(self,vp):
        holder_id = vp.get("holder")
        scid, namespace, alias = itemgetter(2, 4, 5)(holder_id.split(":"))
        logger.info(f"Uploading whois {scid}")
        r = requests.post(
            f"{self.server_url}/{namespace}/{alias}/whois",
            json={"verifiablePresentation": vp},
        )
        return self.try_return(r)


    def create_schema(
        self,issuer_id, name="Test Schema", version="1.0", attributes=["test_attribute"]
    ):
        scid = itemgetter(2)(issuer_id.split(":"))
        logger.info(f"Creating schema {scid}")
        r = requests.post(
            f"{self.admin_url}/anoncreds/schema",
            headers=self.admin_headers,
            json={
                "schema": {
                    "attrNames": attributes,
                    "issuerId": issuer_id,
                    "name": name,
                    "version": version,
                }
            },
        )
        return self.try_return(r)


    def create_cred_def(self, schema_id, tag="default", revocation_size=0):
        issuer_id = schema_id.split("/")[0]
        scid = itemgetter(2)(issuer_id.split(":"))
        logger.info(f"Creating cred def {scid}")
        r = requests.post(
            f"{AGENT_ADMIN_API_URL}/anoncreds/credential-definition",
            headers=AGENT_ADMIN_API_HEADERS,
            json={
                "credential_definition": {
                    "issuerId": issuer_id,
                    "schemaId": schema_id,
                    "tag": tag,
                },
                "options": {
                    "revocation_registry_size": revocation_size,
                    "support_revocation": True if revocation_size else False,
                },
            },
        )
        return self.try_return(r)

def __main__():
    logger.info("Configuring Agent")
    DEMO = {
        'actors': {
            'cpo': {
                'name': 'Chief Permitting Officer'
            },
            'tek': {
                'name': 'Tek Mines'
            },
            'roc': {
                'name': 'Registrar of Companies'
            },
        }
    }
    agent = Agent()
    webvh_config = agent.configure_plugin(WEBVH_SERVER_URL)
    witness_id = webvh_config.get("witnesses")[0]
    logger.info(f"Witness Configured: {witness_id}")
    logger.info("Provisioning Server")
    
    cpo = agent.create_did('pilots', DEMO['actors']['cpo']['name'])
    cpo_scid = cpo.get("parameters", {}).get("scid")
    cpo_did = cpo.get("state", {}).get("id")
    cpo_signing_key = (
        cpo.get("state", {})
        .get("verificationMethod")[0]
        .get("publicKeyMultibase")
    )
    agent.register_watcher(cpo_did)
    agent.update_did(cpo_scid)
    agent.notify_watcher(cpo_did)

    logger.info(f"CPO SCID: {cpo_scid}")
    
    
    tek = agent.create_did('pilots', DEMO['actors']['tek']['name'])
    tek_scid = tek.get("parameters", {}).get("scid")
    tek_did = tek.get("state", {}).get("id")
    logger.info(f"TEK SCID: {tek_scid}")
    
    
    roc = agent.create_did('pilots', DEMO['actors']['roc']['name'])
    roc_scid = roc.get("parameters", {}).get("scid")
    roc_did = roc.get("state", {}).get("id")
    logger.info(f"ROC SCID: {roc_scid}")
    
    
    # ROC issue DIA(BCRegistry)
    dia = agent.sign({
        
    })
    # TEK publishes DIA(BCRegistry) as VC in whois
    # CPO issues DCC(MinesActPermit)
    # CPO publishes DCC(MinesActPermit) as VC
    # TEK issues DPP(RawMaterial) linked to DCC(MinesActPermit)
    # TEK publishes DPP(RawMaterial) as VC
    
    
    
    
    # # Create DIDs in two namespaces
    # for namespace in ["ns-01", "ns-02"]:
    #     # Create 2 DIDs in each namespace
    #     for idx in range(2):
    #         log_entry = create_did(namespace)
    #         scid = log_entry.get("parameters", {}).get("scid")
    #         did = log_entry.get("state", {}).get("id")
    #         signing_key = (
    #             log_entry.get("state", {})
    #             .get("verificationMethod")[0]
    #             .get("publicKeyMultibase")
    #         )
    #         logger.info(f"New signing key: {signing_key}")

    #         # Register with watcher if configured
    #         if WATCHER_URL:
    #             register_watcher(did)

    #         # NOTE, following lines depend on next plugin release
    #         # Update the DID twice to generate some log entries
    #         update_did(scid)
    #         update_did(scid)
    #         notify_watcher(did)

    #         # Create a sample whois VP
    #         vc = sign_credential(witness_id, did).get("securedDocument")
    #         vp = sign_presentation(signing_key, vc).get("securedDocument")
    #         whois = upload_whois(vp)

    #         # Create anoncreds schema and cred def
    #         schema = create_schema(did)
    #         schema_id = schema.get("schema_state", {}).get("schema_id", None)
    #         cred_def = create_cred_def(schema_id, revocation_size=10)
    #         cred_def_id = cred_def.get("credential_definition_state", {}).get(
    #             "credential_definition_id", None
    #         )

    #         # Deactivate every second DID to generate some activity
    #         if idx == 1:
    #             deactivate_did(scid)
