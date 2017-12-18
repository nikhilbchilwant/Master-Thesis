import json
import docker
from docker.types import ServiceMode
import time



class ApplicationService():
    def __init__(self, servicename="", nodehostname="", devicename="", imagename="", envvar=[]):
        """
           :type servicename : str | unicode
           :type serviceport : dictionary
           :type imagename : str | unicode
           :type envvar : str | unicode
           :param servicename    :
           :param serviceport  :
           :param imagename:
           :param envvar: "EP=http://192.168.1.115:8000"
        """
        self._serviceid = ""
        self._service_name = servicename
        self._nodehostname = nodehostname # which node to run the service
        self._device_name = devicename # which device to use for the service
        self._image = imagename # which image to use
        self._environment_variables = envvar
        self.running = False

    # service ID is set when the service is started and running = True
    @property
    def serviceid(self):
        return self._serviceid

    @property
    def service_name(self):
        return self._service_name

    @property
    def nodehostname(self):
        return self._nodehostname

    @property
    def device_name(self):
        return self._device_name

    @property
    def image(self):
        return self._image

    @property
    def environment_variables(self):
        return self._environment_variables

    @property
    def json(self):
        return {
            "service_id": self.serviceid,
            "service_name": self.service_name,
            "node": self.nodehostname,
            "device_name": self.device_name,
            "image": self.image,
            "environment_variables": self.environment_variables
        }

    def set_service_id(self,serviceid=""):
        self._serviceid = serviceid

    def set_service_name(self,servicename=""):
        self._service_name =servicename

    def set_service_node(self,nodehostname=""):
        self._nodehostname=nodehostname

    def set_service_device(self,devicename=""):
        self._device_name=devicename

    def set_service_image(self,imagename=""):
        self._image=imagename

    def set_environment_variables(self,envvar=[]):
        self._environment_variables=envvar

    def add_environment_variables(self,envvar=""):
        self._environment_variables.append(envvar)

    def start_swarm_service(self):

        if self.service_name=="" or self.nodehostname=="" or self.device_name=="" or self.image =="":
            return False, ValueError('Not all parameters are provided')
        if len(self.environment_variables) == 0:
            return False, ValueError('No Environment variable provided. At least "EP=http://<GW>:8000" is required')

        if not self.running:

            client = docker.from_env()
            try:
                serviceid = client.services.create(name=self.service_name,
                                                   constraints=['node.hostname == ' + str(self.nodehostname)],
                                                   mode=ServiceMode(mode='replicated', replicas=1), mounts=[str(self.device_name)+':/dev/ttyACM0:ro'],
                                                   env=self.environment_variables,
                                                   image=self.image)
            # serviceid = client.services.create(name='zigbeeservice',
            #                                    constraints=['node.hostname == worker1'],
            #                                    mode=ServiceMode(mode='replicated',replicas=1), mounts=['/dev/ttyUSB0:/dev/ttyACM0:ro'],
            #                                    env=["EP=http://192.168.66.238:8000"],
            #                                    image='dregistry.fokus.fraunhofer.de:5000/tests/openmtczigbeeipe')

            # serviceid = client.services.create(name='culservice',
            #                                    constraints=['node.hostname == worker1'],
            #                                    mode=ServiceMode(mode='replicated',replicas=1), mounts=['/dev/ttyACM0:/dev/ttyACM0:ro'],
            #                                    env=["EP=http://192.168.66.238:8000"],
            #                                    image='dregistry.fokus.fraunhofer.de:5000/tests/openmtcculipe')
                print type(serviceid.id)

            except docker.errors.APIError as e:
                return False, e

            self.running = True
            self.set_service_id(serviceid=serviceid.id)
            return True, None

        else:
            return False, ValueError('This Service is already running')

    def stop_swarm_service(self):
        if self.running:
            client = docker.from_env()
            service = client.services.get(self.serviceid)

            try:
                service.remove()
            except docker.errors.APIError as e:
                return False, e
            self.running = False
            return True, None

        else:
            return False, ValueError('This service is not running!')



#docker service create --name zigbee --constraint 'node.hostname == ThinkPad-X200' --replicas 1
# --mount type=bind,source=/dev/ttyUSB0,target=/dev/ttyACM0 -e "EP=http://10.147.65.119:8000" openmtc/zigbeeipe-amd64

if __name__ == '__main__':
    test = ApplicationService(servicename='culservice',nodehostname='worker1',devicename="/dev/ttyACM0",imagename='dregistry.fokus.fraunhofer.de:5000/tests/openmtcculipe')
    a, b = test.start_swarm_service()
    print a , b
    time.sleep(120)

    test.stop_swarm_service()

