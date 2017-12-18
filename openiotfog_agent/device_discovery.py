import pyudev
from udev_device import USBDevice, TTYDevice


class DeviceDiscovery():
    def __init__(self):
        self._registered_cbs = dict()


    # Use following as example:
    #   watch_usb_devices_blocking(USBDevice.collect_usb_devices_map())
    #
    # For monitoring via udev see:
    #
    # https://pyudev.readthedocs.io/en/latest/guide.html#monitoring-devices
    #
    @staticmethod
    def watch_usb_blocking(usb_dev_map):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('usb')
        # monitor.filter_by('tty')
        for device in iter(monitor.poll, None):
            # usb_dev = USBDevice.udev_dev_to_USBDevice(device)

            if device.action == "add":
                usb_dev = USBDevice.udev_dev_to_USBDevice(device)
                if usb_dev:
                    print (device.action + " " + str(usb_dev))
            if device.action == "remove":
                usb_dev = USBDevice.udev_dev_to_USBDevice(device)
                if usb_dev:
                    print (device.action + " " + str(usb_dev))

    @property
    def registered_cbs(self):
        return self._registered_cbs

    def dev_is_registerd(self, usb_dev):
        res = self._registered_cbs.get(usb_dev.clean_str())
        if res is not None:
            return True
        else:
            return False

    # def default_add_cb_usb(usb_dev):
    #     print ("add: " + str(usb_dev))
    #     print usb_dev.vendor_id
    #     print usb_dev.product_id
    #     print "busnum", usb_dev.busnum
    #     print "devnum", usb_dev.devnum
    #     print "devpath", usb_dev.devpath
    #
    def default_add_cb_tty(usb_dev):
        print ("add: " + str(usb_dev))
        # print usb_dev.vendor_id
        # print usb_dev.product_id
        # print "devname: ", usb_dev.devname
        # print "devpath: ", usb_dev.devpath
        # print "devrealpath: ", usb_dev.devrealpath


    def default_add_cb(usb_dev):
        print ("add: " + str(usb_dev))


    def default_remove_cb(usb_dev):
        print ("remove: " + str(usb_dev))


    ## pyudev.Monitor : A synchronous device event monitor.
    ## pyudev.Monitor is for synchronous device event monitor and it is not used anywhere in this project.
    def register_cb_for_usb_dev_blocking(self, template_usb_dev, add_cb=default_add_cb, remove_cb=default_remove_cb):
        if add_cb is None and remove_cb is None:
            #TODO pythong logging
            #self.logger.error("Need at least one callback function, none provided")
            return

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('usb')
        for device in iter(monitor.poll, None):

            # Create an USBDevice. For minor devices None will be
            # returned, so they are ignored.
            usb_dev = USBDevice.udev_dev_to_USBDevice(device)
            if usb_dev is None:
                continue

            # *jedi handwave*, this is not the usb device you're looking for
            if not usb_dev.equal_vendor_product(template_usb_dev):
                continue

            if device.action == "add":
                usb_dev = USBDevice.udev_dev_to_USBDevice(device)
                if usb_dev:
                    add_cb(usb_dev)

            if device.action == "remove":
                usb_dev = USBDevice.udev_dev_to_USBDevice(device)
                if usb_dev:
                    remove_cb(usb_dev)


    ## Device
    def register_cb_for_usb_dev(self, template_usb_dev,
                                add_cb=default_add_cb,
                                remove_cb=default_remove_cb):
        if add_cb is None and remove_cb is None:
            #self.logger.error("Need at least one callback function, none provided")
            print("Need at least one callback function, none provided")
            return

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('usb')

        def _event_handler(action, device):
            # Create an USBDevice. For minor devices None will be
            # returned, so they are ignored.
            usb_dev = USBDevice.udev_dev_to_USBDevice(device)
            if usb_dev is None:
                return

            # *jedi handwave*, this is not the usb device you're looking for
            if not usb_dev.equal_vendor_product(template_usb_dev):
                return

            if device.action == "add":
                for i in device.properties.items():
                    print i

                print "-----------------------------------------------------------------"
                usb_dev = USBDevice.udev_dev_to_USBDevice(device)
                if usb_dev:
                    add_cb(usb_dev)

            if device.action == "remove":
                usb_dev = USBDevice.udev_dev_to_USBDevice(device)
                if usb_dev:
                    remove_cb(usb_dev)

        observer = pyudev.MonitorObserver(monitor, _event_handler)

        dev_id = template_usb_dev.vendor_id + "-" + template_usb_dev.product_id
        if self._registered_cbs.get(dev_id) is not None:
            #self.logger.warning("Event handlers for this usb device prototype was already registered!")
            print "logging: Event handlers for this usb device prototype was already registered!"

        self._registered_cbs[dev_id] = observer
        #self.logger.debug("New callbacks registerd for device template: " + dev_id)
        print "logging: New callbacks registered for device template: " + dev_id

        observer.start()

    def unregister_cb_for_usb_dev(self, template_usb_dev):
        dev_id = template_usb_dev.vendor_id + "-" + template_usb_dev.product_id

        observer = self._registered_cbs.get(dev_id)
        if observer is None:
            #TODO Use python Logging
            print("There are no event handlers registered for this device prototype!")
        else:
            # TODO Use python Logging
            print("Deregistering callbacks for registerd device template: " + dev_id)
            observer.stop()
            # TODO: Should the "usb" filter be removed too?
            self._registered_cbs.pop(dev_id)
            # test = self._registered_cbs.get(dev_id)
            # self.logger.debug("dev_id should be removed from dict: " + str(test))

    def register_cb_for_tty_dev(self, template_tty_dev,
                                add_cb=default_add_cb_tty,
                                remove_cb=default_remove_cb):
        if add_cb is None and remove_cb is None:
            #TODO python logging
            #self.logger.error("Need at least one callback function, none provided")
            return

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('tty')

        def _event_handler(action, device):
            # Create a TTYDevice. For minor devices None will be
            # returned, so they are ignored.
            tty_dev = TTYDevice.udev_dev_to_TTYDevice(device)
            if tty_dev is None:
                return

            # *jedi handwave*, this is not the tty device you're looking for
            if not tty_dev.equal_vendor_product(template_tty_dev):
                return

            if device.action == "add":
                tty_dev = TTYDevice.udev_dev_to_TTYDevice(device)
                if tty_dev:
                    add_cb(tty_dev)

            if device.action == "remove":
                tty_dev = TTYDevice.udev_dev_to_TTYDevice(device)
                if tty_dev:
                    remove_cb(tty_dev)

        observer = pyudev.MonitorObserver(monitor, _event_handler)

        dev_id = template_tty_dev.vendor_id + "-" + template_tty_dev.product_id
        if self._registered_cbs.get(dev_id) is not None:
            #self.logger.warning("Event handlers for this tty device prototype was already registered!")
            print("Event handlers for this tty device prototype was already registered!")

        self._registered_cbs[dev_id] = observer
        # TODO use python logging
        #self.logger.debug("New callbacks registerd for device template: " + dev_id)
        print("New callbacks registerd for device template: " + dev_id)
        observer.start()


    def unregister_cb_for_tty_dev(self, template_tty_dev):
        dev_id = template_tty_dev.vendor_id + "-" + template_tty_dev.product_id

        observer = self._registered_cbs.get(dev_id)
        if observer is None:
            #self.logger.info("There are no event handlers registered for this device prototype!")
            print("There are no event handlers registered for this device prototype!")
        else:
            #self.logger.debug("Deregistering callbacks for registered device template: " + dev_id)
            print("Deregistering callbacks for registered device template: " + dev_id)
            observer.stop()
            # TODO: Should the "tty" filter be removed too?
            self._registered_cbs.pop(dev_id)
            # test = self._registered_cbs.get(dev_id)
            # self.logger.debug("dev_id should be removed from dict: " + str(test))


    def list_registered_cbs(self):
        # self.logger.info("Registered dev_ids:")
        print ("Registered dev_ids:")
        for dev_id in self._registered_cbs.keys():
            # self.logger.info("\t" + dev_id)
            print("\t" + dev_id)




if __name__ == '__main__':
    udev_device = TTYDevice(vendor_id="0403",
                            product_id="6001"
    )

    udev_device2 = TTYDevice(vendor_id="03eb",
                            product_id="204b"
    )
    dd = DeviceDiscovery()
    dd.register_cb_for_tty_dev(udev_device)
    dd.register_cb_for_tty_dev(udev_device2)
    while 1:
        continue

