import gevent
import logging

from requests.exceptions import ChunkedEncodingError, ConnectionError

import requests, subprocess
from json import loads
import traceback


from . import socketio
from . import orchestrator_endpoint

infra_nodes = {}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



def get_all_supported_devices():
    # print orchestrator_endpoint
    r = requests.get("http://"+orchestrator_endpoint+"devices", stream=True)
    return r.content


def devices_thread():
    while True:
        gevent.sleep(0.5)
        # socketio.sleep(2)
        try:
            deviceslist = get_all_supported_devices()
            # nodelist = "tests"
            socketio.emit('deviceslist', {"data": deviceslist},
                          namespace='/devices')

        except ChunkedEncodingError as e:
            logger.debug("Connection Lost! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it LOST the CONNECTION '
                           'with the data source. Refresh or '
                           'try again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/devices')
        except ConnectionError as e:
            logger.debug("Connection Error! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it CANNOT CONNECT to the '
                           'data source. Refresh or try '
                           'again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/devices'
            )

@socketio.on('connect', namespace='/devices')
def test_connect():
    logger.debug("Connected to Receive devices Data!")
    logger.info("Connected to Receive devices Data!")
    # print "hello connected"
    deviceslist = get_all_supported_devices()

    socketio.emit('deviceslist', {"data": deviceslist},
                  namespace='/devices')


@socketio.on('disconnect', namespace="/devices")
def test_connect():
    # print "disconnected"
    logger.debug("Disconnected!")


@socketio.on('monitor_device_templates', namespace="/devices")
def _stream(json):
    node = loads(str(json))
    node_id = node['node']
    infra_monitoring_thread = socketio.start_background_task(target=devices_thread)

    # print "supported devices"
    socketio.emit('control', {'data': 'Device templates data Stream started'},
                  namespace='/devices')
