import itertools

import docker
from docker import APIClient

CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5

DOCKER_LINKS = [('gateway', 'gateway')]


class ContainerImage():
    def __init__(self, image_name="", image_id="",
                 image_data=None,
                 *args, **kw):
        """
        :type image_name: str | unicode
        :type image_id: str | unicode
        :param image_name:
        :param image_id:
        :param image_data:
        :param args:
        :param kw:
        """

        # Use case for already prepared container images (undeletable)
        if image_name != "" and image_id != "":
            if image_data is not None:
                self.logger.error("image_data is ignored when name and id are given!")
            self._name = image_name
            """ :type: str | unicode"""
            self._id = image_id
            """ :type: str | unicode"""
            self._deletable = False
            """ :type: bool"""

        elif image_name != "" and image_data is not None:
            if image_id != "":
                self.logger.error("image_id must not be set when image_data is given!")
            self._name = image_name
            """ :type: str | unicode"""
            if not self.create(image_name, image_data):
                raise  # todo: do this in a proper way!!
            self._deletable = True
            """ :type: bool"""
        else:
            self.logger.error("Problem when creating ContainerImage")

    @property
    def ID(self):  # todo: this should not be Uppercase
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def deletable(self):
        # returns true if no container_templates is using the docker image
        return self._deletable and not ContainerTmpl.is_image_used(self.ID)

    @property
    def json(self):
        return {
            "image_name": self.name,
            "image_id": self.ID,
            "deletable": self.deletable
        }

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "image_name": {"type": "string"},
                "image_id": {"type": "string"},
                "deletable": {"type": "boolean"}
            }
        }

    def create(self, name, image_data):
        return self._docker_create_image(image_data)

    def destroy(self):
        return self._docker_destroy_image()

    def _docker_create_image(self, image_data):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        try:
            s = cli.load_image(data=image_data)
            if s is None:
                s = cli.import_image_from_data(data=image_data, repository=self.name)
                if s is None:
                    return False
                    # TODO: the returned string actually holds (also) the ID
        except Exception as e:
            print e
            self.logger.error("Could not create container image: " + str(self.name))
            return False

        # Get the ID from the newly created image
        # Hopefully we meet the correct one

        res_images = None
        try:
            name = self.name
            res_images = cli.images(name=name)
        except:
            self.logger.error("Could not create container image: " + str(name))
            return False
        if len(res_images) != 1:
            self.logger.error("Could not create container image: " + str(name))
            return False
        self._id = res_images[0]['Id']
        return True

    def __del__(self):
        self.destroy()

    # TODO
    def _docker_destroy_image(self):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        imagename = self.name

        if self.deletable:
            try:
                cli.remove_image(imagename)
            except:
                self.logger.error("Could not delete image: " + str(imagename))
                return False
        else:
            self.logger.error("Image is not deletable image")
            return False
        return True

    def _docker_image_verify(self):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        imagename = self.name
        imageid = self.ID
        tempimage = cli.images(imagename)

        if bool(tempimage):
            if tempimage[0]['Id'] == imageid:
                return True
        return False


class ContainerConfig():
    def __init__(self, command_str="",
                 image=None,
                 environment={},
                 devices_mapping=None,
                 port_bindings={},
                 *args, **kw):
        self.command_str = command_str
        """ :type: str | unicode"""
        self.image = image
        """ :type: ContainerImage"""
        self.environment = environment  # Environment vars for the container
        """ :type: dict"""
        self.devices_mapping = devices_mapping if devices_mapping is None or isinstance(devices_mapping, list) else [
            devices_mapping]
        """ :type: list of dict"""
        self.port_bindings = port_bindings
        """ :type: dict"""


    @property
    def json(self):
        return {
            "command_str": self.command_str,
            "image": self.image.json,
            "environment": self.environment,
            "devices_mapping": self.devices_mapping,
            "port_bindings": self.port_bindings
        }

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "command_str": {"type": "string"},
                "image": ContainerImage.json_schema()
                # TODO: Add optional variables
            }
        }

    @staticmethod
    def default_devices_mapping():
        return [
            ContainerConfig.device_mapping('/dev/ttyACM0', '/dev/ttyACM0', 'rwm')
        ]

    @staticmethod
    def device_mapping(internal_dev, external_dev, permission):
        """Create a single device mapping.

        See: https://docker-py.readthedocs.io/en/1.7.2/host-devices/
        """
        return {
            'PathOnHost': internal_dev,  # e.g. /dev/ttyUSB0
            'PathInContainer': external_dev,  # e.g. /dev/ttyUSB3
            'CgroupPermissions': permission  # e.g. 'rwm'
        }


