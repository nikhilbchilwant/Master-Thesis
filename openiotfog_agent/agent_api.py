import gevent
import thread
import json
import re

import netifaces as ni
from flask import Flask, jsonify, make_response, abort, request, Response
from gevent.wsgi import WSGIServer
from jsonschema import validate, ValidationError

#monitoring module
from monitoring import monitoring_blueprint, sense_monitoring_data, start_database

#device modules
from device_discovery import DeviceDiscovery
from udev_device import TTYDevice
from device_adapter import DeviceAdapterTmpl
from container_images import Container_Image, Container_Image_Manager
# Docker Swarm related module
from openiotfognodeconfig import fognodeconfig
from ConfigParser import SafeConfigParser

config = SafeConfigParser()
config.read('agent_config.ini')

class OpenIoTFogAgent():
    def default_cleanup(self):
        #TODO Use standard logging module of python
        # TODO leave the swarm if the node is part of a cluster

        # TODO Update the images from the central orchestrator when Agent starts
        # delete all the images from the Node
        for n, i in enumerate(self._images_list):
            self.image_manager.image_delete(imagerepo=i.repo,tag=i.tag)
            del self._images_list[n]

        # TODO update the device templates from the central orchestrator when the Agent starts
        # delete all the device templates
        for n,i in enumerate(self._device_template_list):
            del self._device_template_list[n]


    def __init__(self, do_cleanup=True, *args, **kw):
        #TODO Use standard logging module

        self.openiotfogagentapp_flask = Flask(__name__)

        # using standard configparser
        #self.host = config.get('main', 'HOST')
        self.port = int(config.get('main', 'PORT'))
        self.interface = config.get('main', 'INTERFACE')

        self.ip = ni.ifaddresses(self.interface)[2][0]['addr']
        self.host = self.ip
        # # Enable/Disable Monitoring
        self.monitoring = config.get('main', 'MONITORING') == "True"

        #  Check here if you want to change config file and how to read from config file https://stackoverflow.com/questions/19078170/python-how-would-you-save-a-simple-settings-config-file

        # USING python config for flask.
        # Reading the configurations from config.py file
        # self.openiotfogagentapp_flask.config.from_object('config')
        #
        # self.host = self.openiotfogagentapp_flask.config['HOST']
        # self.port = self.openiotfogagentapp_flask.config['PORT']
        # self.interface = self.openiotfogagentapp_flask.config['INTERFACE']
        # self.ip = ni.ifaddresses(self.interface)[2][0]['addr']
        # self.host = self.ip

        # Enable/Disable Monitoring
        #self.monitoring = self.openiotfogagentapp_flask.config['MONITORING']

        # print self.host, self.port, self.interface, self.monitoring
        # print type(self.host), type(self.port), type(self.interface), type(self.monitoring)


        ## READING Container registry info
        registry = config.get('image_registry', 'CONTAINER_REGISTRY')
        registryusername = config.get('image_registry', 'REGISTRY_USERNAME')
        registryuserpass = config.get('image_registry', 'REGISTRY_USERPASSWORD')

        # print registry,registryusername,registryuserpass

        # create image_handler object

        self._auth = {'username': registryusername, 'password':registryuserpass }

        self.image_manager = Container_Image_Manager(imageregistry=registry,auth=self._auth)

        # Only Attribute to manage with Swarm
        self._node_config = None


        # Device attributes: There are 2 list. Known Device List.
        # device_template_list, is the list of known devices. Inside each Device_adapter_template there is a list of "all_device_adapters". If device is attached it shows up in this list

        self._device_template_list = []

        #self._container_list = []
        """ :type: list of Container"""

        self._dd = DeviceDiscovery()

        self._images_list = []

        self.debug = None

        self.do_cleanup = do_cleanup


        # error handlers:
        @self.openiotfogagentapp_flask.errorhandler(404)
        def page_not_found(e):
            return make_response(jsonify({'error': e.description}), 404)

        @self.openiotfogagentapp_flask.errorhandler(405)
        def method_not_allowed(e):
            return make_response(jsonify({'error': e.description}), 405)

        ##########################################################################################
        # Base endpoint TODO Try to add HATEOS
        @self.openiotfogagentapp_flask.route('/agent/v1', methods=['GET'], strict_slashes=False)
        def base_endpoint():
            return """<xmp> OpenIoTFog Node
            /agen/v1 [POST] : For adding this node to a Docker Swarm Cluster
            /agent/v1/swarm_spec [GET,DELETE] : To remove this node from a Docker Swarm Cluster
            /device_templates [GET, POST] : To see the list of known devices to this node
            /device_templates/device_name [GET, DELETE, PUT] Get details, Delete or Update known device.
            /images: to see the supported OpenIoTFog Docker images in this Node
            </xmp>"""

        ###########################################################################################
        #  Following endpoints are for adding the node to a cluster
        @self.openiotfogagentapp_flask.route('/agent/v1', methods=['POST'], strict_slashes=False)
        def join_swarm_cluster():
            if not request.json or 'remotemanager' not in request.json or 'token' not in request.json:
                return make_response(jsonify({'error': 'Need proper JSON to create a container!'}), 400)

            # TODO: Check the provided JSON for correct values, use
            # json-schema here
            expected_json = {
                'remotemanager': 'IP_OF_SWARM_MANAGER',
                'token': 'TOKEN'
            }
            # swarmnodeconfig()
            # self._swarm_config.swarm_cluter_join("10.147.66.51:2377",
            #                       'SWMTKN-1-48ktu2mw56khrli3lpoihgihwcfwsjoi9u3ug8gthtg4d488nh-b84ku93uc0sb0wstayl02yek5')
            # TODO: Check weather POSTing 2 time returns error
            if (self._node_config != None and self._node_config.get_swarmconfig_node_ID() != ""):
                return make_response(jsonify({'error': 'This node is already part of a swarm cluster!'}), 400)

            # Join a new Swarm Cluster based on the configuration
            # new_json = request.get_json(force=False)
            remotemanager = request.json['remotemanager']
            swarmtoken = request.json['token']
            self._node_config = fognodeconfig(nodeip=self.ip)
            res = self._node_config.swarm_cluter_join(remotemanager, swarmtoken)
            if res:
                return jsonify(self._node_config.json)


        @self.openiotfogagentapp_flask.route('/agent/v1/swarm_spec', methods=['GET'], strict_slashes=False)
        def get_swarm_config():
            if self._node_config == None:
                return make_response(jsonify({'error': 'This node is not part of a Swarm cluster'}), 404)
            if self._node_config.get_swarmconfig_node_ID() == "":
                return make_response(jsonify({'error': 'This node is not part of a Swarm cluster'}), 404)
            swarmconfig = self._node_config.json
            print swarmconfig
            return make_response(jsonify(swarmconfig))
            # return make_response(jsonify({'error': 'Container: >' + name + '< not found!'}), 404)

        # Remove the node from swarm cluster
        @self.openiotfogagentapp_flask.route('/agent/v1/swarm_spec', methods=['DELETE'], strict_slashes=False)
        def leave_swarm_cluster():
            if self._node_config == None:
                return make_response(jsonify({'error': 'This node is not part of a Swarm cluster'}), 404)
            if self._node_config.nodeid == "":
                return make_response(jsonify({'error': 'This node is not part of a Swarm cluster'}), 404)

            leftswarm = self._node_config.swarm_cluster_leave()
            self._node_config = None
            if leftswarm:
                return make_response(jsonify({'success': 'This node left Swarm cluster successfully'}), 200)
            return make_response(jsonify({'error': 'could not leave swarm'}), 404)


        ##########################################################################################################
        ############## Following EndPoints are for managing Devices --------------------


        #list the device templates : works
        @self.openiotfogagentapp_flask.route('/agent/v1/device_templates', methods=['GET'], strict_slashes=False)
        def device_templates():
            return jsonify({'device_templates': [i.json for i in self._device_template_list]})


        #Add a new Device_adapter_template. Works. posting 2 times checked.
        @self.openiotfogagentapp_flask.route('/agent/v1/device_templates', methods=['POST'], strict_slashes=False)
        def device_template_add():
            # checks if the provided json is correct
            expected_json = {
                'device_adapter_name': 'GIVEN_NAME_BY_USER',
                'product_id': 'DEVICE_PRODUCT_ID',
                'vendor_id': 'DEVICE_VENDOR_ID'
            }
            print request.json

            if not request.json or 'device_adapter_name' not in request.json or 'product_id' not in request.json  or 'vendor_id' not in request.json:
                return make_response(jsonify({'error': 'Need proper JSON to create a container!','expected_json':expected_json}), 400)

            deviceadaptername = request.json['device_adapter_name']
            product_id = request.json['product_id']
            vendor_id = request.json['vendor_id']
            # Checking if deviceadaptername already exist
            device_template = get_device_template_by_name(deviceadaptername)
            # According to RFC 7231, a 303 can be used If the result of processing a POST would be equivalent to a representation of an existing resource.
            if device_template is not None:
                return make_response(jsonify({'error': 'Device template : >' + deviceadaptername + '< already used! use a different name'}), 303)

            # checking if deviceadater already exist for product id and vendor id
            device_template = get_device_template_by_productidvendorid(productid=product_id, vendorid=vendor_id)
            if device_template is not None:
                return make_response(jsonify({'error': 'Device template for product id and vendor id : >' + product_id +" "+ vendor_id + '< already used!'}), 303)

            # A device object created
            new_udev_device = TTYDevice(vendor_id=vendor_id, product_id=product_id)


            # device discovery always on. The moment a device template is created, it is on. We can see the list of attached devices, when the device is pluged in.
            #deviceadaptertmpl1 = DeviceAdapterTmpl(name="zigbeetemplate",udev_device=udev_device1, container_image=image1, device_discovery="on")
            device_adapter_tmpl = DeviceAdapterTmpl(name=deviceadaptername,udev_device=new_udev_device, device_discovery="on")

            self.register_device_adapter_tmpl(device_adapter_tmpl)

            return make_response(jsonify({'success': 'New device template successfully created!'}), 200)


        # shows details of the device templates.
        @self.openiotfogagentapp_flask.route('/agent/v1/device_templates/<string:name>', methods=['GET'], strict_slashes=False)
        def show_device_template(name):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            device_template = get_device_template_by_name(name)
            if device_template is not None:
                return make_response(jsonify(device_template.json), 200)
            else:
                return make_response(jsonify({'error': 'Device template: >' + name + '< not found!'}), 404)


        def get_device_template_by_name(name):
            for e in self._device_template_list:
                if e.name == name:
                    return e
            return None


        def get_device_template_by_productidvendorid(productid, vendorid):
            for e in self._device_template_list:
                if e.udev_device.vendor_id == vendorid and e.udev_device.product_id == productid:
                    return e
            return None

        # works. Checks if deletable. If a Swarm service is running using this template then it is not deletable.
        @self.openiotfogagentapp_flask.route('/agent/v1/device_templates/<string:name>', methods=['DELETE'], strict_slashes=False)
        def device_templates_delete(name):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            device_template = get_device_template_by_name(name)
            """ :type: DeviceAdapterTmpl """

            if device_template is not None:
                if device_template.deletable:
                    # self._device_template_list.remove(device_template)
                    # del device_template
                    self.unregister_device_adapter_tmpl(device_adapter_tmpl=device_template)
                    return make_response(jsonify({'success': 'Device template: >' + name + '< deleted!'}), 302)
                else:
                    return make_response(jsonify({'error': 'Device template: >' + name +
                                                           '< is not deletable!'}), 404)
            else:
                return make_response(jsonify({'error': 'Device template: >' + name + '< not found!'}), 404)



        # update device template. associate a container image or remove the image # Check for if Image already associated with devicetemplate
        @self.openiotfogagentapp_flask.route('/agent/v1/device_templates/<string:name>', methods=['PUT'], strict_slashes=False)
        def device_templates_update(name):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            device_template = get_device_template_by_name(name)
            """ :type: DeviceAdapterTmpl """

            if device_template is not None:
                # checks if the provided json is correct

                if device_template.container_autostart == True:
                    return make_response(jsonify({'error': 'An Image already associated with this device template!'}), 400)

                expected_json = {
                    'image_name': 'IMAGE_NAME_FROM_IMAGE_LIST'
                }
                if not request.json or 'image_name' not in request.json:
                    return make_response(jsonify({'error': 'Need proper JSON to create a container!', 'expected_json': expected_json}), 400)

                imagename = request.json['image_name']

                # check if image exist in the node. If not, return Image cannot be associated.
                # print imagename
                imageexist = get_image_by_name(name=imagename)
                print imageexist

                if imageexist != None:
                    # update device template
                    for n, i in enumerate(self._device_template_list):
                        if i.name == name:
                            self._device_template_list[n].container_image = imageexist # associate the image
                            self._device_template_list[n].set_container_autostart_on()  # set Container_autostart on so, it will setup the Container permission for swarm
                            self._device_template_list[n].set_as_notdeletable() # As an image is associated, So, may be a service is running with this device_template.So, This device_template is not deletable

                            # self._device_template_list[n].destroy_device_adapter_docker_swarm(tty_dev=self._device_template_list[n].udev_device)
                            # self._device_template_list[n].create_device_adapter_docker_swarm(tty_dev=self._device_template_list[n].udev_device)
                            #Set the image as not deletable. As a device template is using this image. It should not be deletable.
                            for m,j in enumerate(self._images_list):
                                if j.name == imageexist.name:
                                    self._images_list[m].set_notdeletable()
                    # TODO what to return. In my opinion return the updated device template
                    device_template = get_device_template_by_name(name)
                    if device_template is not None:
                        return make_response(jsonify(device_template.json), 200)
                    else:
                        return make_response(jsonify({'error': 'Device template: >' + name + '< not found!'}), 404)
                else:
                    return make_response(jsonify({'error': 'Image: >' + imagename + '< is not found in this Node! Image cannot be associated with this device_template'}), 400)


            else:
                return make_response(jsonify({'error': 'Device template: >' + name + '< not found!'}), 404)

        # Unassociate an image from device template
        @self.openiotfogagentapp_flask.route('/agent/v1/device_templates/<string:name>/<string:imagename>', methods=['DELETE'],strict_slashes=False)
        def remove_image_from_device_template(name,imagename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            device_template = get_device_template_by_name(name)
            if device_template!=None:
                if device_template.container_image.name == imagename:
                    for n, i in enumerate(self._device_template_list):
                        if i.name == name:
                            self._device_template_list[n].container_image = Container_Image()
                            self._device_template_list[n].set_container_autostart_off()
                            self._device_template_list[n].set_as_deletable()
                            for m,j in enumerate(self._images_list):
                                if j.name == imagename:
                                    self._images_list[m].set_deletable()
                            return make_response(jsonify(self._device_template_list[n].json), 200)

                else:
                    return make_response(jsonify({'error': 'Wrong Image name Given!'}),400)
            else:
                return make_response(jsonify({'error': 'Device template: >' + name + '< not found!'}), 404)



        # List all currently "running" device adapters
        @self.openiotfogagentapp_flask.route('/agent/v1/devices', methods=['GET'], strict_slashes=False)
        def devices():
            devices = {}
            for device_adapter_template in self._device_template_list:
                #TODO use logging

                # Use this to show full JSON description of each single device
                # device_adapters[device_adapter_template.name] =
                #   [i.json for i in device_adapter_template.all_device_adapters.values()]
                devices[device_adapter_template.name] = device_adapter_template.udev_device.json

            return jsonify({'devices': devices})

        # Show detailed information for a single device adapter
        @self.openiotfogagentapp_flask.route('/agent/v1/devices/<string:name>', methods=['GET'], strict_slashes=False)
        def device_detail(name):
            # Search all device_adapter_templates for this particular device name
            for device_adapter_template in self._device_template_list:
                for device_adapter in device_adapter_template.all_device_adapters.values():
                    if name == device_adapter.name:
                        return make_response(jsonify(device_adapter.json), 200)
            return make_response(jsonify({'error': 'Device: >' + name + '< not found!'}), 404)


        ########################################################################################################################
        ############## Following EndPoints are for Images   --------------------

        # list the images for this node : works
        @self.openiotfogagentapp_flask.route('/agent/v1/images', methods=['GET'], strict_slashes=False)
        def list_images():
            return jsonify({'images': [i.json for i in self._images_list]})


        #Adds a new image. Posting 2 times checked
        @self.openiotfogagentapp_flask.route('/agent/v1/images', methods=['POST'], strict_slashes=False)
        def image_add_to_node():
            # checks if the provided json is correct
            expected_json = {
                'image_name': 'GIVEN_NAME_BY_USER',  ## write now it's very basic. Only image name and it gets downloaded
                'tag': 'TAG_OF_LATEST_IMAGE'
            }
            if not request.json or 'image_name' not in request.json or 'tag' not in request.json:
                return make_response(jsonify({'error': 'Need proper JSON to create a container!','expected_json':expected_json}), 400)


            imagename = request.json['image_name']
            tag = request.json['tag']

            # check if already exist in the node
            print imagename
            imagealreadyexist = get_image_by_name(name=imagename)

            # print imagealreadyexist
            if imagealreadyexist!=None:
                print imagealreadyexist.json
                return make_response(jsonify({'error': 'Image: >' + imagename + '< already present in this node! Use PUT method to update to latest image'}),303)

            newimage = self.image_manager.image_pull(name=imagename,tag=tag)

            if newimage!= None and isinstance(newimage,Container_Image):
                self._images_list.append(newimage)
                return make_response(jsonify({'success': 'New docker image successfully added!'}), 200)
            else:
                return make_response(jsonify({'error': 'Could not add docker Image to the Node!'}), 400)


        def get_image_by_name(name):
            for e in self._images_list:
                print e.name
                # print type(e.name)
                # print type(name)
                if e.name == name:
                    # print True
                    return e
            return None

        # shows details of the image. works
        @self.openiotfogagentapp_flask.route('/agent/v1/images/<string:imagename>', methods=['GET'],
                                             strict_slashes=False)
        def show_image(imagename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            tempimage = get_image_by_name(imagename)
            if tempimage is not None:
                return make_response(jsonify(tempimage.json), 200)
            else:
                return make_response(jsonify({'error': 'Image: >' + imagename + '< not found!'}), 404)

        # update an image. works
        @self.openiotfogagentapp_flask.route('/agent/v1/images/<string:imagename>', methods=['PUT'],
                                             strict_slashes=False)
        def update_image(imagename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            expected_json = {
                'image_name': 'GIVEN_NAME_BY_USER',
            ## write now it's very basic. Only image name and it gets downloaded
                'tag': 'TAG_OF_LATEST_IMAGE'
            }
            if not request.json or 'image_name' not in request.json or 'tag' not in request.json:
                return make_response(
                    jsonify({'error': 'Need proper JSON to create a container!', 'expected_json': expected_json}), 400)

            imagename = request.json['image_name']
            tag = request.json['tag']

            # check if already exist in the node
            print imagename
            imagealreadyexist = get_image_by_name(name=imagename)

            print imagealreadyexist
            if imagealreadyexist != None:
                print imagealreadyexist.json
                # same tag. that means same image version
                if imagealreadyexist.name == imagename and imagealreadyexist.tag == tag:
                    return make_response(jsonify({'error': 'Image: >' + imagename + '< is already same version! Use a different version to update!'}),303)
                else:
                    # update image with new version(tag)
                    updatedimage=self.image_manager.update_image(imagealreadyexist,imagename=imagename,tag=tag )
                    for n, i in enumerate(self._images_list):
                        if i.name == updatedimage.name:
                            self._images_list[n] = updatedimage
                    return make_response(jsonify(updatedimage.json), 200)

            else:
                return make_response(jsonify({'error': 'Image: >' + imagename + '< is not present in the node! Use POST to add this Image.'}),303)


        # delete an image from the node. works
        @self.openiotfogagentapp_flask.route('/agent/v1/images/<string:imagename>', methods=['DELETE'],
                                             strict_slashes=False)
        def delete_image(imagename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            tempimage = get_image_by_name(imagename)
            if tempimage is not None:
                if tempimage.deletable:
                    imagedeleted = self.image_manager.image_delete(imagerepo=tempimage.repo,tag=tempimage.tag)
                    if imagedeleted:
                        self._images_list.remove(tempimage)
                        del tempimage
                        return make_response(jsonify({'success': 'Image: >' + imagename + '< deleted!'}), 302)

                else:
                    return make_response(jsonify({'error': 'Image: >' + imagename +'< is not deletable!'}), 404)
            else:
                return make_response(jsonify({'error': 'Image: >' + imagename + '< not found!'}), 404)


    def run(self, threaded=False, processes=1):
        try:
            self.debug = debug = True
            self.openiotfogagentapp_flask.register_blueprint(monitoring_blueprint)
            self.openiotfogagentapp_flask.debug = debug
            if self.monitoring == True:
                start_database()
                threads = [gevent.spawn(sense_monitoring_data)]
                http_server = WSGIServer(('', self.port), self._flask)
                threads.append(http_server.serve_forever())
                gevent.joinall(threads)
            self.openiotfogagentapp_flask.run(self.host, self.port, debug=debug, threaded=threaded, processes=processes)

        finally:
            if self.do_cleanup:
                self.default_cleanup()


    def register_device_adapter_tmpl(self, device_adapter_tmpl):
        """
        :type device_adapter_tmpl: DeviceAdapterTmpl
        :return:
        """
        import os
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not self.debug:
            # TODO:
            #
            # - Check whether this particular device adapter is already
            # available
            if device_adapter_tmpl in self._device_template_list:
                return
            #
            # - Check whether device discovery is supported and already
            # turned on
            if device_adapter_tmpl.is_discoverable and device_adapter_tmpl.is_discovery_on():
                    # TODO use logging
                    print("autostarting discovery because discoverable and discovery is on")
                    device_adapter_tmpl.start_device_discovery(self._dd)

            self._device_template_list.append(device_adapter_tmpl)

    def unregister_device_adapter_tmpl(self, device_adapter_tmpl):
        """
        :type device_adapter_tmpl: DeviceAdapterTmpl
        :return:
        """
        import os
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not self.debug:
            # TODO:
            print("removing discovery")
            device_adapter_tmpl.stop_device_discovery(self._dd)
            self._device_template_list.remove(device_adapter_tmpl)


if __name__ == '__main__':
    test = OpenIoTFogAgent()
    test.run()
