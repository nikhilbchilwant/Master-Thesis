import json
import docker
from docker.types import EndpointSpec
import time


class GatewayService():
    def __init__(self, servicename="",serviceport={}, imagename='openmtc/gateway-amd64', envvar=["ONEM2M_NOTIFICATION_DISABLED=false"]):
        """
           :type servicename : str | unicode
           :type serviceport : dictionary
           :type imagename : str | unicode
           :type envvar : str | unicode
           :param servicename    :
           :param serviceport  :
           :param imagename:
           :param envvar:
         """
        self._serviceid = ""
        self._service_name = servicename
        self._port = serviceport  # which node to run the service
        self._image = imagename  # which image to use
        self._environment_variables = envvar
        self.running = False
        self._serviceid = ""


    # service ID is set when the service is started and running = True
    @property
    def serviceid(self):
        return self._serviceid

    @property
    def service_name(self):
        return self._service_name

    @property
    def port(self):
        return self._port

    @property
    def image(self):
        return self._image

    @property
    def environment_variables(self):
        return self._environment_variables

    @property
    def json(self):
        return {
            "service_id":self._serviceid,
            "service_name": self.service_name,
            "port": self.port,
            "environment_variables": self.environment_variables,
            "image": self.image,
            "service_running":self.running
        }

    def set_service_id(self,serviceid=""):
        self._serviceid = serviceid

    def set_service_name(self, servicename=""):
        self._service_name = servicename

    def set_service_port(self, serviceport={}):
        self._port = serviceport

    def set_service_image(self, imagename=""):
        self._image = imagename

    def set_environment_variables(self, envvar):
        self.environment_variables = envvar

    def add_environment_variables(self,envvar = ""):
        self.environment_variables.append(envvar)

    def start_swarm_service(self):
        # print self.environment_variables, type(self.environment_variables)
        # print self.image, type(self.image)
        # print self.port, type(self.port)
        if self.service_name == "" or len(self.port) == 0 or self.image == "":
            return False, ValueError('Not all parameters are provided')
        if len(self.environment_variables)==0:
            return False, ValueError('No Environment variable provided. At least "ONEM2M_NOTIFICATION_DISABLED=false" is required')

        if not self.running:
            # docker service create --name gatewayservice -p 8000:8000 -e "ONEM2M_NOTIFICATION_DISABLED=false" openmtc/gateway
            client = docker.from_env()
            # serviceid = client.services.create(name='gatewayservice',
            #                                    endpoint_spec= EndpointSpec(ports={8000:8000}),
            #                                    env=["ONEM2M_NOTIFICATION_DISABLED=false"],
            #                                    image='dregistry.fokus.fraunhofer.de:5000/tests/gateway')
            try:
                serviceid = client.services.create(name=self.service_name,
                                               endpoint_spec= EndpointSpec(ports=self._port),
                                               env=self.environment_variables,
                                               image=self.image)
                print type(serviceid.id)
            except docker.errors.APIError as e:
                return False, e

            self.running = True
            self.set_service_id(serviceid=serviceid.id)
            return True, None

        else:
            return False, ValueError('This Service is already running')
        # docker
        # service create
        # --name gatewayservice
        # - p 8000:8000
        # - e "ONEM2M_NOTIFICATION_DISABLED=false"
        # openmtc/gateway




    def stop_swarm_service(self):
        if self.running:
            client = docker.from_env()
            service = client.services.get(self.serviceid)

            try:
                service.remove()
            except 	docker.errors.APIError as e:
                return False, e
            self.running = False
            return True, None

        else:
            return False, ValueError('This service is not running!')


# docker service create --name zigbee --constraint 'node.hostname == ThinkPad-X200' --replicas 1
# --mount type=bind,source=/dev/ttyUSB0,target=/dev/ttyACM0 -e "EP=http://10.147.65.119:8000" openmtc/zigbeeipe-amd64

if __name__ == '__main__':
    test = GatewayService(servicename='gatewayservice',serviceport={8000:8000})
    servicestatus, error = test.start_swarm_service()
    print servicestatus, error


    # time.sleep(10)
    #
    # test.stop_swarm_service()
