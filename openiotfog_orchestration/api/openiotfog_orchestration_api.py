from flask import Flask, jsonify, Response, make_response, request
import requests
import socket
import docker, json
import netifaces as ni
import threading
import unicodedata

# Custom packages
from nodes import manager, PrimaryManager
from nodes import FogNode
from devices import knowndevice
from dockerimages import Container_Image
from services import GatewayService,ApplicationService

# configuration
from ConfigParser import SafeConfigParser

config = SafeConfigParser()
config.read('openiotfogorchestrator_config.ini')

# import config
# import global_config
#orchestrationapp = Flask(__name__)
#orchestrationapp.config.from_object('config')

## Client config for Docker library
CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5


# OpenIoTFogAgent_port = global_config.OpenIoTFogAgent_PORT
OpenIoTFogAgent_port = int(config.get('agent', 'OpenIoTFogAgent_PORT'))
def OpenIoTFogNodeURL(nodeip):
    url = 'http://' + nodeip + ':6000/agent/v1/'
    return url



class OpenIoTFogOrchestrator():

    def default_cleanup(self):

        #TODO delete all worker node. Nodes Leave Swarm
        for worker in self._worker_list:
            nodeip= worker.node_ip
            url = OpenIoTFogNodeURL(nodeip=nodeip)+'swarm_spec'
            # node leaves swarm
            r = requests.delete(url)
            if r.status_code == 200:
                # As we are destroying the Swarm. We don't need to remove node 1 by 1
                # client = docker.APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
                # # If lambda is not used, the functions is called, and then passed to the Timer function, so, lambda function, make it possible to wait
                # t = threading.Timer(30.0, lambda: client.remove_node(nodeip))
                # t.start()

                self._worker_list.remove(worker)
                del worker

        for manager in self._manager_list:
            manager.destroy()


    def __init__(self, do_cleanup=True, *args, **kw):

        # TODO: What's the proper name here?
        # self._flask = Flask(type(Orchestrator).__module__)

        self.orchestrationapp_flask = Flask(__name__)
        # self._flask.response_class = OrchestratorResponse

        # import the configuration from .ini file
        self.port = int(config.get('main', 'PORT'))
        self.interface = config.get('main', 'INTERFACE')

        self.ip = ni.ifaddresses(self.interface)[2][0]['addr']
        self.host = self.ip

        # #Import the configurations
        # self.orchestrationapp_flask.config.from_object('config')
        # #assign the configuration to flask app
        # self.host = self.orchestrationapp_flask.config['HOST']
        # self.port = self.orchestrationapp_flask.config['PORT']
        # self.interface = self.orchestrationapp_flask.config['INTERFACE']


        self._manager_list = []
        # TODO is it necessary?
        self._node_list = []
        self._worker_list = []

        # all known devices
        self._known_device_list= []

        # all known images
        self._known_image_list= []

        # all running service list (with mapping to node, image, device)
        self._gateway_service = []

        self._application_service_list = []

        self.do_cleanup = do_cleanup

        hostname = socket.gethostname()
        #print hostname
        #print ni.ifaddresses('eth0') //prints ip
        ip = ni.ifaddresses(self.interface)[2][0]['addr']

        self._primarymanager = PrimaryManager(manager_name=hostname + "manager1", advertise_addrs=ip)
        #print jsonify(primarymanager.json)
        self._manager_list.append(self._primarymanager)

        @self.orchestrationapp_flask.route('/openiotfogorc/v1',strict_slashes=False)
        def index():
            return """<xmp> Docker Swarm initialized
            /nodes : to see the nodes
            /services: to see the services
            /devices: known devices
            /images: known images for the cluster
            </xmp>"""


        ## Cluster level management
        ## List images from the registry
        ## Add images to the registry
        ## Delete Image from Registry

        #######################################################################################################
        ### Node Management
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/nodes', methods=['GET'], strict_slashes=False)
        def nodes():
            all_worker_nodes = []

            for worker in self._worker_list:
                all_worker_nodes.append(worker.json)

            return make_response(json.dumps(all_worker_nodes),200)

        @self.orchestrationapp_flask.route('/openiotfogorc/v1/nodes', methods=['POST'], strict_slashes=False)
        def add_node():
            # json-schema here
            expected_json = {
                'nodeip': {
                    'type': 'string',
                    'required': True
                },
                'layer': {
                    'type': 'string',
                    'allowed': ['Fog', 'Edge'],
                    'required': True,
                },
            }
            if not request.json or 'nodeip' not in request.json or 'layer' not in request.json:
                return make_response(jsonify({'error': 'Need proper JSON to create a container!','expected_json':expected_json}), 400)

            # TODO: Check weather POSTing 2 time returns error (check if this node is part of swarm cluster)

            # Join a new Swarm Cluster based on the configuration
            nodeip = request.json['nodeip']
            layer = request.json['layer']
            remotemanager = self._primarymanager.advertiseaddr
            token = self._primarymanager.join_token
            # url = 'http://'+nodeip+':6000/orch/v1'
            url = OpenIoTFogNodeURL(nodeip=nodeip)
            data = {'remotemanager': remotemanager, 'token': token}
            headers = {'Content-Type': 'application/json'}

            r = requests.post(url, data=json.dumps(data), headers=headers)
            print r.content
            contents = json.loads(r.content)
            nodeip=contents['NodeIP']
            #print nodeip
            nodeid=contents['NodeID']
            nodehostname = contents['Nodehostname']
            nodestatus= "Active"
            nodelayer=layer
            # nodeip="",nodeid="",nodestatus= "",nodelayer="")
            # print r.json()
            if r.status_code == 200:
                fognode =FogNode(nodeip=nodeip,nodeid=nodeid,nodehostname=nodehostname,nodestatus=nodestatus,nodelayer=nodelayer)
                self._worker_list.append(fognode)

            #return jsonify(r.json())
            for worker in self._worker_list:
                return make_response(jsonify(worker.json))

        # Get Node details
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/nodes/<string:nodeid>', methods=['GET'], strict_slashes=False)
        def get_node_details_by_id(nodeid):
            # TODO read from DB and return details of the node. At this point database if more important to make the cluster state persistent. Not only variable from Class object. Use ORM Object relation Mapping (e.g. MongoEngine)
            for worker in self._worker_list:
                if worker.node_id == nodeid:
                    return make_response(jsonify(worker.json),200)
            return make_response(jsonify({'error':'node >'+nodeid+'< not found!'}),404)

        # Delete Node
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/nodes/<string:nodeid>', methods=['DELETE'], strict_slashes=False)
        def delete_node_by_id(nodeid):
            #TODO read from DB and remove node from cluster and from DB
            for worker in self._worker_list:
                if worker.node_id == nodeid:
                    nodeip= worker.node_ip
                    url = OpenIoTFogNodeURL(nodeip=nodeip)+'swarm_spec'
                    # node leaves swarm
                    r = requests.delete(url)
                    if r.status_code == 200:
                        self._worker_list.remove(worker)
                        del worker
                        # remove from swarm node list (docker node rm )
                        client = docker.APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
                        # If lambda is not used, the functions is called, and then passed to the Timer function, so, lambda function, make it possible to wait
                        t =  threading.Timer(30.0, lambda: client.remove_node(nodeid))
                        t.start()

                        return make_response(jsonify({'success': 'node >' + nodeip + '< successfully removed!'}), 200)
                    else:
                        return make_response(jsonify({'error': 'node >' + nodeip + '< could not be removed!'}), r.status_code)

            return make_response(jsonify({'error': 'node >' + nodeid + '< not found!'}), 404)


        # TODO Add a label to the node (in swarm node, list, DB)
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/nodes/<string:nodeid>', methods=['PUT'], strict_slashes=False)
        def update_node_details_by_id(nodeid):
            #TODO read from DB and update node with a label, both in db and in swarm
            # json-schema here
            expected_json = {
                'layer': {
                    'type': 'string',
                    'allowed': ['Fog', 'Edge'],
                    'required': True
                },
                'label': {
                    'type': 'string',
                    'required': True
                }
            }

            if not request.json or 'label' not in request.json:
                return make_response(jsonify({'error': 'Need proper JSON to create a container!'}), 400)
            #nodelayer = request.json['layer']
            nodelabel = request.json['label']
            node_spec = {
                'Availability': 'active',
                'Role': 'worker',
                'Labels': {'NodeTAG': nodelabel}
            }
            # {'Availability': 'active',
            #  'Name': 'node-name',
            #  'Role': 'manager',
            #  'Labels': {'foo': 'bar'}
            #  }

            for worker in self._worker_list:
                if worker.node_id == nodeid:


                    # using high level API in docker py
                    client = docker.from_env(version=CLI_VERSION)
                    Node = client.nodes.get(nodeid)
                    updatesuccess = Node.update(node_spec)

                    #low level API of docker-py, update method needs a version
                    #client = docker.APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
                    #client.update_node(node_id=nodeid, version=8, node_spec=node_spec)

                    if updatesuccess:
                        # update label in object
                        print nodelabel
                        print type(nodelabel)
                        nodelabelinaschii = unicodedata.normalize('NFKD', nodelabel).encode('ascii', 'ignore')
                        print nodelabelinaschii, type(nodelabelinaschii)
                        worker.set_node_label(nodelabelinaschii)
                        return make_response(jsonify(worker.json), 200)
                        #return make_response(jsonify({'success': 'node >' + worker.node_ip + '< successfully updated with new label!'}), 200)
                    else:
                        return make_response(jsonify({'error': 'node >' + worker.node_ip + '< could not be updated!'}),
                                             500)
            return make_response(jsonify({'error': 'node >' + nodeid + '< not found!'}), 404)



        ##############################################################################################################
        ## Image management
        # List the images
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/images', methods=['GET'], strict_slashes=False)
        def list_docker_images():
            return jsonify({'known_images': [i.json for i in self._known_image_list]})

        # Add a new image and Node downloads it
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/images', methods=['POST'], strict_slashes=False)
        def add_docker_images_in_orchestrator():
            # checks if the provided json is correct
            expected_json = {
                'image_name': 'GIVEN_NAME_BY_USER',
                'tag': 'TAG_OF_LATEST_IMAGE'
            }
            if not request.json or 'image_name' not in request.json or 'tag' not in request.json:
                return make_response(
                    jsonify({'error': 'Need proper JSON to add a known image!', 'expected_json': expected_json}), 400)

            imagename = request.json['image_name']
            tag = request.json['tag']

            # check if already exist in the node
            # print imagename
            imagealreadyexist = get_image_by_name(name=imagename)

            # print imagealreadyexist
            if imagealreadyexist != None:
                print imagealreadyexist.json
                return make_response(jsonify({'error': 'Image: >' + imagename + '< already present in this node! Use PUT method to update to latest image'}),303)

            newimage = Container_Image(image_name=imagename,image_tag=tag)

            if newimage != None and isinstance(newimage, Container_Image):
                self._known_image_list.append(newimage)
                return make_response(jsonify({'success': 'New docker image successfully added!'}), 200)
            else:
                return make_response(jsonify({'error': 'Could not add docker Image to the Node!'}), 400)

        def get_image_by_name(name):
            for e in self._known_image_list:
                if e.name == name:
                    # print True
                    return e
            return None

        # details the image name, id etc. in the Node
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/images/<string:imagename>', methods=['GET'], strict_slashes=False)
        def details_docker_image_by_name(imagename):
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


        # Delete the image from the Node.
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/images/<string:imagename>', methods=['DELETE'], strict_slashes=False)
        def delete_docker_image_by_imagename(imagename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            tempimage = get_image_by_name(imagename)
            if tempimage is not None:
                if tempimage.deletable:
                    self._known_image_list.remove(tempimage)
                    del tempimage
                    return make_response(jsonify({'success': 'Image: >' + imagename + '< deleted!'}), 302)

                else:
                    return make_response(jsonify({'error': 'Image: >' + imagename +'< is not deletable!'}), 404)
            else:
                return make_response(jsonify({'error': 'Image: >' + imagename + '< not found!'}), 404)

        # Change the image from the Node.
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/images/<string:imagename>', methods=['PUT'], strict_slashes=False)
        def modify_docker_image_in_node_by_imagename(imagename):
            """
            :type imagename: str | unicode
            :param imagename:
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

            newimagename = request.json['image_name']
            tag = request.json['tag']

            # check if already exist in the node
            # print imagename
            imagealreadyexist = get_image_by_name(name=imagename)

            # if imagealreadyexist then, it's possible to update
            if imagealreadyexist != None:
                # TODO logging print imagealreadyexist.json
                # same tag. that means same image version
                if imagealreadyexist.name == newimagename and imagealreadyexist.tag == tag:
                    return make_response(jsonify({'error': 'Image: >' + imagename + '< is already same version! Use a different version to update!'}),303)

                #only change the name of the image, not repository, not tag
                elif imagealreadyexist.name != newimagename:
                    # update image with new imagename
                    for n, i in enumerate(self._known_image_list):
                        if i.name == imagename:
                            self._known_image_list[n].set_image_name(newimagename=newimagename)
                    return make_response(jsonify(self._known_image_list[n].json), 200)

                elif imagealreadyexist.tag != tag:
                    if imagealreadyexist.deletable == True:
                        for n, i in enumerate(self._known_image_list):
                            if i.name == imagename:
                                self._known_image_list[n].set_image_tag(newtag=tag)
                                return make_response(jsonify(self._known_image_list[n].json), 200)
                    else:
                        return make_response(jsonify({'error': 'Image: >' + imagename + '< is not possible to update! It is being used by some service'}),400)

            else:
                return make_response(jsonify(
                    {'error': 'Image: >' + imagename + '< is not present in the known image list! Use POST to add this Image.'}), 303)

        ##############################################################################################################
        ## Device Management
        # List devices. This devices are known to all Fog Nodes
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/devices', methods=['GET'], strict_slashes=False)
        def list_devices():
            #TODO read from openiotfogagent, which provides details of images
            return jsonify({'known_devices': [i.json for i in self._known_device_list]})

        # Add a new device to the orchestrator. This device will be know to all Node
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/devices', methods=['POST'], strict_slashes=False)
        def add_device_in_orchestrator_devicelist():
            expected_json = {
                'device_name': 'GIVEN_NAME_BY_USER',
                'product_id': 'DEVICE_PRODUCT_ID',
                'vendor_id': 'DEVICE_VENDOR_ID'
            }
            if not request.json or 'device_name' not in request.json or 'product_id' not in request.json  or 'vendor_id' not in request.json:
                return make_response(jsonify({'error': 'Need proper JSON to add a device type!','expected_json':expected_json}), 400)

            devicename = request.json['device_name']
            product_id = request.json['product_id']
            vendor_id = request.json['vendor_id']

            # Checking if deviceadaptername already exist
            device_template = get_device_template_by_name(devicename)
            # According to RFC 7231, a 303 can be used If the result of processing a POST would be equivalent to a representation of an existing resource.
            if device_template is not None:
                return make_response(jsonify(
                    {'error': 'Device : >' + devicename + '< already used! use a different name'}), 303)

            # checking if deviceadater already exist for product id and vendor id
            device_template = get_device_template_by_productidvendorid(productid=product_id, vendorid=vendor_id)
            if device_template is not None:
                return make_response(jsonify({'error': 'Device for product id and vendor id : >' + product_id + " " + vendor_id + '< already used!'}),303)

            # A device object created
            new_device = knowndevice(devicename=devicename,vendor_id=vendor_id, product_id=product_id)

            self._known_device_list.append(new_device)

            return make_response(jsonify({'success': 'New device successfully created!'}), 200)

        def get_device_template_by_name(name):
            for e in self._known_device_list:
                if e.device_name == name:
                    return e
            return None

        def get_device_template_by_productidvendorid(productid, vendorid):
            for e in self._known_device_list:
                if e.vendor_id == vendorid and e.product_id == productid:
                    return e
            return None

        # Get details of the device template. product_id, vendor_id and device type name
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/devices/<string:devicename>', methods=['GET'], strict_slashes=False)
        def show_details_of_device(devicename):
            device = get_device_template_by_name(devicename)
            if device is not None:
                return make_response(jsonify(device.json), 200)
            else:
                return make_response(jsonify({'error': 'Device template: >' + devicename + '< not found!'}), 404)

        # delete device from the known device list
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/devices/<string:devicename>', methods=['DELETE'],strict_slashes=False)
        def delete_device_by_devicename(devicename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            device = get_device_template_by_name(devicename)
            """ :type: knowndevice """

            if device is not None:
                self._known_device_list.remove(device)
                del device
                return make_response(jsonify({'success': 'device type: >' + devicename + '< deleted!'}), 302)
            else:
                return make_response(jsonify({'error': 'Device template: >' + devicename + '< not found!'}), 404)

        # Update the name for the device(vendor_id, product_id)
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/devices/<string:existingdevicename>', methods=['PUT'],strict_slashes=False)
        def update_devicename_productdendor(existingdevicename):
            device = get_device_template_by_name(existingdevicename)
            if device is not None:
                expected_json = {
                    'device_name': 'GIVEN_NAME_BY_USER',
                    'product_id': 'DEVICE_PRODUCT_ID',
                    'vendor_id': 'DEVICE_VENDOR_ID'
                }
                if not request.json or 'device_name' not in request.json or 'product_id' not in request.json or 'vendor_id' not in request.json:
                    return make_response(jsonify({'error': 'Need proper JSON to create a device type!', 'expected_json': expected_json}),400)

                newdevicename = request.json['device_name']
                product_id = request.json['product_id']
                vendor_id = request.json['vendor_id']

                # Checking if deviceadaptername already exist
                device_template = get_device_template_by_name(newdevicename)
                # According to RFC 7231, a 303 can be used If the result of processing a POST would be equivalent to a representation of an existing resource.
                if device_template is not None:
                    return make_response(jsonify(
                        {'error': 'Device : >' + newdevicename + '< already used! use a different name'}), 303)

                # checking if deviceadater already exist for product id and vendor id
                device_template = get_device_template_by_productidvendorid(productid=product_id, vendorid=vendor_id)
                if device_template is not None:
                    return make_response(jsonify({'error': 'Device type for product id and vendor id : >' + product_id + " " + vendor_id + '< already used!'}),303)


                for n, i in enumerate(self._known_device_list):
                    if i.device_name == existingdevicename:
                        self._known_device_list[n].set_device_name(newdevicename=newdevicename)
                        self._known_device_list[n].set_vendor_id(vendorid=vendor_id)
                        self._known_device_list[n].set_product_id(productid=product_id)
                return make_response(jsonify(self._known_device_list[n].json), 200)
            else:
                return make_response(jsonify({'error': 'Device: >' + existingdevicename + '< not found!'}), 404)


        ## Service Management #######################################################################################################################

        # Start Gateway Service for whole cluster
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/services/gw_service', methods=['GET'], strict_slashes=False)
        def create_gw_service_for_cluster():
            gw = GatewayService(servicename="OpenIoTFog-Gateway",serviceport={8000:8000})
            if gw !=None:
                val, err = gw.start_swarm_service()
                if val==True:
                    self._gateway_service.append(gw)
                    return make_response(jsonify({'success': 'Gateway successfully created and started!'}), 200)
                else:
                    return make_response(jsonify({'error': 'Gateway couldnot be started!','error_message':str(err)}), 200)

        # Stop Gateway Service for whole cluster
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/services/gw_service/stop', methods=['GET'],
                                           strict_slashes=False)
        def stop_gw_service_for_cluster():
            gw_stop, err = self._gateway_service[0].stop_swarm_service()
            if gw_stop==True:
                service = get_GW_service_by_name(name="OpenIoTFog-Gateway")
                self._gateway_service.remove(service)
                return make_response(jsonify({'success': 'Gateway successfully stopped!'}), 200)
            else:
                return make_response(jsonify({'error': 'Gateway couldnot be stopped!', 'error_message': str(err)}), 200)

        def get_GW_service_by_name(name):
            for e in self._gateway_service:
                if e.service_name == name :
                    # print True
                    return e
            return None
        ###############################################################################################################
        # Application Service
        #List Global Service
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/services', methods=['GET'], strict_slashes=False)
        def list_all_services():
            # TODO read from openiotfogagent, which provides details of images
            return jsonify({'services': [i.json for i in self._application_service_list]})

        ##List the running services in the Node
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/services/', methods=['POST'], strict_slashes=False)
        def add_new_service():
            # checks if the provided json is correct  #test = Service(servicename='culservice',nodehostname='worker1',devicename="/dev/ttyACM0",imagename='dregistry.fokus.fraunhofer.de:5000/tests/openmtcculipe')
            expected_json = {
                'service_name': 'GIVEN_NAME_BY_USER',
                'node_hostname': 'CHECK_NODE_HOSTNAME',
                'device_name': 'ATTACHED_DEVICE_NAME',
                'image_name': 'AVAILABLE_IMAGE_ON_NODE'
            }
            if not request.json or 'service_name' not in request.json or 'node_hostname' not in request.json or 'device_name' not in request.json or 'image_name' not in request.json:
                return make_response(
                    jsonify({'error': 'Need proper JSON to add a known image!', 'expected_json': expected_json}), 400)

            servicename = request.json['service_name']
            nodehostname = request.json['node_hostname']
            devicename = request.json['device_name']
            imagename = request.json['image_name']

            # check if already exist in the node
            # print imagename
            servicealreadyexist = get_service_by_name(name=servicename)

            # print servicealreadyexist
            if servicealreadyexist != None:
                print servicealreadyexist.json
                return make_response(jsonify({'error': 'Service: >' + servicename + '< already running in this node!'}),303)

            # checking if Service is running with that node with that image with a different name
            servicealreadyexist = get_service_by_hostname_image(hostname=nodehostname, image=imagename)

            if servicealreadyexist != None:
                print servicealreadyexist.json
                return make_response(jsonify({'error': 'Service: >' + servicename + '< already running in this node with a different name using same Image!'}),303)


            # test = Service(servicename='culservice',nodehostname='worker1',devicename="/dev/ttyACM0",imagename='dregistry.fokus.fraunhofer.de:5000/tests/openmtcculipe',envvar=[""EP=http://192.168.1.115:8000""])
            print "debug3 in the POST:" +  nodehostname
            node= get_node_by_hostname(nodehostname=nodehostname)
            print node.node_hostname
            if node == None:
                return make_response(jsonify({'error': 'Could not start Swarm Service in this node! Node does not exist. Check node_hostname :'}), 400)

            newservice = ApplicationService(servicename=servicename,nodehostname=nodehostname,devicename=devicename,imagename=imagename,envvar=["EP=http://"+str(node.node_ip)+":8000"])

            returnvalue, errormessage = newservice.start_swarm_service()

            if returnvalue==True:
                self._application_service_list.append(newservice)
                return make_response(jsonify({'success': 'New Swarm Service successfully started!'}), 200)
            else:
                return make_response(jsonify({'error': 'Could not start Swarm Service in this node! Error:'+str(errormessage)}), 400)

        def get_node_by_hostname(nodehostname):
            print "debug2:" +  nodehostname
            for e in self._worker_list:
                print "debug2:" +  e.node_hostname
                if e.node_hostname == nodehostname:
                    return e
            return None

        def get_service_by_name(name):
            for e in self._application_service_list:
                if e.service_name == name :
                    # print True
                    return e
            return None

        def get_service_by_hostname_image(hostname, image):
            for e in self._application_service_list:
                if e.nodehostname == hostname and e.image == image:
                    return e
            return None

        def get_node_ip_by_hostname(nodehostname):
            for e in self._node_list:
                if e.nodehostname == nodehostname:
                    return e
            return None


        #Provide details of a Service
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/services/<string:servicename>', methods=['GET'], strict_slashes=False)
        def show_details_a_service(servicename):
            service = get_service_by_name(servicename)
            if service is not None:
                return make_response(jsonify(service.json), 200)
            else:
                return make_response(jsonify({'error': 'Service: >' + servicename + '< not found!'}), 404)


        # delete a service
        @self.orchestrationapp_flask.route('/openiotfogorc/v1/services/<string:servicename>', methods=['DELETE'],strict_slashes=False)
        def delete_service_by_servicename(servicename):
            """
            :type name: str | unicode
            :param name:
            :return: Response
            """
            service = get_service_by_name(servicename)

            if service is not None:
                returnval, errormsg = service.stop_swarm_service()
                if returnval == True:
                    self._application_service_list.remove(service)
                    del service
                    return make_response(jsonify({'success': 'Service: >' + servicename + '< stoped and deleted!'}), 302)
                else:
                    return make_response(jsonify({'error': 'Service: >' + servicename + '< could not be removed! Error: '+str(errormsg)}), 404)
            else:
                return make_response(jsonify({'error': 'Service: >' + servicename + '< not found!'}), 404)

    def run(self, threaded=False, processes=1):
        try:
            self.debug = debug = True
            self.orchestrationapp_flask.run(self.host, self.port, debug=debug, threaded=threaded, processes=processes, use_reloader=False)
        finally:
            if self.do_cleanup:
                self.default_cleanup()

if __name__ == '__main__':
    test = OpenIoTFogOrchestrator()
    test.run()