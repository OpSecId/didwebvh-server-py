from flask import Blueprint, render_template, url_for, current_app, session, redirect, jsonify
import time
from asyncio import run as await_
from app.services import AgentController, AskarStorage
from config import Config

bp = Blueprint("exchanges", __name__)

agent = AgentController()
askar = AskarStorage()

@bp.before_request
def before_request_callback():
    if "connection_id" not in session:
        return {}, 401

@bp.route("/exchanges/<exchange_id>")
def exchanges(exchange_id: str):
    exchange = await_(AskarStorage().fetch('exchange', exchange_id))
    if not exchange:
        return {}, 404
    return exchange

@bp.route("/offer")
def credential_offer():
    connection_id = session.get('connection_id')
    await_(askar.update('pres_ex_id', connection_id, 'deleted'))
    await_(askar.update('cred_ex_id', connection_id, None))
    demo = await_(askar.fetch('demo', connection_id))
    try:
        session['cred_ex_id'] = agent.send_offer(
            session["connection_id"],
            demo.get("cred_def_id"),
            demo.get("preview"),
        ).get("cred_ex_id")
        await_(askar.update('cred_ex_id', connection_id, session['cred_ex_id']))
    except:
        pass
    return redirect(url_for("index"))

@bp.route("/update")
def credential_update():
    connection_id = session.get('connection_id')
    await_(askar.update('pres_ex_id', connection_id, 'deleted'))
    cred_ex_id = await_(askar.fetch('cred_ex_id', connection_id))
    try:
        agent.revoke_credential(cred_ex_id)
    except:
        pass
    return redirect(url_for("index"))

@bp.route("/request")
def presentation_request():
    connection_id = session.get('connection_id')
    await_(askar.update('pres_ex_id', connection_id, None))
    demo = await_(askar.fetch('demo', connection_id))
    try:
        session['pres_ex_id'] = agent.send_request(
            connection_id,
            "Demo Presentation",
            demo.get("cred_def_id"),
            demo.get("request").get("attributes"),
            demo.get("request").get("predicate"),
            int(time.time()),
        ).get("pres_ex_id")
        await_(askar.update('pres_ex_id', connection_id, session['pres_ex_id']))
    except:
        pass
    return redirect(url_for("index"))

@bp.route("/message")
def send_message():
    agent.send_message(session["connection_id"])
    return redirect(url_for("index"))