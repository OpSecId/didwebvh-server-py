import os
import uuid
import requests
from app.services import AskarStorage
from app.utils import id_to_url, demo_id, url_encode
from config import Config
import time
import pyjokes
from random import randint


class AgentControllerError(Exception):
    """Generic AgentControllerError Error."""

class AgentController:
    def __init__(self):
        self.label = Config.DEMO.get('issuer')
        self.webvh_server = os.getenv('DIDWEBVH_SERVER')
        self.did_domain = self.webvh_server.split("://")[-1]
        self.did_namespace = "demo"
        self.did_identifier = str(uuid.uuid4())
        self.did_web = f'did:web:{self.did_domain}:{self.did_namespace}:{self.did_identifier}'
        self.witness_key = os.getenv('DIDWEBVH_WITNESS_KEY')
        self.endpoint = os.getenv('AGENT_ADMIN_ENDPOINT')
        # self.headers = {
        #     'X-API-KEY': os.getenv('AGENT_ADMIN_API_KEY')
        # }
        
    async def provision(self):
        demo = await AskarStorage().fetch('demo', demo_id(Config.DEMO))
        if not demo:
            await AskarStorage().store(
                'demo',
                demo_id(Config.DEMO),
                Config.DEMO | self.setup_demo()
            )
        
    def configure_did_webvh(self):
        requests.post(
            f'{self.endpoint}/did/webvh/configuration',
            # headers=self.headers,
            json={
                'server_url': self.webvh_server,
                'witness_key': self.witness_key,
                'witness': True
            }
        )
        return self.create_did_webvh(self.did_namespace, self.did_identifier).get('id')
        
    def create_did_webvh(self, namespace, identifier):
        print('Creating DID')
        try:
            r = requests.post(
                f'{self.endpoint}/did/webvh/create',
                # headers=self.headers,
                json={
                    'options': {
                        'identifier': identifier,
                        'namespace': namespace,
                        'parameters': {
                            'portable': False,
                            'prerotation': False
                        }
                    }
                }
            )
            return r.json()
        except:
            raise AgentControllerError('Error creating DID.')
        
    def create_schema(self, schema):
        print('Creating Schema')
        try:
            r = requests.post(
                f'{self.endpoint}/anoncreds/schema',
                # headers=self.headers,
                json={
                    'options': {},
                    'schema': schema
                }
            )
            return r.json()['schema_state']['schema_id']
        except:
            pass
        
    def create_cred_def(self, cred_def:dict, rev_size:int=0):
        print('Credential Definition')
        try:
            r = requests.post(
                f'{self.endpoint}/anoncreds/credential-definition',
                # headers=self.headers,
                json={
                    'options': {
                        'support_revocation': True if rev_size > 0 else False, 
                        'revocation_registry_size': rev_size
                    },
                    'credential_definition': cred_def
                }
            )
            return r.json()['credential_definition_state']['credential_definition_id']
        except:
            pass
        
    def create_rev_def(self, rev_def:dict):
        try:
            r = requests.post(
                f'{self.endpoint}/anoncreds/revocation-registry-definition',
                # headers=self.headers,
                json={
                    'options': {},
                    'revocation_registry_definition': rev_def
                }
            )
            return r.json()['revocation_registry_definition_state']['revocation_registry_definition_id']
        except:
            pass
        
    def create_rev_list(self, rev_def_id:str):
        r = requests.post(
            f'{self.endpoint}/anoncreds/revocation-list',
            # headers=self.headers,
            json={
                'options': {},
                'rev_reg_def_id': rev_def_id
            }
        )
        
    def setup_demo(self):
        print('Setting up AnonCreds Demo')
        issuer_id = self.configure_did_webvh()
        schema_id = self.create_schema(
            {
                'issuerId': issuer_id,
                'name': Config.DEMO.get('name'),
                'version': Config.DEMO.get('version'),
                'attrNames':[attribute for attribute in Config.DEMO.get('preview')],
            }
        )
        cred_def_id = self.create_cred_def(
            {
                'issuerId': issuer_id,
                'schemaId': schema_id,
                'tag': Config.DEMO.get('name'),
            },
            Config.DEMO.get('size')
        )
        rev_def_id = self.get_active_registry(cred_def_id)
        # rev_def_id = self.create_rev_def(
        #     {
        #         'credDefId': cred_def_id,
        #         'issuerId': issuer,
        #         'maxCredNum': Config.DEMO.get('size'),
        #         'tag': '0'
        #     }
        # )
        # self.create_rev_list(rev_def_id)
        return {
            'issuer_id': issuer_id,
            'schema_id': schema_id,
            'cred_def_id': cred_def_id,
            'rev_def_id': rev_def_id,
        }
        
        
        
    def get_active_registry(self, cred_def_id):
        r = requests.get(f'{self.endpoint}/anoncreds/revocation/active-registry/{url_encode(cred_def_id)}')
        return r.json()['result']['revoc_reg_id']
        
    def bind_key(self, verification_method, public_key_multibase):
        r = requests.put(
            f'{self.endpoint}/wallet/keys',
            json={
                'kid': verification_method,
                'multikey': public_key_multibase
            }
        )
        
    
    def offer_credential(self, alias, cred_def_id, attributes):
        cred_offer = self.create_cred_offer(cred_def_id, attributes)
        invitation = self.create_oob_inv(
            alias=alias, 
            cred_ex_id=cred_offer['cred_ex_id'], 
            handshake=True
        )
        return cred_offer['cred_ex_id'], invitation
    
    def create_cred_offer(self, cred_def_id, attributes):
        endpoint = f'{self.endpoint}/issue-credential-2.0/create'
        cred_offer = {
            'auto_remove': False,
            'credential_preview': {
                "@type": "issue-credential/2.0/credential-preview",
                "attributes": [
                    {
                        "name": attribute,
                        "value": attributes[attribute]
                    } for attribute in attributes
                ]
            },
            'filter': {
                'anoncreds': {
                    'cred_def_id': cred_def_id,
                }
            }
        }
        r = requests.post(
            endpoint,
            # headers=self.headers,
            json=cred_offer
        )
        print(r.text)
        try:
            return r.json()
        except:
            raise AgentControllerError('No exchange')
    
    def request_presentation(self, name, cred_def_id, attributes):
        pres_req = self.create_pres_req(name, cred_def_id, attributes)
        invitation = self.create_oob_inv(
            pres_ex_id=pres_req['pres_ex_id'], 
            handshake=False
        )
        return pres_req['pres_ex_id'], invitation
        
    def create_pres_req(self, name, cred_def_id, attributes):
        endpoint = f'{self.endpoint}/present-proof-2.0/create-request'
        pres_req = {
            'auto_remove': False,
            'auto_verify': True,
            'presentation_request': {
                'anoncreds': {
                    'name': name,
                    'version': Config.DEMO.get('version'),
                    'nonce': str(randint(1, 99999999)),
                    'requested_attributes': {
                        'requestedAttributes': {
                            'names': attributes,
                            'restrictions':[
                                {
                                    'cred_def_id': cred_def_id
                                }
                            ]
                        }
                    },
                    'requested_predicates': {}
                }
            }
        }
        r = requests.post(
            endpoint,
            # headers=self.headers,
            json=pres_req
        )
        try:
            return r.json()
        except:
            raise AgentControllerError('No exchange')
    
    def create_oob_inv(self, alias=None, cred_ex_id=None, pres_ex_id=None, handshake=False):
        endpoint = f'{self.endpoint}/out-of-band/create-invitation?auto_accept=true'
        invitation = {
            "my_label": self.label,
            "attachments": [],
            "handshake_protocols": [],
        }
        if pres_ex_id:
            invitation['attachments'].append({
                "id":   pres_ex_id,
                "type": "present-proof"
            })
        if cred_ex_id:
            invitation['attachments'].append({
                "id":   cred_ex_id,
                "type": "credential-offer"
            })
        if handshake:
            invitation['alias'] = alias
            invitation['handshake_protocols'].append(
                "https://didcomm.org/didexchange/1.0"
            )
        r = requests.post(
            endpoint,
            # headers=self.headers,
            json=invitation
        )
        try:
            return r.json()['invitation']
        except:
            raise AgentControllerError('No invitation')
        
    def verify_presentation(self, pres_ex_id):
        endpoint = f'{self.endpoint}/present-proof-2.0/records/{pres_ex_id}'
        r = requests.get(
            endpoint,
            # headers=self.headers
        )
        try:
            return r.json()
        except:
            raise AgentControllerError('No exchange')
        
    def verify_offer(self, cred_ex_id):
        endpoint = f'{self.endpoint}/issue-credential-2.0/records/{cred_ex_id}'
        r = requests.get(
            endpoint,
            # headers=self.headers
        )
        try:
            return r.json().get('cred_ex_record')
        except:
            raise AgentControllerError('No exchange')

    
    def create_oob_connection(self, client_id):
        endpoint = f'{self.endpoint}/out-of-band/create-invitation?auto_accept=true'
        invitation = {
            "alias": client_id,
            "my_label": self.label,
            "handshake_protocols": ["https://didcomm.org/didexchange/1.0"],
        }
        r = requests.post(
            endpoint,
            json=invitation
        )
        try:
            return r.json()
        except:
            raise AgentControllerError('No invitation')
    
    def get_connection(self, connection_id):
        endpoint = f'{self.endpoint}/connections/{connection_id}'
        r = requests.get(
            endpoint
        )
        try:
            return r.json()
        except:
            raise AgentControllerError('No connection')
    
    def get_connection_from_alias(self, client_id):
        endpoint = f'{self.endpoint}/connections?alias={client_id}'
        r = requests.get(
            endpoint
        )
        try:
            return r.json()['results'][0]
        except:
            raise AgentControllerError('No connection')
    
    def send_offer(self, connection_id, cred_def_id, attributes):
        endpoint = f'{self.endpoint}/issue-credential-2.0/send'
        cred_offer = {
            'auto_remove': False,
            'connection_id': connection_id,
            'credential_preview': {
                "@type": "issue-credential/2.0/credential-preview",
                "attributes": [
                    {
                        "name": attribute,
                        "value": attributes[attribute]
                    } for attribute in attributes
                ]
            },
            'filter': {
                'anoncreds': {
                    'cred_def_id': cred_def_id,
                }
            }
        }
        r = requests.post(
            endpoint,
            json=cred_offer
        )
        # print(r.text)
        try:
            return r.json()
        except:
            raise AgentControllerError('No offer')
            
    
    def get_latest_sl(self, cred_def_id):
        rev_def_id = self.get_registry(cred_def_id)['result']['revoc_reg_id']
        status_list = self.get_status_list(rev_def_id)['content']['revocationList']
        return status_list
            
    
    def get_registry(self, cred_def_id):
        r = requests.get(f'{self.endpoint}/anoncreds/revocation/active-registry/{url_encode(cred_def_id)}')
        return r.json()
            
    
    def get_status_list(self, rev_def_id):
        r = requests.get(id_to_url(rev_def_id))
        status_list_id = r.json()['links'][-1]['id']
        r = requests.get(id_to_url(status_list_id))
        return r.json()
    
    def send_request(self, connection_id, name, cred_def_id, attributes, predicate, timestamp):
        endpoint = f'{self.endpoint}/present-proof-2.0/send-request'
        pres_req = {
            'auto_remove': False,
            'auto_verify': True,
            'connection_id': connection_id,
            'presentation_request': {
                'anoncreds': {
                    'name': name,
                    'version': Config.DEMO.get('version'),
                    'nonce': str(randint(1, 99999999)),
                    'requested_attributes': {
                        'requestedAttributes': {
                            'names': attributes,
                            'restrictions':[
                                {
                                    'cred_def_id': cred_def_id
                                }
                            ]
                        }
                    } if attributes else {},
                    'requested_predicates': {
                        'requestedPredicate': {
                            'name': predicate[0],
                            'p_type': predicate[1],
                            'p_value': predicate[2],
                            'restrictions':[
                                {
                                    'cred_def_id': cred_def_id
                                }
                            ]
                        }
                    } if predicate else {},
                    'non_revoked': {
                        'from': timestamp,
                        'to': timestamp
                    } if timestamp else {}
                }
            }
        }
        r = requests.post(
            endpoint,
            json=pres_req
        )
        print(r.text)
        try:
            return r.json()
        except:
            raise AgentControllerError('No request')
    
    def revoke_credential(self, cred_ex_id:str, publish:bool=True):
        endpoint = f'{self.endpoint}/anoncreds/revocation/revoke'
        r = requests.post(
            endpoint,
            json={
                'cred_ex_id': cred_ex_id,
                'publish': publish
            }
        )
        try:
            return r.json()
        except:
            raise AgentControllerError('No revocation')
    
    def send_message(self, connection_id, message=None):
        endpoint = f'{self.endpoint}/connections/{connection_id}/send-message'
        requests.post(
            endpoint,
            json={
                'content': message or pyjokes.get_joke()
            }
        )