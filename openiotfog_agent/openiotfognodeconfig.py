import docker
import json
import netifaces as ni


# fognodeconfig contains the node information and the status as a Docker Swarm worker node.
# The methods provide functionality to add the node to a Docker Swarm Cluster and Remove from the Cluster

class fognodeconfig:

    def __init__(self, nodeip):
        self._remotemanager = []
        self._token = ""
        self._isManager = False
        self._nodeID = ""
        # Only IP is known from the node configuration. So, while creating Object IP should be provided. Other attributes will be set, when node join a Docker Swarm Cluster.
        self._nodeIP = nodeip             #ni.ifaddresses('em1')[2][0]['addr']
        self._nodehostname = ""
        self._label = ""



    @property
    def managers(self):
        return self._remotemanager

    @property
    def ismanagers(self):
        return self._isManager

    # returns the nodeID
    @property
    def nodeid(self):
        return self._nodeID

    # returns the nodeIP
    @property
    def nodeip(self):
        return self._nodeIP

    # returns the nodeHostname
    @property
    def nodehostname(self):
        return self._nodehostname

    # returns the node-label
    @property
    def label(self):
        return self._label


    @property
    def json(self):
        return {
            "managers": json.dumps(self._remotemanager),
            "Role_Manager": self._isManager,
            "NodeID": self._nodeID,
            "NodeIP": self._nodeIP,
            "Nodehostname": self._nodehostname,
            "Node_Label": self._label
        }


    #This method make this Node join a Swarm Cluster
    def swarm_cluter_join(self, remotemanager, token):
        client = docker.from_env()
        self._remotemanager.append(remotemanager)
        self._token = token
        try:
            client.swarm.join(self._remotemanager, self._token, self._nodeIP)
            self._nodeID = self._get_swarm_node_ID()
            self._nodehostname = self._get_swarm_node_hostname()
            return True
        except docker.errors.APIError as e:
            print "could not join swarm "+str(e)
        return False

    #This method make this Node leave a Swarm Cluster
    def swarm_cluster_leave(self):
        client = docker.from_env()
        res = client.swarm.leave()
        #print res
        if res:
            del self._remotemanager[:]
            self._token = ""
            self._nodeID = ""
            self._label = ""
            self._nodehostname = ""
            return True
        else:
            print "could not leave swarm"
            return False

    # retrieve nodeID from docker info
    def _get_swarm_node_ID(self):
        client = docker.from_env()
        responce = client.info()
        swarmconfig = responce['Swarm']
        for key, value in swarmconfig.items():
            if key == "NodeID":
                return value

    # retrieve nodehostname from docker info
    def _get_swarm_node_hostname(self):
        client = docker.from_env()
        responce = client.info()
        hostname = responce['Name']
        return hostname

    # retrieve node-role(manager/worker) from docker info
    def _get_swarm_node_is_Manager(self):
        client = docker.from_env()
        responce = client.info()
        swarmconfig = responce['Swarm']
        for key, value in swarmconfig.items():
            if key == "ControlAvailable":
                return value

    def _get_swarm_manager_address(self):
        client = docker.from_env()
        responce = client.info()
        swarmconfig = responce['Swarm']
        remotemanagerconfig =None
        for key, value in swarmconfig.items():
            if key == "RemoteManagers":
                remotemanagers = value
                if remotemanagers is None:
                    return ""
                #print type(remotemanagerconfig)
                remotemanagerconfig = remotemanagers[0]
        for key, value in remotemanagerconfig.items():
            print key, value
            if key == "Addr":
                return value

    def _set_swarm_manager_address(self):
        client = docker.from_env()
        responce = client.info()
        swarmconfig = responce['Swarm']
        remotemanagerconfig =None
        for key, value in swarmconfig.items():
            if key == "RemoteManagers":
                remotemanagers = value
                if remotemanagers is None:
                    return False
                #print type(remotemanagerconfig)
                remotemanagerconfig = remotemanagers[0]
        for key, value in remotemanagerconfig.items():
            print key, value
            if key == "Addr":
                self._remotemanager.append(value)
                return True


    def _get_all_swarm_config(self):
        client = docker.from_env()
        responce = client.info()
        swarmconfig = responce['Swarm']
        for key, value in swarmconfig.items():
            print key, value


    def _update_swarm_node_config(self):
        if len(self._remotemanager) == 0:
            self._remotemanager.append(self._get_swarm_manager_address())
        self._isManager = self._get_swarm_node_is_Manager()
        self._nodeID = self.get_swarm_node_ID()




#if __name__ == '__main__':
#    test = swarmnodeconfig()
#    a = test.json
#    print a
#    test.swarm_cluter_join("10.147.66.51:2377",'SWMTKN-1-48ktu2mw56khrli3lpoihgihwcfwsjoi9u3ug8gthtg4d488nh-b84ku93uc0sb0wstayl02yek5')
    #test._get_all_swarm_config()
    #test.show_swarm_node_config()
#    test.swarm_cluster_leave()
#    print ("node id : " + test.get_swarmconfig_node_ID())

