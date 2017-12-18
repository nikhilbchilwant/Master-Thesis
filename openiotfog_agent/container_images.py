from docker import APIClient
import docker

CLI_VERSION = 'auto'
CLI_STOP_TIMEOUT = 5


class Container_Image():
    def __init__(self, image_name="",image_repo="", image_id="",image_tag="", *args, **kw):
        """
        :type image_name: str | unicode
        :type image_id: str | unicode
        :type image_tag: str | unicode
        :param image_name:
        :param image_tag:
        :param image_id:
        :param image_data:
        :param args:
        :param kw:
        """

        # Use case for already prepared container images (undeletable)

        self._name = image_name
        """ :type: str | unicode"""
        self._repo = image_repo
        """ :type: str | unicode"""
        self._tag = image_tag
        self._id = image_id
        """ :type: str | unicode"""
        self._deletable = True
        """ :type: bool"""

    @property
    def name(self):
        return self._name

    @property
    def repo(self):
        return self._repo

    @property
    def tag(self):
        return self._tag

    @property
    def id(self):
        return self._id


    @property
    def deletable(self):
        # returns true if no Container is using the docker image
        return self._deletable # and not ContainerTmpl.is_image_used(self.ID) # TODO add correct checker. it is used in any device template? if no deletable

    def set_deletable(self):
        self._deletable = True

    def set_notdeletable(self):
        self._deletable = False

    @property
    def json(self):
        return {
            "image_name": self.name,
            "image_repo": self.repo,
            "image_tag": self.tag,
            "image_id": self.id,
            "deletable": self.deletable
        }

    @staticmethod
    def json_schema():
        return {
            "type": "object",
            "properties": {
                "image_name": {"type": "string"},
                "image_repo": {"type": "string"},
                "image_tag": {"type": "string"},
                "image_id": {"type": "string"},
                "deletable": {"type": "boolean"}
            }
        }


    def destroy(self):
        #return self._docker_destroy_image()
        del self

    def __del__(self):
        self.destroy()

    # TODO It will remove Image from Node when delete from the image_list. but when remove an object of this class the Image will not be removed from the host.
    def _docker_destroy_image(self):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        imagename = self._name
        tag = self._tag
        if self.deletable:
            try:
                cli.remove_image(imagename)
            except:
                #self.logger.error("Could not delete image: " + str(imagename))
                print("Could not delete image: " + str(imagename))
                return False
        else:
            #self.logger.error("Image is not deletable image")
            print("Image is not deletable image")
            return False
        return True

    def _docker_image_verify(self):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        imagename = self.name
        imageid = self.ID
        tempimage = cli.images(imagename)

        if bool(tempimage):
            if tempimage[0]['Id'] == imageid:
                return True
        return False