class ContainerTmpl():
    """A template/prototype for a container.

    This class stores any kind of information which is needed to
    create a runable container.
    """
    used_image_ids = []

    def __init__(self, name, container_config=ContainerConfig(), deletable=True, *args, **kw):

        self.next_container_id = itertools.count().next

        self.name = name  # Container template name
        """ :type: str | unicode"""
        self.container_config = container_config
        """ :type: ContainerConfig"""
        self._deletable = deletable
        """ :type: bool"""
        self.container_count = 0
        """ :type: int"""

        ContainerTmpl.used_image_ids.append(self.get_image_id())

    @property
    def json(self):
        return {
            "name": self.name,
            "container_config": self.container_config.json,
            "deletable": self.deletable
        }

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "container_config": {
                    "type": ContainerConfig.json_schema()
                },
                "deletable": {"type": "boolean"}
            }
        }

    def get_image_id(self):
        """
        Returns the image id associated with the Container Template
        :return: Container Image
        """
        return self.container_config.image.ID

    @staticmethod
    def is_image_used(image_id):
        """
        Checks if the image is used by some container template
        :param image:
        :return: bool
        """
        return image_id in ContainerTmpl.used_image_ids

    def __del__(self):
        ContainerTmpl.used_image_ids.remove(self.get_image_id())

    @property
    def deletable(self):
        # A containerTemplate is deletable when there is no containers created with this template
        return self._deletable and self.container_count < 1

    # TODO: This is too detailed, constructed for a particular case of
    # devices.  Wow, this needs totaly to be redone correctly!
    #
    # Take a TTYDevice.devname and fill out the current device mapping
    # for this
    def adjusted_device_mapping(self, devname_str):
        devices_mapping = self.container_config.devices_mapping[0]  # TODO
        devices_mapping["PathOnHost"] = devname_str
        return [devices_mapping]

    def create_container(self, environment, devices_mapping, port_bindings):
        # Try to create a new container
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        current_names = [str(x["Names"][0]) for x in cli.containers(all=True)]

        while True:
            new_id = self.next_container_id()
            new_name = self.name + "-" + str(new_id)
            if "/" + new_name not in current_names:
                break

        container_config = ContainerConfig(
            # The first three should not be configurable by the user!
            command_str=self.container_config.command_str,
            image=self.container_config.image,
            environment=environment,
            devices_mapping=devices_mapping,
            port_bindings=port_bindings
        )

        container_id = Container.create_container_docker(new_name, container_config)
        # self.container_config.image.name,
        # environment,
        # devices_mapping,
        # port_bindings)
        if container_id is None:
            self.logger.error("Creation of container failed!")
            return None

        new_container = Container(new_name, self, container_config)
        new_container.set_docker_container_id(container_id)

        self.container_count += 1

        return new_container


