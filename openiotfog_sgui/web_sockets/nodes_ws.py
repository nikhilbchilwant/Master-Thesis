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
    # r = requests.get("http://10.42.0.1:5001/openiotfogorc/v1/nodes",
    #                  params={'interval': '1'}, stream=True)
    print orchestrator_endpoint
    r = requests.get("http://"+orchestrator_endpoint+"nodes", stream=True)

    # lines = r.iter_lines()
    # for line in lines:
    #     print line
    #     yield line
    return r.content


def infrastructure_thread():
    while True:
        gevent.sleep(2)
        # socketio.sleep(2)
        try:
            # for line in get_all_nodes():
            #     logger.debug("To emit: {}".format(line))
            nodelist = get_all_nodes()
            # nodelist = "tests"
            socketio.emit('nodelist', {"data": nodelist},
                          namespace='/nodes')

        except ChunkedEncodingError as e:
            logger.debug("Connection Lost! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it LOST the CONNECTION '
                           'with the data source. Refresh or '
                           'try again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/nodes')
        except ConnectionError as e:
            logger.debug("Connection Error! {}".format(e.message))
            socketio.emit('error', {
                'message': 'An Internal Error in the Server Occurred. '
                           'Looks like that it CANNOT CONNECT to the '
                           'data source. Refresh or try '
                           'again later!<p/>',
                'stacktrace': traceback.format_exc()},
                          namespace='/nodes'
            )


#
# @socketio.on('connect', namespace='/test')
# def test_connect():
#     # need visibility of the global thread object
#     global thread
#     print('Client connected')



@socketio.on('connect', namespace='/nodes')
def test_connect():
    logger.debug("Connected to Receive nodes Data!")
    logger.info("Connected to Receive nodes Data!")
    # print "hello connected"
    nodelist = get_all_nodes()
    # nodelist = "tests"
    socketio.emit('nodelist', {"data": nodelist},
                  namespace='/nodes')
    # infra_monitoring_thread = socketio.start_background_task(target=infrastructure_thread)


@socketio.on('disconnect', namespace="/nodes")
def test_connect():
    print "disconnected"
    logger.debug("Disconnected!")


@socketio.on('monitor_nodes', namespace="/nodes")
def _stream(json):
    node = loads(str(json))
    node_id = node['node']
    infra_monitoring_thread = socketio.start_background_task(target=infrastructure_thread)

    print "hello monitoring infra"
    socketio.emit('control', {'data': 'Monitoring infra Stream started'},
                  namespace='/nodes')
