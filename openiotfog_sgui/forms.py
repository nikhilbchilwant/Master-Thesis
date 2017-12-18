from flask_wtf import Form
from wtforms import StringField,TextField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField

from wtforms import validators, ValidationError


class NodeaddForm(Form):
    ip = StringField("IP", [validators.DataRequired("Please IP of Fog Node")])

    layer = StringField("Layer", [validators.DataRequired("Please enter layer of Node")])

    submit = SubmitField("Send")


class ImageaddForm(Form):
    image_name = StringField("ImageName", [validators.DataRequired("Please provide Image name")])

    tag = StringField("Tag", [validators.DataRequired("Please enter the tag")])

    Imagesubmit = SubmitField("PullImage")



class DeviceForm(Form):
    device_adapter_name = StringField("DeviceName", [validators.DataRequired("Please provide Image name")])

    product_id = StringField("ProductID", [validators.DataRequired("Please enter the tag")])

    vendor_id = StringField("VendorID", [validators.DataRequired("Please enter the tag")])

    Devicesubmit = SubmitField("AddDeviceTemplate")