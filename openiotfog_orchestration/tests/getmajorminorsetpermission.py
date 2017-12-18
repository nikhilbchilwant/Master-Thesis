import os, sys
import time

import __future__
import docker
CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5
client = docker.APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

path = "/dev/ttyUSB0"

# Now get  the touple
info = os.lstat(path)
print info
# Get major and minor device number
major_dnum = os.major(info.st_rdev)
minor_dnum = os.minor(info.st_rdev)

print "Major Device Number :", major_dnum
print "Minor Device Number :", minor_dnum

### This module get the minor and major number for device and tries to setup permission for a container.

while 1:
    cid = client.containers(filters={"ancestor":"openmtc/zigbeeipe-amd64"})
    if cid != []:
        ContainerID=cid[0]['Id']
        print ContainerID
        permissionsetupcommand = "c "+str(major_dnum)+":"+str(minor_dnum)+" rwm"
        print permissionsetupcommand

        print "setting up permission: "

        with open("/sys/fs/cgroup/devices/docker/"+ContainerID+"/devices.allow", 'a') as the_file:
            the_file.write(permissionsetupcommand)
        time.sleep(1)
    else:
        pass

