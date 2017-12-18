import os
import io

class USBDevice():
    def __init__(self, vendor_id, product_id, busnum="", devnum="", devpath="", devrealpath="", *args, **kw):

        self.vendor_id = vendor_id
        self.product_id = product_id
        self.busnum = busnum
        self.devnum = devnum
        self.devpath = devpath
        self.devrealpath = devrealpath

    def __str__(self):
        return (str(self.vendor_id) + ":" + str(self.product_id)
                + "@" + str(self.busnum) + "/" + str(self.devnum))

    def clean_str(self):
        return (str(self.vendor_id) + "-" + str(self.product_id)
                + "-" + str(self.busnum) + "-" + str(self.devnum))

    @property
    def json(self):
        return {
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "busnum": self.busnum,
            "devnum": self.devnum,
            "devpath": self.devpath,
            "devrealpath": self.devrealpath
        }

    def equal_vendor_product(self, other):
        if self.vendor_id == other.vendor_id \
                and self.product_id == other.product_id:
            return True
        else:
            return False

    def equals(self, other):
        if self.vendor_id == other.vendor_id \
                and self.product_id == other.product_id \
                and self.busnum == other.busnum \
                and self.devnum == other.devnum \
                and self.devpath == other.devpath \
                and self.devrealpath == other.devrealpath:
            return True
        else:
            return False

    @staticmethod
    def collect_usb_devices_map():
        usb_devices_path = "/sys/bus/usb/devices"
        ret_map = dict()
        # See the location /sys/bus/usb/devices. Inside each directory in this location,there are files 'idProduct', 'idVendor', 'busnum', 'devnum'.
        # This function reads the vendorid, productid etc from the files. and make a dictionary with pathname: usb_device
        for d in os.listdir(usb_devices_path):
            # sub is the location for each directory in /sys/bus/usb/devices
            sub = os.path.join(usb_devices_path, d)

            # vendor_id = ""
            # product_id = ""
            # busnum = ""
            # devnum = ""
            devpath = sub
            devrealpath = os.path.realpath(sub)

            product_id_file = os.path.join(sub, "idProduct")
            vendor_id_file = os.path.join(sub, "idVendor")
            busnum_file = os.path.join(sub, "busnum")
            devnum_file = os.path.join(sub, "devnum")

            if os.path.exists(product_id_file) and os.path.exists(vendor_id_file):
                with io.open(vendor_id_file, "r") as _vendor_file:
                    vendor_id = _vendor_file.readline().strip()
                with io.open(product_id_file, "r") as _product_file:
                    product_id = _product_file.readline().strip()
                with io.open(busnum_file, "r") as _busnum_file:
                    busnum = _busnum_file.readline().strip()
                with io.open(devnum_file, "r") as _devnum_file:
                    devnum = _devnum_file.readline().strip()
                    usb_device = USBDevice(vendor_id, product_id, busnum, devnum, devpath, devrealpath)
                    ret_map[usb_device.devrealpath] = usb_device
        return ret_map

    # Convert a udev device into an USBDevice
    #
    # The following show a full list of properties' keys.  This may be
    # relevant in the future?
    #
    # [u'ACTION', u'BUSNUM',
    # u'DEVNAME', u'DEVNUM', u'DEVPATH', u'DEVTYPE', u'ID_BUS',
    # u'ID_MODEL', u'ID_MODEL_ENC', u'ID_MODEL_FROM_DATABASE',
    # u'ID_MODEL_ID', u'ID_REVISION', u'ID_SERIAL',
    # u'ID_SERIAL_SHORT', u'ID_USB_INTERFACES', u'ID_VENDOR',
    # u'ID_VENDOR_ENC', u'ID_VENDOR_FROM_DATABASE',
    # u'ID_VENDOR_ID', u'MAJOR', u'MINOR', u'PRODUCT', u'SEQNUM',
    # u'SUBSYSTEM', u'TYPE', u'USEC_INITIALIZED']

    # @staticmethod
    # def udev_dev_to_USBDevice(dev):
    #     _props = dev.properties
    #     vendor_id = _props.get(u'ID_VENDOR_ID')
    #     product_id = _props.get(u'ID_MODEL_ID')
    #     busnum = _props.get(u'BUSNUM')
    #     devnum = _props.get(u'DEVNUM')
    #     devpath = _props.get(u'DEVPATH')
    #
    #     # pprint.pprint (dict(dev.properties))
    #     # print ("DBG: udev_dev DEVNAME: " + str(dev.properties.get(u'DEVNAME')))
    #
    #     for _p in [vendor_id, product_id, busnum, devnum, devpath]:
    #         if _p is None:
    #             return None
    #     return USBDevice(vendor_id, product_id, busnum, devnum, devpath)

    @staticmethod
    def udev_dev_to_USBDevice(dev):
        _props = dev.properties
        vendor_id = _props.get(u'ID_VENDOR_ID')
        product_id = _props.get(u'ID_MODEL_ID')
        busnum = _props.get(u'BUSNUM')
        devnum = _props.get(u'DEVNUM')
        devpath = _props.get(u'DEVPATH')
        # devrealpath = _props.get(u'DEVREALPATH')
        # pprint.pprint (dict(dev.properties))
        # print ("DBG: udev_dev DEVNAME: " + str(dev.properties.get(u'DEVNAME')))

        for _p in [vendor_id, product_id, busnum, devnum, devpath]:
            if _p is None:
                return None
        return USBDevice(vendor_id, product_id, busnum, devnum, devpath)

    # print usb_dev.vendor_id
    # print usb_dev.product_id
    # print usb_dev.busnum
    # print usb_dev.devnum
    # print usb_dev.devpath
    # print usb_dev.devrealpath


    @staticmethod
    def usb_dev_list_to_map(usb_dev_list):
        ret_dict = dict()
        for dev in usb_dev_list:
            ret_dict[dev.devrealpath] = dev

    @staticmethod
    def check_udev_in_usb_dev_map(realpath, usb_dev_map):
        usb_device = usb_dev_map.get(realpath)
        return usb_device

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "vendor_id": {"type": "string"},
                "product_id": {"type": "string"},
                "busnum": {"type": "string"},
                "devnum": {"type": "string"},
                "devpath": {"type": "string"},
                "devrealpath": {"type": "string"}
            }
        }


