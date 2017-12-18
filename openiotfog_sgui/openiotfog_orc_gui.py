from gevent import monkey
monkey.patch_all()

import json
from flask import Flask, request
from flask import render_template, flash, redirect,request
import netifaces as ni
import requests

# configuration
from ConfigParser import SafeConfigParser

config = SafeConfigParser()
configFilePath = 'openiotfog_gui_config.ini'
config.read(configFilePath)

# import the configuration from .ini file
guiendpointport = int(config.get('endpoint', 'PORT'))
guiendpointinterface = config.get('endpoint', 'INTERFACE')
guiendpointip = ni.ifaddresses(guiendpointinterface)[2][0]['addr']
guiendpointhost = guiendpointip

image_registry = config.get('image_config', 'image_registry')
orchestrator_endpoint = config.get('orchestrator_config','endpoint')



# import the websockets
from web_sockets import *

#custom import
from forms import NodeaddForm, ImageaddForm, DeviceForm

guiapp = Flask(__name__)
guiapp.config.from_object(__name__)
guiapp.config['SECRET_KEY'] = '7d441f27d441f27567d441f2b6176a'
guiapp.config["DEBUG"] = True
# This is view
@guiapp.route('/')
@guiapp.route('/index')
def index():
    return render_template('index.html',
                           title="OpenIoTFog Orchestration Toolkit")


@guiapp.route('/nodes', methods=['GET', 'POST'])
def show_nodes():
    form = NodeaddForm()

    if request.method == 'POST':
        if form.validate() == False:
            flash('All fields are required.')
            return render_template('nodes.html',title='Nodes', form=form)
        else:
            nodeip= str(form.data['ip'])
            nodelayer = str(form.data['layer'])
            print nodeip, nodelayer
            url = 'http://' + orchestrator_endpoint + 'nodes'
            data = {"nodeip": nodeip, "layer": nodelayer}
            headers = {'Content-Type': 'application/json'}

            r = requests.post(url, data=json.dumps(data), headers=headers)
            print r.content

            return render_template('nodes.html',title='Nodes', form=form)

    elif request.method == 'GET':
        return render_template('nodes.html',
                               title='Nodes', form=form)


@guiapp.route('/nodes/<string:nodeid>', methods=['GET', 'POST'])
def show_node(nodeid):
    imageform = ImageaddForm()
    deviceform = DeviceForm()
    print nodeid
    headers = {'Content-Type': 'application/json'}
    url = "http://"+orchestrator_endpoint+'nodes/'+nodeid
    r = requests.get(url, headers=headers)
    responce =  json.loads(r.content)
    print type(responce), responce['node_hostname']
    return render_template('node.html',
                           title='Node Status',nodehostname=responce['node_hostname'],nodedetail=responce)


@guiapp.route('/devices', methods=['GET', 'POST'])
def show_devices():
    return render_template('devices.html',
                           title='Supported Devices and Machines')

@guiapp.route('/dockerimages', methods=['GET', 'POST'])
def show_images():
    return render_template('dockerimages.html',
                           title='Docker Images')

@guiapp.route('/swarmservices', methods=['GET', 'POST'])
def show_services():
    return render_template('swarmservices.html',
                           title='Services')


# guiapp.run(debug=True,port=5006)
# socketio = SocketIO(guiapp)
socketio.init_app(guiapp)
#
# if __name__ == '__main__':
#     socketio.run(guiapp,port=8080)


if __name__ == '__main__':
    socketio.run(guiapp,host=guiendpointhost,port=guiendpointport)