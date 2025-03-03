from typing import Dict, List, Union


class Interval():
    from_timestamp: str = ''
    to_timestamp: str = ''

class Request():
    attributes: List[str] = []
    predicate: List[Union[str, int]] = []
    interval: Interval = {}

class Credential():
    id: str = ''
    name: str = ''
    version: str = ''
    schema_id: str = ''
    registry_id: str = ''
    preview: Dict[str, str] = {}
    request: Request = {}

class Issuer():
    id: str = ''
    name: str = ''
    image: str = ''

class Invitation():
    id: str = ''
    url: str = ''
    short_url: str = ''
    content: dict = ''

class Connection():
    id: str = ''
    label: str = ''
    state: str = ''

class CredentialExchange():
    id: str = ''
    state: str = ''
    connection_id: str = ''

class PresentationExchange():
    id: str = ''
    state: str = ''
    connection_id: str = ''
    verified: bool = ''

class Message():
    connection_id: str = ''
    content: str = ''
    timestamp: str = ''
    author_hash: str = ''
    author: str = ''
    state: str = ''

class DemoState():
    name: str = ''
    issuer: Issuer = ''
    credential: Credential = ''
    connection: Connection = ''
    invitation: Invitation = ''
    cred_ex: CredentialExchange = ''
    pres_ex: PresentationExchange = ''
    msg_log: List[Message] = ''