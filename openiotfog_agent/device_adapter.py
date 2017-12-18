from gevent import spawn_later, wait
import docker
CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5

import os, time
import thread

import itertools

from device_discovery import DeviceDiscovery

from udev_device import USBDevice, TTYDevice

#from container import ContainerTmpl

# Device Adapter 2 only depends on Container Image, not Container Tmpl
from container_images import Container_Image

# TODO: Note that a device adapter may not depend on a single
# container_tmpl, but a graph of dependant container_tmpl!

# Device Adapter holds a list of device_adapter.
class DeviceAdapterTmpl():
    def __init__(self, name, udev_device, container_image=None, device_discovery="unsupported", container_autostart=False,
                 deletable=True):


        self.next_device_adapter_id = itertools.count().next

        self.name = name
        self.udev_device = udev_device
        self.device_discovery = device_discovery

        # Start Container autonomously. self.container_tmpl and self.container_autostart is needed for Agent v1 version.
        # self.container_tmpl = container_tmpl
        self.container_autostart = container_autostart
        """ :type: bool"""
        # """ :type: Container_Image"""


        ## To Map device to Docker Swarm, we need to setup device permission, for that we need only image.
        if container_image == None:
            self.container_image = Container_Image()
        else:
            self.container_image = container_image
        # """ :type: Container_Image"""

        ##There can be multiple device adapter for a device. Each device adapter is an action for that device.
        self.all_device_adapters = {}
        # This is for adding callback
        self._discovery_thread = None


        self._deletable = deletable
        """ :type: bool"""

    @property
    def deletable(self):
        return self._deletable

    def is_discoverable(self):
        return self.device_discovery != "unsupported"

    def is_discovery_on(self):
        return self.is_discoverable() and self.device_discovery != "off"

    def set_discovery_on(self):
        self.device_discovery = "on"

    def set_discovery_off(self):
        self.device_discovery = "off"

    def is_autostart_on(self):
        return self.container_autostart

    def set_container_autostart_on(self):
        self.container_autostart = True

    def set_container_autostart_off(self):
        self.container_autostart = False

    def set_as_notdeletable(self):
        self._deletable=False

    def set_as_deletable(self):
        self._deletable=True

    # Old with Container Template
    # @property
    # def json(self):
    #     return {
    #         # TODO: "id" : id(self),
    #         "name": self.name,
    #         "udev_device": self.udev_device.json,
    #         "device_discovery": self.device_discovery,
    #         "container_autostart": self.container_autostart,
    #         "container_tmpl": self.container_tmpl.json
    #     }
    @property
    def json(self):
        return {
            # TODO: "id" : id(self),
            "name": self.name,
            "udev_device": self.udev_device.json,
            "device_discovery": self.device_discovery,
            "container_autostart": self.container_autostart,
            "container_image": self.container_image.json
        }

    # old with Container Template (to be used later)
    # @staticmethod
    # def json_schema_to_validate():
    #     return {
    #         "type": "object",
    #         "properties": {
    #             # TODO: "id" : { "type" : "number" },
    #             "name": {"type": "string"},
    #             "udev_device": USBDevice.json_schema(),
    #             "device_discovery": {"type": "string", "enum": ["on", "off", "unsupported"]},
    #             "container_autostart": {"type": "boolean"},
    #             "container_tmpl": ContainerTmpl.json_schema()
    #         }
    #     }

    @staticmethod
    def json_schema_to_validate():
        return {
            "type": "object",
            "properties": {
                # TODO: "id" : { "type" : "number" },
                "name": {"type": "string"},
                "udev_device": TTYDevice.json_schema(),
                "device_discovery": {"type": "string", "enum": ["on", "off", "unsupported"]},
                "container_autostart": {"type": "boolean"},
                "container_image": Container_Image.json_schema()
            }
        }

    def json_schema(self):
        # udev_device_json_schema = type(self.udev_device).json_schema()
        # container_tmpl_json_schema = type(self.container_tmpl).json_schema()
        udev_device_json_schema = self.udev_device.json_schema()
        container_tmpl_json_schema = self.container_tmpl.json_schema()
        return {
            "type": "object",
            "properties": {
                # TODO: "id" : { "type" : "number" },
                "name": {"type": "string"},
                "udev_device": udev_device_json_schema,
                "device_discovery": {"type": "string", "enum": ["on", "off", "unsupported"]},
                "container_autostart": {"type": "boolean"},
                "container_image": Container_Image.json_schema()
            }
        }


    def stop_device_discovery(self, dd_obj):
        """
        :type dd_obj: DeviceDiscovery | unicode
        :param dd_obj:
        """
        # TODO
        # self._discovery_thread = thread.start_new_thread(dd_obj.unregister_cb_for_usb_dev, self.udev_device)

        # TODO: Identify the object that needs to be destructed by known device adapters and there underlying device

        #if type(self.udev_device) in (USBDevice, TTYDevice, ):
        if isinstance(self.udev_device, USBDevice) or isinstance(self.udev_device,TTYDevice):
            dd_obj.unregister_cb_for_tty_dev(self.udev_device)
        else:
            # TODO Add python logging
            #self.logger.error("Unknown device type: '" + str(type(self.udev_device)) + "'!")
            print("Unknown device type: '" + str(type(self.udev_device)) + "'!")
        self.set_discovery_off()

    def start_device_discovery(self, dd_obj):
        """
        :type dd_obj: DeviceDiscovery | unicode
        :param dd_obj:
        """
        # self._discovery_thread = thread.start_new_thread(dd_obj.register_cb_for_usb_dev, (self.udev_device,  ))

        ## Adding Callback is adding DeviceAdapter. (In this case, DeviceAdapter start and stop a Container. When add_cb is called, DeviceAdapter starts a Container, when remove_cb is called Container is removed.)
        def add_cb(dev):
            # TODO check if Container Autostart ON then deviceadapter1, otherwise deviceadapter2. Check issue 6
            print dev
            # If I update the self.udev_device then, the devname(e.g. /dev/ttyUSB0, /dev/ttyACM0) will be updated. And we can see the devname when they are attached.
            self.udev_device = dev

            #### TODO here are the condition check. If, Container Autostart = SWARM_MODE, create swarm mode. Otherwise just call the default_add_cb and default_remove_cb from device_discovery
            if self.container_autostart:
                return self.create_device_adapter_docker_swarm(dev)
            else:
                print "added: " + str(self.udev_device)
            # remove_cb = dd_obj.__class__.default_remove_cb

        ## Remove Callback is destroying deviceadapter. (In this case DeviceAdapter, remove the Container)
        def remove_cb(dev):
            # device removed, so the path information is removed.
            self.udev_device.reset_path()
            #If container_autostart (swarm adapter) is on setup permission. Otherwise just show that the device is added.
            if self.container_autostart:
                return self.destroy_device_adapter_docker_swarm(dev)
            else:
                print "removed: " +str(self.udev_device)

        if isinstance(self.udev_device, USBDevice):
            #if type(self.udev_device) is USBDevice:
            print("Registering device discovery for USBDevice.")
            #self.logger.debug("Registering device discovery for USBDevice.")
            self._discovery_thread = thread.start_new_thread(dd_obj.register_cb_for_usb_dev,
                                                             (self.udev_device, add_cb, remove_cb,))

        elif isinstance(self.udev_device, TTYDevice):
            #elif type(self.udev_device) is TTYDevice:
            print("Registering device discovery for TTYDevice.")
            #self.logger.debug("Registering device discovery for TTYDevice.")
            self._discovery_thread = thread.start_new_thread(dd_obj.register_cb_for_tty_dev,
                                                             (self.udev_device, add_cb, remove_cb,))
        else:
            print("Unknown device type: '" + str(type(self.udev_device)) + "'!")
            #self.logger.error("Unknown device type: '" + str(type(self.udev_device)) + "'!")
            return
        self.set_discovery_on()

    def run(self):
        try:
            wait()
        except (KeyboardInterrupt, SystemExit):
            print("Shut down after interrupt")
            #self.logger.info("Shut down after interrupt")
        except Exception:
            print("Error")
            #self.logger.exception("Error")
            raise
        finally:
            print("Shut down, all children exited")
            #self.logger.debug("Shut down, all children exited")
            # for timer in self._timers:
            #     timer.kill()


    # def __init__(self, name, device_adapter_tmpl, containerimage, udev_device, *args, **kw):
    def create_device_adapter_docker_swarm(self, tty_dev):

        # Create the device and return the device
        new_id = self.next_device_adapter_id()
        new_name = self.name + "-" + str(new_id)
        new_device_adapter = DeviceAdapter_DockerSwarm(new_name, self, containerreponame= self.container_image.repo, udev_device=tty_dev)

        #TODO use python loggin instead of print
        print("Successfully created new device adapter.")

        #if container autostart is False, setup permission.
        if self.container_autostart:
            print("Setting up Container cgroup permission to access device")
            thread.start_new_thread(new_device_adapter.set_permission_in_container,())
        else:
            #TODO python Logging
            print("Device Adapter for Swarm should not be activated, but device adapter for host should be activated")

        self.all_device_adapters[new_id] = new_device_adapter


    def destroy_device_adapter_docker_swarm(self, tty_dev):

        # Identify the device adapter
        id = self.get_device_adapter_name_by_dev(tty_dev)
        if id is not None:
            #TODO logging
            # Delete the device adapter from the internal list and destroy it
            #TODO logging
            print("Removing device adapter: " + str(id))
            self.all_device_adapters.pop(id)
        else:
            # TODO use logging
            print("Could not find device adapter for device: " + str(tty_dev.json) + ".")



    def get_device_adapter_name_by_dev(self, usb_dev):
        # usb_dev is an USBDevice!
        for (id, device_adapter) in self.all_device_adapters.items():
            if usb_dev.equals(device_adapter.udev_device):
                #self.logger.debug("Found device: '" + device_adapter.name + "' in device adapters list")
                print("Found device: '" + device_adapter.name + "' in device adapters list")
                return id
        return None



