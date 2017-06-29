"""Handle for local copies of image groups and image resources."""

import json
import os
import requests
import shutil
import tarfile
import urllib2

from scoserv import Attribute, JsonResource, ResourceHandle
from scoserv import download_file, has_tar_suffix, references_to_dict
from scoserv import QPARA_LIMIT, REF_DOWNLOAD, REF_SELF, REF_UPDATE_OPTIONS
from scoserv import REF_UPSERT_PROPERTIES


class GroupImage(object):
    """Required for compatibility with the data store image group object.
    Represents an image in a image group.

    Attributes
    ----------
    identifier : string
        Unique identifier of the image
    folder : string
        (Sub-)folder in the grouop (default: /)
    name : string
        Image name (unique within the folder)
    data_file : string
        Path to image file on local disk
    """
    def __init__(self, identifier, folder, name, filename):
        """Initialize attributes of the group image.

        Parameters
        ----------
        identifier : string
            Unique identifier of the image
        folder : string
            (Sub-)folder in the group (default: /)
        name : string
            Image name (unique within the folder)
        filename : string
            Absolute path to file on local disk
        """
        self.identifier = identifier
        self.folder = folder
        self.name = name
        self.data_file = filename


class ImageGroupHandle(ResourceHandle):
    """Resource handle for SCO image group resource on local disk. The contents
    of the image group tar-file are extracted into the objects data directory.

    Attributes
    ----------
    data_directory : string
        Absolute path to directory containing a local copy of the resource
        data files
    images : List(string)
        List if absolute file path to images in the group.
    options : Dictionary(Attribute)
        Dictionary of options for image group
    """
    def __init__(self, json_obj, base_dir):
        """Initialize image group handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        base_dir : string
            Path to cache base directory for object
        """
        super(ImageGroupHandle, self).__init__(json_obj)
        # Set image group options
        self.options = {}
        for kvp in json_obj['options']:
            a_name = str(kvp['name'])
            self.options[a_name] = Attribute(a_name, kvp['value'])
        # Set the data directory. If directory does not exist, create it,
        # download the resource data archive, and unpack into data directory
        self.data_directory = os.path.abspath(os.path.join(base_dir, 'data'))
        if not os.path.isdir(self.data_directory):
            os.mkdir(self.data_directory)
            # Download tar-archive
            tmp_file, f_suffix = download_file(self.links[REF_DOWNLOAD])
            # Unpack downloaded file into data directory
            try:
                tf = tarfile.open(name=tmp_file, mode='r')
                tf.extractall(path=self.data_directory)
            except (tarfile.ReadError, IOError) as err:
                # Clean up in case there is an error during extraction
                shutil.rmtree(self.data_directory)
                raise ValueError(str(err))
            # Remove downloaded file
            os.remove(tmp_file)
        # Set list of group images. The list (and order) of images is stored in
        # the .images file in the resource's data directory. If the file does
        # not exists read list from SCO-API.
        self.images = []
        images_file = os.path.join(base_dir, '.images')
        if not os.path.isfile(images_file):
            json_list = JsonResource(
                references_to_dict(
                    json_obj['images']['links']
                )[REF_SELF] + '?' + QPARA_LIMIT + '=-1'
            ).json
            with open(images_file, 'w') as f:
                for element in json_list['items']:
                    # Folder names start with '/'. Remove to get abs local path
                    local_path = element['folder'][1:] + element['name']
                    img_file = os.path.join(self.data_directory, local_path)
                    record = '\t'.join([
                        element['id'],
                        element['folder'],
                        element['name'],
                        local_path
                    ])
                    f.write(record + '\n')
                    self.images.append(
                        GroupImage(
                            element['id'],
                            element['folder'],
                            element['name'],
                            img_file
                        )
                    )
        else:
            # Read content of images file into images list
            with open(images_file, 'r') as f:
                for line in f:
                    tokens = line.strip().split('\t')
                    self.images.append(
                        GroupImage(
                            tokens[0],
                            tokens[1],
                            tokens[2],
                            os.path.join(self.data_directory, tokens[3])
                        )
                    )

    @staticmethod
    def create(url, filename, options, properties):
        """Create new image group at given SCO-API by uploading local file.
        Expects an tar-archive containing images in the image group. Allows to
        update properties of created resource.

        Parameters
        ----------
        url : string
            Url to POST image group create request
        filename : string
            Path to tar-archive on local disk
        options : Dictionary, optional
            Values for image group options. Argument may be None.
        properties : Dictionary
            Set of additional properties for image group (may be None)

        Returns
        -------
        string
            Url of created image group resource
        """
        # Ensure that the file has valid suffix
        if not has_tar_suffix(filename):
            raise ValueError('invalid file suffix: ' + filename)
        # Upload file to create image group. If response is not 201 the uploaded
        # file is not a valid tar file
        files = {'file': open(filename, 'rb')}
        response = requests.post(url, files=files)
        if response.status_code != 201:
            raise ValueError('invalid file: ' + filename)
        # Get image group HATEOAS references from successful response
        links = references_to_dict(response.json()['links'])
        resource_url = links[REF_SELF]
        # Update image group options if given
        if not options is None:
            obj_ops = []
            # Catch TypeErrors if properties is not a list.
            try:
                for opt in options:
                    obj_ops.append({'name' : opt, 'value' : options[opt]})
            except TypeError as ex:
                raise ValueError('invalid option set')
            try:
                req = urllib2.Request(links[REF_UPDATE_OPTIONS])
                req.add_header('Content-Type', 'application/json')
                response = urllib2.urlopen(
                    req,
                    json.dumps({'options' : obj_ops})
                )
            except urllib2.URLError as ex:
                raise ValueError(str(ex))
        # Update image group properties if given
        if not properties is None:
            obj_props = []
            # Catch TypeErrors if properties is not a list.
            try:
                for key in properties:
                    obj_props.append({'key':key, 'value':properties[key]})
            except TypeError as ex:
                raise ValueError('invalid property set')
            try:
                req = urllib2.Request(links[REF_UPSERT_PROPERTIES])
                req.add_header('Content-Type', 'application/json')
                response = urllib2.urlopen(
                    req,
                    json.dumps({'properties' : obj_props})
                )
            except urllib2.URLError as ex:
                raise ValueError(str(ex))
        return resource_url
