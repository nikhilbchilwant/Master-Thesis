"""
This module contains code responsible for monitoring the Host resource loads.
"""
from flask import Response, request, Blueprint
from enum import Enum
from rrdtool import update, create, lastupdate

from gevent import monkey

import gevent
import datetime
import json
import psutil
import sys
import os

monkey.patch_all()

# Current Working Directory
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))
# DATABASE file
DATABASE_CPU = os.path.join(__location__,
                             'tests/cpu_data.rrd')
DATABASE_MEMORY = os.path.join(__location__,
                             'tests/memory_data.rrd')
DATABASE_STORAGE = os.path.join(__location__,
                             'tests/storage_data.rrd')
DATABASE_NETWORK = os.path.join(__location__,
                             'tests/network_data.rrd')
DATABASE_SENSORS = os.path.join(__location__,
                             'tests/sensors_data.rrd')

# files used in tests


sys.path.insert(0, os.path.abspath('..'))

monitoring_blueprint = Blueprint("monitoring", __name__,
                                 url_prefix="/monitoring/v0.1")


@monitoring_blueprint.route('/stream/cpu')
def stream_cpu_data():
    if hasattr(request.args, "interval"):
        interval = float(request.args.get("interval"))
    else:
        interval = 1

    def generate(interval=1):
        while True:
            t = gevent.spawn(retrieve_monitoring_data)
            t.join()
            yield t.value
            gevent.sleep(interval)
    return Response(generate(interval), content_type='text/plain')

@monitoring_blueprint.route('/datastream')
def stream_monitoring_data():
    if hasattr(request.args, "interval"):
        interval = float(request.args.get("interval"))
    else:
        interval = 1

    def generate(interval=1):
        while True:
            t = gevent.spawn(retrieve_monitoring_data)
            t.join()
            yield t.value
            gevent.sleep(interval)
    return Response(generate(interval), content_type='text/plain')


def start_database():
    create(DATABASE_CPU, "--step", "1", "--start", "N", "DS:cpu_percentage:GAUGE:10:U:U",
           "DS:cpu_system:GAUGE:10:U:U", "DS:cpu_user:GAUGE:10:U:U",
           "RRA:AVERAGE:0.1:1:24")
    create(DATABASE_MEMORY, "--step", "1", "--start", "N", "DS:used_memory:GAUGE:10:U:U",
           "DS:total_memory:GAUGE:10:U:U", "RRA:AVERAGE:0.1:1:24")
    create(DATABASE_STORAGE, "--step", "1", "--start", "N", "DS:used_storage:GAUGE:10:U:U",
           "DS:total_storage:GAUGE:10:U:U", "RRA:AVERAGE:0.1:1:24")
    create(DATABASE_NETWORK, "--step", "1", "--start", "N", "DS:network_tx:GAUGE:10:U:U",
           "DS:network_rx:GAUGE:10:U:U", "RRA:AVERAGE:0.1:1:24")
    create(DATABASE_SENSORS, "--step", "1", "--start", "N", "DS:battery:GAUGE:10:U:U",
           "DS:temperature:GAUGE:10:U:U", "RRA:AVERAGE:0.1:1:24")


def sense_monitoring_data():
    while True:
        cpu = psutil.cpu_times_percent()
        network = psutil.net_io_counters()
        monitoring_data = {
                               'cpu_total': cpu.user + cpu.system,
                               'cpu': cpu,
                               'memory': psutil.virtual_memory(),
                               'storage': [
                                   {'data': psutil.disk_usage('/'),
                                    'partition': '/'}
                               ],
                               'network': [
                                   {
                                       'interface': 'All',
                                       'Rx': network.bytes_recv,
                                       'Tx': network.bytes_sent
                                   }
                               ],
                               'sensors': {
                                   'battery': psutil.sensors_battery(),
                                   'temperature': psutil.sensors_temperatures()
                               }
                           }
        t = gevent.spawn(store_monitoring_data, monitoring_data)
        t.join()
        gevent.sleep(1)


def store_monitoring_data(data):
    # update(DATABASE_CPU, 'N:{0}:{1}:{2}'.format((data.get('cpu_total')),
    #                                             data.get('cpu').system, data.get('cpu').user))
    # update(DATABASE_MEMORY, 'N:{0}:{1}'.format(data.get('memory').used, data.get('memory').total))
    # update(DATABASE_STORAGE, 'N:{0}:{1}'.format(data.get('storage')[0].get('data').used,
    #                                             data.get('storage')[0].get('data').total))
    # update(DATABASE_NETWORK, 'N:{0}:{1}'.format(data.get('network')[0].get('Rx'),
    #                                             data.get('network')[0].get('Tx')))
    # update(DATABASE_SENSORS, 'N:{0}:{1}'.format(data.get('sensors').get('battery', -1).percent,
    #                                             data.get('sensors').get('temperatures', -1)))
    gevent.sleep()


def monitor():
    pass


def monitoring_data_stream():
    pass


def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError('Unknown type')


def retrieve_monitoring_data():
    cpu = lastupdate(DATABASE_CPU)
    memory = lastupdate(DATABASE_MEMORY)
    storage = lastupdate(DATABASE_STORAGE)
    network = lastupdate(DATABASE_NETWORK)
    sensors = lastupdate(DATABASE_SENSORS)
    result = {'cpu': cpu, 'memory': memory, 'storage': storage,
              'network': network, 'sensors': sensors}
    return "{}\n".format(json.dumps(result, default=datetime_handler))


class DatabaseManager:

    def __init__(self, metadata_file):
        with open(metadata_file) as metadata_file_dp:
            db_metadata = json.loads(metadata_file_dp.read())
            # print db_metadata
