from flask import Flask, current_app, render_template, session, redirect, url_for, request
from flask_cors import CORS
from flask_qrcode import QRcode
from flask_session import Session
from flask_avatars import Avatars
from config import Config
from asyncio import run as await_
import uuid
import json
import time
from app.routes.exchanges import bp as exchanges_bp
from app.routes.webhooks import bp as webhooks_bp
from app.services import AskarStorage, AgentController
from app.utils import id_to_url, demo_id, hash, fetch_resource, id_to_resolver_link
from app.operations import provision_demo, sync_connection, sync_demo, update_chat, sync_demo_state


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    @app.template_filter('ctime')
    def ctime(s):
        return time.ctime(s)
    
    @app.template_filter('dereference')
    def dereference(s):
        return id_to_url(s)
    
    @app.template_filter('resolve')
    def id_resolver(s):
        return id_to_resolver_link(s)

    CORS(app)
    QRcode(app)
    Session(app)
    Avatars(app)
    
    askar = AskarStorage()
    
    app.register_blueprint(exchanges_bp)
    app.register_blueprint(webhooks_bp)

    @app.before_request
    def before_request_callback():
        session["title"] = Config.APP_TITLE
        session["endpoint"] = Config.ENDPOINT
        session["agent"] = {
            "label": Config.DEMO.get("issuer"),
            "endpoint": Config.AGENT_ADMIN_ENDPOINT,
        }
        if not session.get('connection_id'):
            session.clear()
            session["demo"] = demo = await_(provision_demo())
            session["connection_id"] = demo['connection']['connection_id']
            await_(askar.store('demo', session["connection_id"], demo))
            await_(askar.store('cred_ex_id', session['connection_id'], None))
            await_(askar.store('pres_ex_id', session['connection_id'], None))

    @app.route("/")
    def index():
        return render_template("pages/index.jinja")

    @app.route("/restart")
    def restart():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/sync")
    def sync_state():
        if not session.get('connection_id'):
            return {}, 400
        state = await_(sync_demo_state(session.get('connection_id')))
        # current_app.logger.warning(state)
        return state, 200

    @app.route("/resource", methods=["GET", "POST"])
    def render_resource():
        resource_id = request.args.get('id')
        try:
            resource = fetch_resource(resource_id)
            resource_url = id_to_url(resource_id)
            return render_template("pages/resource.jinja", resource=resource, resource_url=resource_url)
        except:
            return {}, 404

    return app
