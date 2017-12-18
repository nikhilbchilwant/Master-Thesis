import docker
CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5
client = docker.APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
import pyudev
import os, time
#from udev_device import USBDevice, TTYDevice

#template_usb_dev = USBDevice(vendor_id=0403, product_id=6001)

class DeviceDiscovery():
    def __init__(self):
        self.devices = []


    def discover_devices(self):
        context = pyudev.Context()
        for device in context.list_devices():
            vendor_id = device.properties.get(u'ID_VENDOR_ID')
            product_id = device.properties.get(u'ID_MODEL_ID')
            devicefilename = device.properties.get(u'DEVNAME')
            if vendor_id == '0403' and product_id == '6001': #and 'ttyUSB' in str(devicefilename)
                # print device.properties.items()


                devname = device.properties.get(u'DEVNAME')
                devpath = device.properties.get(u'DEVPATH')
                for i in device.properties.items():
                    print i
                # print vendor_id
                # print product_id
                # print devname
                # print devpath
                print '-----------------------------------------------------------'

                # containerid = self.set_permission_in_container(devicename=devname,containerimage="openmtc/zigbeeipe-amd64")
                # print containerid

    def set_permission_in_container(self, devicename="",containerimage=""):
        if devicename =="" or containerimage =="":
            return "devicename and Container Image name required"

        info = os.lstat(devicename)
        print info
        # Get major and minor number for device
        major_dnum = os.major(info.st_rdev)
        minor_dnum = os.minor(info.st_rdev)

        # print "Major Device Number :", major_dnum
        # print "Minor Device Number :", minor_dnum

        while 1:
            cid = client.containers(filters={"ancestor":containerimage})
            if cid != []:
                ContainerID = cid[0]['Id']
                # print ContainerID

                permissionsetupcommand = "c " + str(major_dnum) + ":" + str(minor_dnum) + " rwm"
                # print permissionsetupcommand

                # print "setting up permission: "

                with open("/sys/fs/cgroup/devices/docker/" + ContainerID + "/devices.allow", 'a') as the_file:
                    the_file.write(permissionsetupcommand)
                time.sleep(1)
                return ContainerID
            else:
                pass


if __name__ == '__main__':
    test = DeviceDiscovery()
    test.discover_devices()