class TTYDevice():
    def __init__(self, vendor_id, product_id, devname="", devpath="", devrealpath="", *args, **kw):

        self.vendor_id = vendor_id
        self.product_id = product_id
        # self.devicetype is a user given name. Like XBee-Stick, Cul-Stick etc.
        #self.devicetype = devtype
        self.devname = devname
        self.devpath = devpath
        self.devrealpath = devrealpath

    def __str__(self):
        return (str(self.vendor_id) + ":" + str(self.product_id)
                + ">" + str(self.devname))

    @property
    def json(self):
        return {
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            #"user_given_device_type": self.devicetype,
            "devname": self.devname,
            "devpath": self.devpath,
            "devrealpath": self.devrealpath
        }

    # TODO
    #
    @staticmethod
    def json_schema():
        return {
            "type" : "object",
            "properties" : {
                "vendor_id": { "type": "string" },
                "product_id": { "type": "string" },
                "devname" : { "type": "string" },
                "devpath" : { "type": "string" },
                "devrealpath" : { "type": "string" }
            }
        }

    def equal_vendor_product(self, other):
        if self.vendor_id == other.vendor_id \
                and self.product_id == other.product_id:
            return True
        else:
            return False

    def equals(self, other):
        if self.vendor_id == other.vendor_id \
                and self.product_id == other.product_id \
                and self.devname == other.devname \
                and self.devpath == other.devpath \
                and self.devrealpath == other.devrealpath:
            return True
        else:
            return False


    def reset_path(self):
        self.devname = ""
        self.devpath =""
        self.devrealpath = ""

            # @staticmethod

    # def collect_usb_devices_map():
    #     usb_devices_path = "/sys/bus/usb/devices"
    #     ret_map = dict()

    #     for d in os.listdir(usb_devices_path):
    #         sub = os.path.join(usb_devices_path, d)

    #         vendor_id = ""
    #         product_id = ""
    #         busnum = ""
    #         devnum = ""
    #         devpath = sub
    #         devrealpath = os.path.realpath(sub)

    #         product_id_file = os.path.join(sub, "idProduct")
    #         vendor_id_file = os.path.join(sub, "idVendor")
    #         busnum_file = os.path.join(sub, "busnum")
    #         devnum_file = os.path.join(sub, "devnum")

    #         if os.path.exists(product_id_file) and os.path.exists(vendor_id_file):
    #             with io.open(vendor_id_file, "r") as _vendor_file:
    #                 vendor_id = _vendor_file.readline().strip()
    #             with io.open(product_id_file, "r") as _product_file:
    #                 product_id = _product_file.readline().strip()
    #             with io.open(busnum_file, "r") as _busnum_file:
    #                 busnum = _busnum_file.readline().strip()
    #             with io.open(devnum_file, "r") as _devnum_file:
    #                 devnum = _devnum_file.readline().strip()
    #                 usb_device = USBDevice(vendor_id, product_id, busnum, devnum, devpath, devrealpath)
    #                 ret_map[usb_device.devrealpath] = usb_device
    #     return ret_map

    # Convert a udev device into an TTYDevice
    #
    # The following show a full list of properties' keys.  This may be
    # relevant in the future?
    #
    # TODO
    #
    @staticmethod
    def udev_dev_to_TTYDevice(dev):
        _props = dev.properties
        vendor_id = _props.get(u'ID_VENDOR_ID')
        product_id = _props.get(u'ID_MODEL_ID')
        devname = _props.get(u'DEVNAME')
        devpath = _props.get(u'DEVPATH')
        devrealpath = os.path.realpath(devpath)

        for _p in [vendor_id, product_id, devname, devpath, devrealpath]:
            if _p is None:
                return None
        return TTYDevice(vendor_id, product_id, devname, devpath, devrealpath)

    @staticmethod
    def tty_dev_list_to_map(tty_dev_list):
        ret_dict = dict()
        for dev in tty_dev_list:
            ret_dict[dev.devrealpath] = dev

    @staticmethod
    def check_udev_in_tty_dev_map(realpath, tty_dev_map):
        tty_device = tty_dev_map.get(realpath)
        return tty_device
