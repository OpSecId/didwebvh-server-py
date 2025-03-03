from app.utils import id_to_url, demo_id, id_to_resolver_link, hash
from app.services import AgentController, AskarStorage
import uuid
from config import Config

agent = AgentController()
askar = AskarStorage()

async def provision_demo():
    instance_id = hash(str(uuid.uuid4()))
    invitation = agent.create_oob_connection(instance_id)
    connection = agent.get_connection_from_alias(instance_id)
    connection_id = connection.get('connection_id')
    invitation["short_url"] = (
        f"{Config.ENDPOINT}/exchange/{connection_id}"
    )
    
    await askar.store(
            "exchange", connection_id, invitation["invitation"]
        )
    demo = await askar.fetch("demo", demo_id(Config.DEMO))
    demo = demo | {
        "status_size": Config.DEMO.get('size'),
        "invitation": invitation,
        "connection": connection,
        "instance_id": instance_id,
        "schema_url": id_to_resolver_link(demo["schema_id"]),
        "cred_def_url": id_to_resolver_link(demo["cred_def_id"]),
        "rev_def_url": id_to_resolver_link(demo["rev_def_id"]),
        "agent": {
            "label": Config.DEMO.get("issuer"),
            "endpoint": Config.AGENT_ADMIN_ENDPOINT,
        }
    }
    return demo

def sync_connection(client_id):
    connection = agent.get_connection(client_id)
    connection['hash'] = hash(
        connection.get("their_label")
        or connection.get("connection_id")
    )
    return connection

async def sync_demo(connection_id):
    demo = await askar.fetch('demo', connection_id)
    cred_ex_id = await askar.fetch('cred_ex_id', connection_id)
    pres_ex_id = await askar.fetch('pres_ex_id', connection_id)
    
    demo['issuance'] = {}
    demo['presentation'] = {}
    demo['rev_def_id'] = agent.get_active_registry(demo['cred_def_id'])
    demo['rev_def_url'] = id_to_resolver_link(demo['rev_def_id'])
    
    if cred_ex_id:
        offer = agent.verify_offer(demo.get('cred_ex_id'))
        demo['issuance'] = {
            'state': offer.get('state')
        }
    if pres_ex_id:
        presentation = agent.verify_presentation(demo.get('pres_ex_id'))
        demo['presentation'] = {
            'state': presentation.get('state'),
            'verified': presentation.get('verified')
        }
    return demo

async def sync_demo_state(connection_id):
    demo = await askar.fetch('demo', connection_id)
    
    state = {}
    state['connection'] = agent.get_connection(connection_id)
    state['connection']['hash'] = hash(
        state['connection'].get("their_label")
        or connection_id
    )
    
    cred_ex_id = await askar.fetch('cred_ex_id', connection_id)
    pres_ex_id = await askar.fetch('pres_ex_id', connection_id)
    if cred_ex_id is None:
        state['cred_ex'] = {'state': None}
    elif cred_ex_id == 'deleted':
        state['cred_ex'] = {'state': 'deleted'}
    else:
        state['cred_ex'] = agent.verify_offer(cred_ex_id)

    if pres_ex_id is None:
        state['pres_ex'] = {'state': None}
    elif pres_ex_id == 'deleted':
        state['pres_ex'] = {'state': 'deleted'}
    else:
        state['pres_ex'] = agent.verify_presentation(pres_ex_id)
        
    status_list = agent.get_latest_sl(demo.get('cred_def_id'))
    state['status_widget'] = {
        'html': ''
    }
    for bit in status_list:
        if bit == 0:
            state['status_widget']['html'] += '<div class="tracking-block bg-success" data-bs-toggle="tooltip" data-bs-placement="top" title="ok"></div>\n'
        elif bit == 1:
            state['status_widget']['html'] += '<div class="tracking-block bg-danger" data-bs-toggle="tooltip" data-bs-placement="top" title="revoked"></div>\n'
        else:
            state['status_widget']['html'] += '<div class="tracking-block bg-warning" data-bs-toggle="tooltip" data-bs-placement="top" title="unknown"></div>\n'
    return state

def update_chat(connection_id):
    chat_log = []
    # chat_log.append({
    #     'connection_id': connection_id,
    #     'content': 'Hi',
    #     'timestamp': '02-02-12T00:00:00Z',
    #     'author_hash': hash('My label'),
    #     'author': 'My label',
    #     'state': 'sent',
    # })
    # chat_log.append({
    #     'connection_id': connection_id,
    #     'content': 'Hello',
    #     'timestamp': '02-02-12T00:10:00Z',
    #     'author_hash': hash('Their label'),
    #     'author': 'Their label',
    #     'state': 'recieved',
    # })
    return chat_log
    