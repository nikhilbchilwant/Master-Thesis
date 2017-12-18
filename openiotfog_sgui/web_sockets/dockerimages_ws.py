import gevent
import logging

from requests.exceptions import ChunkedEncodingError, ConnectionError

import requests, subprocess
from json import loads
import traceback


from . import socketio
from . import image_registry

infra_nodes = {}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_all_images():
    print image_registry

    r = requests.get("https://"+image_registry+"/v2/_catalog", verify=False)
    # r = requests.get('https://10.42.0.1:5000/v2/_catalog', cert=('/home/saiful/cert/domain.crt', '/home/saiful/cert/path/domain.key'))

    return r.content


def images_thread():
    while True:
        gevent.sleep(1)
        # socketio.sleep(2)
        try:
            # for line in get_all_nodes():
            #     logger.debug("To emit: {}".format(line))
            imageslist = get_all_images()
            # nodelist = "tests"
            socketio.emit('imageslist', {"data": imageslist},
                          namespace='/images')

        except ChunkedEncodingError as e:
            logger.debug("Connection Lost! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it LOST the CONNECTION '
                           'with the data source. Refresh or '
                           'try again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/images')
        except ConnectionError as e:
            logger.debug("Connection Error! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it CANNOT CONNECT to the '
                           'data source. Refresh or try '
                           'again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/images'
            )

@socketio.on('connect', namespace='/images')
def test_connect():
    logger.debug("Connected to Receive images Data!")
    logger.info("Connected to Receive images Data!")
    # print "Image client connected"
    imageslist = get_all_images()
    # nodelist = "tests"
    socketio.emit('imageslist', {"data": imageslist},
                  namespace='/images')
    # infra_monitoring_thread = socketio.start_background_task(target=infrastructure_thread)


@socketio.on('disconnect', namespace="/images")
def test_connect():
    print "Image client disconnected"
    logger.debug("Disconnected!")


@socketio.on('monitor_images', namespace="/images")
def _stream(json):
    node = loads(str(json))
    node_id = node['node']
    infra_monitoring_thread = socketio.start_background_task(target=images_thread)

    print "hello monitoring Images"
    socketio.emit('control', {'data': 'Monitoring infra Stream started'},
                  namespace='/images')
