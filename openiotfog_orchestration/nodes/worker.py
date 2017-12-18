import datetime
from docker import APIClient

CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5

class FogNode():
    def __init__(self, nodeip="",nodeid="",nodehostname = "",nodestatus= "",nodelayer=""):
        """
           :type _node_ip : str | unicode
           :type _node_id : str | unicode
           :param _node_ip    :
           :param _node_id  :
           :param args:
           :param kw:
         """

        self._node_ip = nodeip
        self._node_id = nodeid
        self._node_hostname = nodehostname
        self._node_label = ""
        self._node_status = nodestatus
        self._node_layer = nodelayer
        self._node_starttime = datetime.datetime.now()

        #TODO: ADD Device_List
        #self._devices = [] #list of device object


        #TODO: ADD Image List
        #self._images = [] list of image object

        # # json-schema here
        # expected_json = {
        #     'ip': {
        #         'type': 'string',
        #         'required': True
        #     },
        #     'node_id': {
        #         'type': 'string',
        #         'required': False
        #     },
        #     'label': {
        #         'type': 'string',
        #         'required': False
        #     }
        #     'status': {
        #         'type': 'string',
        #         'allowed': ['Up', 'Down', 'Overloaded'],
        #         'required': False
        #     },
        #     'layer': {
        #         'type': 'string',
        #         'allowed': ['Fog', 'Edge'],
        #         'required': False
        #     },
        #     'start_time': {
        #         'type': 'datetime',
        #         'required': False
        #     }

        # }

    @property
    def node_ip(self):
        return self._node_ip

    @property
    def node_id(self):
        return self._node_id

    @property
    def node_hostname(self):
        return self._node_hostname

    @property
    def node_label(self):
        return self._node_label

    @property
    def node_status(self):
        return self._node_status

    @property
    def node_layer(self):
        return self._node_layer

    @property
    def node_starttime(self):
        return str(self._node_starttime)

    #Set
    def set_node_label(self, value=""):
        self._node_label = value

    #Set hostname
    def set_node_hostname(self, hostname=""):
        self._node_hostname = hostname


    @property
    def json(self):
        return {
            "node_ip": self.node_ip,
            "node_id": self.node_id,
            "node_hostname": self.node_hostname,
            "node_label": self.node_label,
            "node_status": self.node_status,
            "node_layer" : self.node_layer,
            "node_starttime" : self.node_starttime
        }

    def __del__(self):
        del self