class Container():
    def __init__(self, name, container_tmpl, container_config=ContainerConfig(),
                 *args, **kw):
        super(Container, self).__init__()

        self.name = name
        self.tmpl = container_tmpl
        """ :type: ContainerTmpl"""
        self.status = "created"  # [ "created", "started", "restarting", "running", "paused", "exited", "exiting" ]
        """ :type: str | unicode """
        self.container_config = container_config
        """ :type: ContainerConfig"""
        self._docker_container_id = None
        """ :type: str | unicode"""

    # TODO
    #
    # def __del__(self):
    #     self.destroy_container_docker()

    @property
    def json(self):
        return {
            "name": self.name,
            "tmpl": self.tmpl.json,
            "status": self.status,
            "container_config": self.container_config.json
        }

    def json_schema(self):
        # tmpl_json_schema = type(self.container_tmpl).json_schema()
        tmpl_json_schema = self.container_tmpl.json_schema()
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tmpl": tmpl_json_schema,
                "status": {"type": "string", "enum": ["created", "started", "restarting", "running", "paused", "exited",
                                                      "exiting"]}
            }
            # TODO: container_config
        }

    def start(self):
        if not self.status == "created":
            return False

        is_started = self.docker_container_start()
        if is_started:
            self.status = "started"
        return is_started

    def start_or_restart(self):
        if self.status == "created":
            is_started = self.docker_container_start()
            if is_started:
                self.status = "started"
            return is_started
        elif self.status == "exited":
            is_started = self.docker_container_restart()
            if is_started:
                self.status = "started"
            return is_started
        else:
            return False

    def stop(self):
        if not (self.status in ["started", "restarting", "running", "exiting"]):
            return False

        is_stopped = self.docker_container_stop()
        if is_stopped:
            self.status = "exited"
        return is_stopped

    def set_docker_container_id(self, id_str):
        self._docker_container_id = id_str

    def get_docker_container_id(self):
        return self._docker_container_id

    def docker_container_stop(self):
        if self._docker_container_id is None:
            self.logger.error("Fatal: No correct container ID available")
            return False

        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        res = None
        try:
            res = cli.stop(self._docker_container_id, timeout=CLI_STOP_TIMEOUT)
        except docker.errors.NotFound:
            self.logger.warn("Could not stop container for ID: " + str(self.get_docker_container_id()))
            return False

        return True

    def docker_container_start(self):
        if self._docker_container_id is None:
            self.logger.error("Fatal: No correct container ID available")
            return False

        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        res = None
        try:
            res = cli.start(self._docker_container_id)
        except (docker.errors.NotFound):
            self.logger.warn("Could not start container for ID: " + str(self.get_docker_container_id()))
            return False
        return True

    def docker_container_restart(self):
        if self._docker_container_id is None:
            self.logger.error("Fatal: No correct container ID available")
            return False

        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        res = None
        try:
            res = cli.restart(self._docker_container_id)
        except docker.errors.NotFound:
            self.logger.warn("Could not restart container for ID: " + str(self.get_docker_container_id()))
            return False
        return True

    def docker_container_inspect(self):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

        res = None
        try:
            res = cli.inspect_container(self.get_docker_container_id())
        except docker.errors.NotFound:
            self.logger.warn("Could not retrieve container inspect for: " + str(self.get_docker_container_id()))
        return res

    @staticmethod
    def get_open_ports(port_bindings):
        # TODO: Also provide handling of '1111/udp' port mappings!
        #
        #   see: http://docker-py.readthedocs.io/en/latest/port-bindings/
        return port_bindings.keys()

    @staticmethod
    def create_container_docker(name, container_config):
        # image_name, environment, devices_mapping, port_bindings=None):
        '''A docker container is created and its ID is returned.'''
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

        command_str = container_config.command_str
        image_name = container_config.image.name
        environment = container_config.environment
        devices_mapping = container_config.devices_mapping
        port_bindings = container_config.port_bindings

        try:
            env = environment.copy()
        except AttributeError:
            env = {}
        env['NAME'] = name

        use_devices_mapping = False
        if devices_mapping is not None and isinstance(devices_mapping, (dict, list)):
            use_devices_mapping = True

        use_port_bindings = False
        if port_bindings is not None and isinstance(port_bindings, dict):
            use_port_bindings = True

        host_config_kwargs = {"links": DOCKER_LINKS}
        if use_devices_mapping:
            host_config_kwargs["devices"] = devices_mapping
        if use_port_bindings:
            host_config_kwargs["port_bindings"] = port_bindings
        host_config = cli.create_host_config(**host_config_kwargs)

        create_container_kwargs = {
            "name": name,
            "image": image_name,
            "host_config": host_config,
            "environment": env
        }
        if use_port_bindings:
            ports = Container.get_open_ports(port_bindings)
            create_container_kwargs["ports"] = ports
            print ("DEBUG: Creating container with port bindings: " + str(port_bindings) + "  " + str(ports) + "!")
        else:
            print ("DEBUG: Creating container without port bindings!")
        if command_str is not None and isinstance(command_str, (str, unicode)) and command_str is not "":
            print ("DEBUG: Creating container with explicit command str: " + str(command_str) + "!")
            create_container_kwargs["command"] = command_str

        try:
            container = cli.create_container(**create_container_kwargs)
            _id = container.get('Id')
            print ("DEBUG: Id = " + str(_id) + "!")
            return _id
        except docker.errors.NotFound:
            print ("Error: Docker container could not be created")
            return None

    def destroy_container_docker(self):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

        container_id = self.get_docker_container_id()

        # First, stop the container
        try:
            container = cli.stop(container_id, timeout=CLI_STOP_TIMEOUT)
            self.logger.debug("Docker container successfully stopped")
        except docker.errors.NotFound:
            self.logger.error("Docker container could not be stopped")
            return False

        # Second, remove the container
        try:
            container = cli.remove_container(container_id)
            self.logger.debug("Docker container successfully removed")
            self.tmpl.container_count -= 1
            return True
        except docker.errors.NotFound:
            self.logger.error("Docker container could not be removed")
            return False