class DeviceAdapter_DockerSwarm():
    def __init__(self, name, device_adapter_tmpl, containerreponame, udev_device, *args, **kw):

        self.name = name
        self.tmpl = device_adapter_tmpl
        self.containerreponame = containerreponame  # Could be None !
        self.udev_device = udev_device
        print self.containerreponame

    def set_permission_in_container(self):
        if self.udev_device.devname == "" or self.containerreponame == "":
            return "devicename and Container Image name required"

        info = os.lstat(self.udev_device.devname)
        print info
        # Get major and minor number for device
        major_dnum = os.major(info.st_rdev)
        minor_dnum = os.minor(info.st_rdev)

        # print "Major Device Number :", major_dnum
        # print "Minor Device Number :", minor_dnum
        client = docker.APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

        while 1:
            cid = client.containers(filters={"ancestor": self.containerreponame})
            if cid != []:
                ContainerID = cid[0]['Id']
                # print ContainerID

                permissionsetupcommand = "c " + str(major_dnum) + ":" + str(minor_dnum) + " rwm"
                print permissionsetupcommand

                print "setting up permission: "

                with open("/sys/fs/cgroup/devices/docker/" + ContainerID + "/devices.allow", 'a') as the_file:
                    the_file.write(permissionsetupcommand)
                time.sleep(1)
                return ContainerID
            else:
                pass



if __name__ == '__main__':

    #udev_device1 = TTYDevice(vendor_id="0403", product_id="6001")
    udev_device1 = TTYDevice(vendor_id="03eb", product_id="204b")
    print udev_device1.__str__()
    if isinstance(udev_device1, TTYDevice):
        print True



    image1 = Container_Image(image_repo="openmtc/cul868ipe-amd64")

    deviceadaptertmpl1 = DeviceAdapterTmpl(name="cultemplate",udev_device=udev_device1, container_image=image1, device_discovery="on",container_autostart=True)

    dd = DeviceDiscovery()

    deviceadaptertmpl1.start_device_discovery(dd)




    # udev_device2 = TTYDevice(vendor_id="03eb",
    #                         product_id="204b"
    # )

    while 1:
        continue
