from flask_socketio import SocketIO

from gevent import monkey
monkey.patch_all()


from openiotfog_sgui.openiotfog_orc_gui import image_registry,orchestrator_endpoint

socketio = SocketIO(async_mode="gevent")


from devices_ws import *
from dockerimages_ws import *
from node_ws import *
from nodes_ws import *
from swarmservice_ws import *