class Container_Image_Manager():
    def __init__(self, imageregistry="", auth="", *args, **kw):
        """
        :type imageregistry: str | unicode
        :type auth: dictionary | unicode
        :param imageregistry:
        :param auth:
        :param args:
        :param kw:
        """
        self._imageregisty = imageregistry
        self._auth = auth
        """ :type: dictionary"""

    # Pulls an image from the registry server and create & returns an Container_Image object.
    def image_pull(self, name, tag):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

        imagerepo = self._imageregisty+ name
        # print imagerepo,tag

        imagestatus = cli.pull(repository=imagerepo,tag=tag,auth_config=self._auth)

        imageexist = self._verify_image_exist_nametag(imagerepo=imagerepo,tag=tag) # checks if pulled successfully
        # print imageexist

        if imageexist != None: # pulled the image successfully
            print imageexist['RepoTags'][0]     # prints reponame + tag
            print imageexist['Id']              # prints the ID

            reponametag = imageexist['RepoTags'][0].split(name+':') # split before name
            reponame = reponametag[0]+name # localhost:5000/ + zigbeeipe
            tag = reponametag[1] # only tag (e.g. 'v2')
            imageid = imageexist['Id']
            # print name
            # print reponame
            # print tag
            # print imageid

            newimage = Container_Image(image_name=name,image_repo=reponame,image_tag=tag,image_id=imageid)
            return newimage  # return the new image.
        else:
            return None

        # #TODO logging


    # callable with this object.
    # works (similar to docker rmi)
    def image_delete(self,imagerepo,tag):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        image = imagerepo+":"+tag
        imagestatus = cli.remove_image(image)
        imageexist = self._verify_image_exist_nametag(imagerepo=imagerepo, tag=tag)  # checks if deleted successfully
        if imageexist == None:
            return True
        else:
            return False







    # internal method
    def _verify_image_exist(self, imagerepo):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)

        tempimage = cli.images(imagerepo)

        # for i in tempimage:
        #     for k,v in i.items():
        #         print k,v

        # it will be problematic if there are same image with multiple tag. In that case, they all have same Image ID. And tempimage will be a list of Image.
        # for key,val in tempimage[0].items():
        #     print key,val
        if bool(tempimage):
            return tempimage[0]
        return None

    # internal method
    # This method checks for Image with name, tag. In this case, it will return only one Image
    def _verify_image_exist_nametag(self,imagerepo,tag):
        cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
        imagerepotag = imagerepo+":"+tag
        tempimage = cli.images(imagerepotag)
        # print tempimage
        # for i in tempimage:
        #     for k,v in i.items():
        #         print k,v
        if bool(tempimage):
            return tempimage[0]
        return None



    # when there is update. Check the tag. If the tag is different, pull image, create Container_Image object and replace the existing object.
    # If the object is deletable replace it.
    # If the object is not deletable, then stop the running Container, delete the old image, pull the new image. replace the image object
    def update_image(self, containerimage, imagename,tag):

        # This should be very carefully written. When the image is not deletable/ is being used. We have to download latest image and stop the container being used from this image. This is one real scenario of Container restart.
        # Latest Image will have a different Image ID. So, if image ID changes, update image otherwise no.

        imageregistry = self._imageregisty
        imagerepo = imageregistry+ imagename

        # if containerimage is not being used and deletable -> update
        if containerimage.deletable:
            imagedeleted = self.image_delete(imagerepo=containerimage.repo,tag=containerimage.tag)
            if imagedeleted:
                newimage = self.image_pull(imagename,tag)
                containerimage = newimage
                return containerimage
        else: # if container image not deletable then it is being used by any service
            cli = APIClient(base_url='unix://var/run/docker.sock', version=CLI_VERSION)
            # get the Container ID/Name, Stop the Container. Delete image, Pull new image
            cid = cli.containers(filters={"ancestor": imagename})
            if cid != []:
                ContainerID = cid[0]['Id']
                print("stoping container with ID:"+str(ContainerID))
                # Stop the container
                try:
                    res = cli.stop(ContainerID, timeout=CLI_STOP_TIMEOUT)
                except docker.errors.APIError as e:
                    #TODO logging
                    print str(e)

                # Delete image, pull new Image
                imagedeleted = self.image_delete(imagerepo=containerimage.repo, tag=containerimage.tag)
                if imagedeleted:
                    newimage = self.image_pull(imagename, tag)
                    containerimage = newimage
                    return containerimage




if __name__ == '__main__':
    auth = {'username': 'hsa', 'password': ''}
    registry = "localhost:5000/"
    testimagehandler = Container_Image_Manager(imageregistry=registry,auth=auth)

    # test image pull
    #imagereturned = testimagehandler.image_pull(name='openmtczigbee',tag="v2")
    # print imagereturned.name, imagereturned.id, imagereturned.tag

    # test image delete
    # testimagehandler.image_delete(name='openmtczigbee',tag='latest')

    # test image exist
    # imagename = 'dregistry.fokus.fraunhofer.de:5000/openiotfog/zigbeemqtt'
    # test image exists
    # testimagehandler.verify_image_exist('localhost:5000/openmtczigbee')
    # testimagehandler.verify_image_exist_nametag(imagerepo='localhost:5000/openmtczigbee',tag='v2')
    # test = testimagehandler.verify_image_exist(imagename)
