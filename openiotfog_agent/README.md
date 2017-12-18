# OpenIoTFog Agent
OpenIoTFog Agent is a micro-service that run on each Fog Node. 

## Functionality
* Monitor the Node Condition (Work of Mathias)
* Monitor the attached Devices 
* Maintain a list of Known Devices
* Maintain a list of Attached Devices
* Can Join/Leave a Swarm Cluster
* When Central Orchestrator Starts a Swarm Service, Agent manages the permission issue.


## API 
OpenIoTFog Agent provides an API. 

The Endpoints are listed here in groups: 

The PORT is by default 6000 for Agent. But, it is configurable in config file.

### Base Endpoint

* IP:6000/agent/v1

### Cluster Endpoints

Usually, user do not have to use/run these endpoint (Other than for testing). Orchestrator communicates with these endpoints of the Agent-API.

* IP:6000/agent/v1 [POST]
* IP:6000/agent/v1/swarm_spec [GET]
* IP:6000/agent/v1/swarm_spec [DELETE]
* IP:6000/agent/v1/swarm_spec [PUT]
* 

### Device Endpoints

* IP:6000/agent/v1/device_templates [GET]
* IP:6000/agent/v1/device_templates [POST]
* IP:6000/agent/v1/device_templates/templatename [GET]
* IP:6000/agent/v1/device_templates/templatename [DELETE]
* IP:6000/agent/v1/device_templates/templatename [PUT]

attached devices
* IP:6000/agent/v1/devices' [GET]
* IP:6000/agent/v1/devices/devicename' [GET]



### Image Endpoints
Lists all the (registered) OpenIoTFog images in this node.
* IP:6000/agent/v1/images [GET]

Download from private registry server in the node and Add (register) a the Image in Agent.
* IP:6000/agent/v1/images [POST]

Show the details of a registered image in this node.
* IP:6000/agent/v1/images/imagename [GET]

Update a registered Image in this Node. Requires when there is a new Image version available. The newer Image must have a different TAG.
* IP:6000/agent/v1/images/imagename [PUT]

Unregister and Delete an Image from this node.
* IP:6000/agent/v1/images/imagename [DELETE]