class Container_Image():
    def __init__(self, image_name="",image_repo="", image_tag="", *args, **kw):
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
    def deletable(self):
        # returns true if no Container is using the docker image
        return self._deletable # and not ContainerTmpl.is_image_used(self.ID) # TODO add correct checker. it is used in any device template? if no deletable

    def set_image_name(self,newimagename=""):
        self._name = newimagename

    def set_image_tag(self,newtag=""):
        self._tag = newtag


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
                "deletable": {"type": "boolean"}
            }
        }

    def destroy(self):
        #return self._docker_destroy_image()
        del self

    def __del__(self):
        self.destroy()