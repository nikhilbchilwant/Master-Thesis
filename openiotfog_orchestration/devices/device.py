
class knowndevice():
    def __init__(self, product_id="", vendor_id="", devicename=""):
        """
           :type product_id : str | unicode
           :type vendor_id : str | unicode
           :param product_id    :
           :param vendor_id  :
           :param args:
           :param kw:
         """

        self._device_name = devicename
        self._product_id = product_id
        self._vendor_id = vendor_id

    @property
    def device_name(self):
        return self._device_name

    @property
    def vendor_id(self):
        return self._vendor_id

    @property
    def product_id(self):
        return self._product_id

    @property
    def json(self):
        return {
            "devicename": self.device_name,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id
        }

    def set_device_name(self,newdevicename=""):
        self._device_name=newdevicename

    def set_vendor_id(self,vendorid=""):
        self._vendor_id=vendorid

    def set_product_id(self,productid=""):
        self._product_id=productid

#

# expected_json = {
#     'device_adapter_name': 'GIVEN_NAME_BY_USER',
#     'product_id': 'DEVICE_PRODUCT_ID',
#     'vendor_id': 'DEVICE_VENDOR_ID'
# }

