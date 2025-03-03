from flask import Blueprint, render_template, url_for, current_app, session, redirect, jsonify
import asyncio
from app.services import AskarStorage

bp = Blueprint("webhooks", __name__)


# @bp.before_request
# def before_request_callback():
#     if "client_id" not in session:
#         return redirect(url_for('auth.index'))


@bp.route("/webhooks/topics/<topic>", methods=["POST"])
def webhook_topic(topic: str):
    askar = AskarStorage()
    if topic == 'oob_invitation':
        invitation = {}
        invitation_id = ''
        invitation_url = ''
    elif topic == 'connections':
        connection_id = ''
        their_label = ''
        state = ''
    elif topic == 'ping':
        connection_id = ''
    elif topic == 'basicmessages':
        connection_id = ''
    elif topic == 'issue_credential':
        credential_exchange_id = ''
        connection_id = ''
    elif topic == 'issuer_cred_rev':
        state = ''
        rev_reg_id = ''
        updated_at = ''
    elif topic == 'issue_credential_v2_0':
        cred_ex_id = ''
        conn_id = ''
    elif topic == 'present_proof':
        presentation_exchange_id = ''
        connection_id = ''
        state = ''
    elif topic == 'revocation_registry':
        state = ''
        revoc_reg_id = ''
        cred_def_id = ''
    # asyncio.run(sync_wallet(session.get('client_id')))
    return {}, 200