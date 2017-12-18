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

def get_all_nodes():
    print orchestrator_endpoint
    r = requests.get("http://"+orchestrator_endpoint+"nodes", stream=True)
    return r.content

def get_all_images(nodeip):
    r = requests.get("http://"+nodeip+":6000/agent/v1/images", stream=True)
    print "http://"+nodeip+":6000/agent/v1/images"
    return r.content


def nodeimage_thread(nodeip):
    while True:
        gevent.sleep(1)
        try:

            imagelist = get_all_images(nodeip)
            # nodelist = "tests"
            socketio.emit('imagelist', {"data": imagelist},
                          namespace='/node')

        except ChunkedEncodingError as e:
            logger.debug("Connection Lost! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it LOST the CONNECTION '
                           'with the data source. Refresh or '
                           'try again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/node')
        except ConnectionError as e:
            logger.debug("Connection Error! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it CANNOT CONNECT to the '
                           'data source. Refresh or try '
                           'again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/node'
            )

def get_all_devices(nodeip):
    r = requests.get("http://"+nodeip+":6000/agent/v1/device_templates", stream=True)
    print "http://"+nodeip+":6000/agent/v1/device_templates"
    return r.content

def nodedevice_thread(nodeip):
    while True:
        gevent.sleep(1)
        try:

            devicelist = get_all_devices(nodeip)
            socketio.emit('devicelist', {"data": devicelist},
                          namespace='/node')

        except ChunkedEncodingError as e:
            logger.debug("Connection Lost! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it LOST the CONNECTION '
                           'with the data source. Refresh or '
                           'try again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/node')
        except ConnectionError as e:
            logger.debug("Connection Error! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it CANNOT CONNECT to the '
                           'data source. Refresh or try '
                           'again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/node'
            )


def nodedeviceimage_thread(nodeip):
    while True:
        gevent.sleep(1)
        try:
            nodelist = get_all_nodes()
            devicelist = get_all_devices(nodeip)
            imagelist = get_all_images(nodeip)
            socketio.emit('deviceimagelist', {"nodelist":nodelist,"devicelist": devicelist,"imagelist":imagelist},
                          namespace='/node')

        except ChunkedEncodingError as e:
            logger.debug("Connection Lost! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it LOST the CONNECTION '
                           'with the data source. Refresh or '
                           'try again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/node')
        except ConnectionError as e:
            logger.debug("Connection Error! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it CANNOT CONNECT to the '
                           'data source. Refresh or try '
                           'again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/node'
            )


@socketio.on('connect', namespace='/node')
def test_connect():
    logger.debug("Connected to Receive image Data!")
    logger.info("Connected to Receive image Data!")
    print "hello node websocket connected"
    # imagelist = get_all_images()
    # socketio.emit('imagelist', {"data": imagelist},namespace='/node')



@socketio.on('disconnect', namespace="/node")
def test_connect():
    print "disconnected"
    logger.debug("Disconnected!")


@socketio.on('monitor_image', namespace="/node")
def stream_image(json):
    node = loads(str(json))
    # print node
    # print type(node)
    node_ip = node['nodeip']
    print node_ip
    image_monitoring_thread = socketio.start_background_task(target=nodeimage_thread(node_ip))
    # test = get_all_images(node_ip)
    # print test, type(test)
    print "hello monitoring node images status"
    socketio.emit('control', {'data': 'Monitoring Image Stream started'},
                  namespace='/node')

@socketio.on('monitor_devices', namespace="/node")
def stream_devices(json):
    node = loads(str(json))
    node_ip = node['nodeip']
    device_monitoring_thread = socketio.start_background_task(target=nodedevice_thread(node_ip))
    test = get_all_images(node_ip)
    print test, type(test)
    print "hello monitoring node devices status"
    socketio.emit('control', {'data': 'Monitoring device Stream started'},
                  namespace='/node')


@socketio.on('monitor_devices_images', namespace="/node")
def stream_devices_images(json):
    node = loads(str(json))
    node_ip = node['nodeip']
    device_monitoring_thread = socketio.start_background_task(target=nodedeviceimage_thread(node_ip))
    # test = get_all_images(node_ip)
    # print test, type(test)
    print "hello monitoring node devices status"
    socketio.emit('control', {'data': 'Monitoring device Stream started'},
                  namespace='/node')
