from docker import APIClient

CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5

#High level API
#client = docker.from_env(version="auto")
##Low Level API
#cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

class PrimaryManager():
    def __init__(self, manager_name="",advertise_addrs=""):
        """
           :type manager_name : str | unicode
           :type advertise_addrs : str | unicode
           :param manager_name    :
           :param advertise_addrs  :
           :param args:
           :param kw:
         """
        self._node_ip = ""
        self._node_id = ""
        self._manager_name = manager_name
        self._advertise_addr = advertise_addrs
        self._join_token = ""
        #print self._advertise_addr
        swarm_created = self._docker_create_swarm()

    @property
    def advertiseaddr(self):
        return self._advertise_addr

    @property
    def manager_name(self):
        return self._manager_name

    @property
    def join_token(self):
        return self._join_token

    @property
    def json(self):
        return {
            "node_id": self._node_id,
            "manager_name": self._manager_name,
            "advertise_addr": self._advertise_addr
        }

    def __del__(self):
        self.destroy()

    def create(self, name, image_data):
        return self._docker_create_swarm()

    def destroy(self):
        return self._docker_destroy_swarm()

    def _docker_create_swarm(self):
        client = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        try:
            # s = client.swarm.init(
            #     advertise_addr=self._advertise_addr+':2377', listen_addr=self._advertise_addr+':2377',
            #     force_new_cluster=False, snapshot_interval=5000,
            #     log_entries_for_slow_followers=1200
            # )

            s = client.init_swarm(advertise_addr=self._advertise_addr+':2377', listen_addr=self._advertise_addr+':2377')
            print 'swarm created with manager: ', self._manager_name
            nodeinformation = client.info()
            self._node_id = nodeinformation['Swarm']['NodeID']
            # print self._node_id

            swarm_config = client.inspect_swarm()
            self._join_token = swarm_config['JoinTokens']['Worker']
            print self._join_token

            return True
                # TODO: the returned string actually holds (also) the ID
        except Exception as e:
            print "Printing exception here: " + str(e)
            return False

    def _docker_destroy_swarm(self):
        client = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        try:
            s = client.leave_swarm(force=True)
                #cli.load_image(data=image_data)
            if s is True:
                print 'swarm deleted with PrimaryManager: ', self.manager_name
                return True
            # TODO: the returned string actually holds (also) the ID
        except Exception as e:
            print e
            print "can not delete swarm: " + str(self.manager_name)
            return False


class Manager():
    def __init__(self, manager_name="", advertise_addr ="",
                 *args, **kw):
        """
        :type manager_name : str | unicode
        :type advertise_addr : str | unicode
        :param manager_name    :
        :param advertise_addr  :
        :param args:
        :param kw:
        """
        self._manager_name = manager_name
        self._advertise_addr = advertise_addr
        self._docker_create_swarm(advertise_addr)

    @property
    def ADDR(self):  # todo: this should not be Uppercase
        return self._advertise_addr

    @property
    def manager_name(self):
        return self._manager_name
    '''
    @property
    def deletable(self):
        # returns true if no container_templates is using the docker image
        return self._deletable and not ContainerTmpl.is_image_used(self.ID)
    '''
    @property
    def json(self):
        return {
            "manager_name": self._manager_name,
            "advertise_addr": self._advertise_addr,
        }

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "manager_name": {"type": "string"},
                "advertise_addr": {"type": "string"},
            }
        }
    def join(self, name, image_data):
        return self._docker_join_swarm()

    def destroy(self):
        return self._docker_leave_swarm()

    def _docker_leave_swarm(self):
        try:
            s = client.swarm.leave(force=True)
            # cli.load_image(data=image_data)
            if s is True:
                print 'manager is leaving swarm ', self.manager_name
                return True
                # TODO: the returned string actually holds (also) the ID
        except Exception as e:
            print e
            print "can not delete swarm: " + str(self.manager_name)
            return False




