"""Collection of methods and definitions related to the Standard Cortical
Observer Web API resources.
"""

import datetime as dt
from dateutil import tz
import json
import os
import requests
import shutil
import tarfile
import tempfile
import urllib2


# ------------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------------

"""HATEOAS reference keys."""

# SCO-API create experiment
REF_EXPERIMENTS_CREATE = 'experiments.create'
# SCO-API experiments listing
REF_EXPERIMENTS_LISTING = 'experiments.list'
# SCO-API create image group
REF_IMAGE_GROUPS_CREATE = 'images.upload'
# SCO-API image groups listing
REF_IMAGE_GROUPS_LIST = 'images.groups.list'
# SCO-API create subject
REF_SUBJECTS_CREATE = 'subjects.upload'
# SCO-API subjects listing
REF_SUBJECTS_LIST = 'subjects.list'
# Resource download
REF_DOWNLOAD = 'download'
# Resource links listing
REF_LINKS = 'links'
# Resource self reference
REF_SELF = 'self'
# Upsert options (currently for image groups only)
REF_UPDATE_OPTIONS = 'options'
# Upsert properties reference for resources
REF_UPSERT_PROPERTIES = 'properties'

"""Query parameter for object listings."""

# List of attributes to include for each item in listings
QPARA_ATTRIBUTES = 'properties'
# Limit number of items in result
QPARA_LIMIT = 'limit'
# Set offset in collection
QPARA_OFFSET = 'offset'


# ------------------------------------------------------------------------------
#
# SCO Web API Resources
#
# ------------------------------------------------------------------------------

class ResourceHandle(object):
    """Generic handle for a Web API resource in resource listing. Contains the
    four basic resource attributes identifier, name, timestamp, and url. If
    additional properties where requested in the listing call, these will be
    available in a properties dictionary.

    Attributes
    ----------
    identifier : string
        Unique resource identifier
    name : string
        Resource name
    timestamp : datetime.datetime
        Timestamp of resource creation (UTC)
    url : string
        Url to access the resource
    properties : Dictionary
        Dicrionary of additional resource properties and their values. None if
        no additional properties where requested in the client listing method
        call.
    links : Dictionary
        Dictionary of HATEOAS references associated with the resource
    """
    def __init__(self, json_obj, properties=None):
        """Initialize the resource handle using the Json object for the resource
        in the listing result returned by the Web API.

        Parameters
        ----------
        json_obj : Json object
            Json object for resources as returned by Web API
        properties : List(string), optional
            List of additional object properties to be included for items in
            the result
        """
        # Get resource attributes from the Json object
        self.identifier = json_obj['id']
        self.name = json_obj['name']
        # Convert object's creation timestamp from UTC to local time
        self.timestamp = to_local_time(
            dt.datetime.strptime(json_obj['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
        )
        # Get resource HATEOAS references
        self.links = references_to_dict(json_obj[REF_LINKS])
        # Get self reference from list of resource links
        self.url = self.links[REF_SELF]
        # Set resource properties if present in the Json object. For handles
        # in object listings the property element will not be present. In that
        # case the local attribute is set to None.
        if 'properties' in json_obj:
            self.properties = {}
            for kvp in json_obj['properties']:
                self.properties[str(kvp['key'])] = str(kvp['value'])
        else:
            self.properties = None


class ExperimentHandle(ResourceHandle):
    """Resource handle for SCO experiment resource. Experiments are not directly
    associated with any downloadable data files. However, the experiment refers
    to associated subject and image group resources that are cached on local
    disk.

    Attributes
    ----------
    subject : SubjectHandle
        Handle to associated subject resource
    image_group : ImageGroupHandle
        Handle to associated image group resource.
    """
    def __init__(self, json_obj, sco):
        """Initialize image group handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        sco : SCOClient
            Client to access associated subject and image group.
        """
        super(ExperimentHandle, self).__init__(json_obj)
        # Get associated subject and image group using their respective self
        # references in the Json object
        self.subject = sco.subjects_get(
            references_to_dict(
                json_obj['subject']['links']
            )[REF_SELF]
        )
        self.image_group = sco.image_groups_get(
            references_to_dict(
                json_obj['images']['links']
            )[REF_SELF]
        )

    @staticmethod
    def create(url, name, subject_id, image_group_id, properties):
        """Create a new experiment using the given SCO-API create experiment Url.

        Parameters
        ----------
        url : string
            Url to POST experiment create request
        name : string
            User-defined name for experiment
        subject_id : string
            Unique identifier for subject at given SCO-API
        image_group_id : string
            Unique identifier for image group at given SCO-API
        properties : Dictionary
            Set of additional properties for created experiment. Argument may be
            None. Given name will override name property in this set (if present).

        Returns
        -------
        string
            Url of created experiment resource
        """
        # Create list of key,value-pairs representing experiment properties for
        # request. The given name overrides the name in properties (if present).
        obj_props = [{'key':'name','value':name}]
        if not properties is None:
            # Catch TypeErrors if properties is not a list.
            try:
                for key in properties:
                    if key != 'name':
                        obj_props.append({'key':key,'value':properties[key]})
            except TypeError as ex:
                raise ValueError('invalid property set')
        # Create request body and send POST request to given Url
        body = {
            'subject' : subject_id,
            'images' : image_group_id,
            'properties' : obj_props
        }
        try:
            req = urllib2.Request(url)
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps(body))
        except urllib2.URLError as ex:
            raise ValueError(str(ex))
        # Get experiment self reference from successful response
        return references_to_dict(json.load(response)['links'])[REF_SELF]

class ImageGroupHandle(ResourceHandle):
    """Resource handle for SCO image group resource on local disk. The contents
    of the image group tar-file are extracted into the objects data directory.

    Attributes
    ----------
    data_dir : string
        Absolute path to directory containing a local copy of the resource
        data files
    images : List(string)
        List if absolute file path to images in the group.
    options : Dictionary
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
            self.options[str(kvp['name'])] = kvp['value']
        # Set the data directory. If directory does not exist, create it,
        # download the resource data archive, and unpack into data directory
        self.data_dir = os.path.abspath(os.path.join(base_dir, 'data'))
        if not os.path.isdir(self.data_dir):
            os.mkdir(self.data_dir)
            # Download tar-archive
            tmp_file = download_file(self.links[REF_DOWNLOAD])
            # Unpack downloaded file into data directory
            try:
                tf = tarfile.open(name=tmp_file, mode='r')
                tf.extractall(path=self.data_dir)
            except (tarfile.ReadError, IOError) as err:
                # Clean up in case there is an error during extraction
                shutil.rmtree(self.data_dir)
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
                    img_file = os.path.join(self.data_dir, local_path)
                    f.write(local_path + '\n')
                    self.images.append(img_file)
        else:
            # Read content of images file into images list
            with open(images_file, 'r') as f:
                for line in f:
                    self.images.append(os.path.join(self.data_dir, line.strip()))

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

class SubjectHandle(ResourceHandle):
    """Resource handle for SCO subject resource on local disk. Downloads the
    subject tar-file (on first access) and copies the contained FreeSurfer
    directory into the resource's data directory.


    Attributes
    ----------
    data_dir : string
        Absolute path to directory containing the subjects FreeSurfer data files
    """
    def __init__(self, json_obj, base_dir):
        """Initialize subject handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        base_dir : string
            Path to cache base directory for object
        """
        super(SubjectHandle, self).__init__(json_obj)
        # Set the data directory. If directory does not exist, create it,
        # download the resource data archive, and unpack into data directory
        self.data_dir = os.path.abspath(os.path.join(base_dir, 'data'))
        if not os.path.isdir(self.data_dir):
            # Create data dir and temporary directory to extract downloaded file
            os.mkdir(self.data_dir)
            temp_dir = tempfile.mkdtemp()
            # Download tar-archive and unpack into temp_dir
            tmp_file = download_file(self.links[REF_DOWNLOAD])
            try:
                tf = tarfile.open(name=tmp_file, mode='r')
                tf.extractall(path=temp_dir)
            except (tarfile.ReadError, IOError) as err:
                # Clean up in case there is an error during extraction
                shutil.rmtree(temp_dir)
                shutil.rmtree(self.data_dir)
                raise ValueError(str(err))
            # Remove downloaded file
            os.remove(tmp_file)
            # Make sure the extracted files contain a valid freesurfer directory
            freesurf_dir = get_freesurfer_dir(temp_dir)
            if not freesurf_dir:
                # Clean up before raising an exception
                shutil.rmtree(temp_dir)
                shutil.rmtree(self.data_dir)
                raise ValueError('not a valid subject directory')
            # Move all sub-folders from the Freesurfer directory to the new anatomy
            # data directory
            for f in os.listdir(freesurf_dir):
                sub_folder = os.path.join(freesurf_dir, f)
                if os.path.isdir(sub_folder):
                    shutil.move(sub_folder, self.data_dir)
            # Remove temporary directory
            shutil.rmtree(temp_dir)


    @staticmethod
    def create(url, filename, properties):
        """Create new subject at given SCO-API by uploading local file.
        Expects an tar-archive containing FreeSurfer archive file. Allows to
        update properties of created resource.

        Parameters
        ----------
        url : string
            Url to POST image group create request
        filename : string
            Path to tar-archive on local disk
        properties : Dictionary
            Set of additional properties for subject (may be None)

        Returns
        -------
        string
            Url of created subject resource
        """
        # Ensure that the file has valid suffix
        if not has_tar_suffix(filename):
            raise ValueError('invalid file suffix: ' + filename)
        # Upload file to create subject. If response is not 201 the uploaded
        # file is not a valid FreeSurfer archive
        files = {'file': open(filename, 'rb')}
        response = requests.post(url, files=files)
        if response.status_code != 201:
            raise ValueError('invalid file: ' + filename)
        # Get image group HATEOAS references from successful response
        links = references_to_dict(response.json()['links'])
        resource_url = links[REF_SELF]
        # Update subject properties if given
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


# ------------------------------------------------------------------------------
#
# Helper Classes
#
# ------------------------------------------------------------------------------

class JsonResource:
    """Simple class to wrap a GET request that reads a Json object. Includes the
    request response and the retrieved Json object.

    Attributes
    ----------
    json : Json object
        Json response object
    response : Response
        Http request response object
    """
    def __init__(self, url):
        """Get Json object from given Url.

        Raises ValueError if given Url cannot be read or result is not a valid
        Json object.

        Parameters
        ----------
        url : string
            Url of resource to be read
        """
        try:
            self.response = urllib2.urlopen(url)
        except urllib2.URLError as ex:
            raise ValueError(str(ex))
        self.json = json.loads(self.response.read())


# ------------------------------------------------------------------------------
#
# Helper Methods
#
# ------------------------------------------------------------------------------

def download_file(url):
    """Download attached file as temporary file.

    Parameters
    ----------
    url : string
        SCO-API downlioad Url

    Returns
    -------
    string
        Path to downloaded file
    """
    r = urllib2.urlopen(url)
    # Expects a tar-archive or a compressed tar-archive
    if r.info()['content-type'] == 'application/x-tar':
        fd, f_path = tempfile.mkstemp(suffix='.tar')
    elif r.info()['content-type'] == 'application/gzip':
        fd, f_path = tempfile.mkstemp(suffix='.tar.gz')
    else:
        raise ValueError('unexpected file type: ' + r.info()['content-type'])
    # Save attached file in temp file and return path to temp file
    os.write(fd, r.read())
    os.close(fd)
    return f_path


def get_freesurfer_dir(directory):
    """Test if a directory is a Freesurfer anatomy directory. Currently, the
    test is whether (1) there are sub-folders with name 'surf' and 'mri' and
    (2) if the Freesurfer library method freesurfer_subject returns a non-None
    result for the directory. Processes all sub-folders recursively until a
    freesurfer directory is found. If no matching folder is found the result is
    None.

    Parameters
    ----------
    directory : string
        Directory on local disk containing unpacked files

    Returns
    -------
    string
        Sub-directory containing a Freesurfer files or None if no such
        directory is found.
    """
    dir_files = [f for f in os.listdir(directory)]
    # Look for sub-folders 'surf' and 'mri'
    if 'surf' in dir_files and 'mri' in dir_files:
        return directory
    # Directory is not a valid freesurfer directory. Continue to search
    # recursively until a matching directory is found.
    for f in os.listdir(directory):
        sub_dir = os.path.join(directory, f)
        if os.path.isdir(sub_dir):
            if get_freesurfer_dir(sub_dir):
                return sub_dir
    # The given directory does not contain a freesurfer anatomy directory
    return None


def get_resource_listing(url, offset, limit, properties):
    """Gneric method to retrieve a trsource listing from a SCO-API. Takes the
    resource-specific API listing Url as argument.

    Parameters
    ----------
    url : string
        Resource listing Url for a SCO-API
    offset : int, optional
        Starting offset for returned list items
    limit : int, optional
        Limit the number of items in the result
    properties : List(string)
        List of additional object properties to be included for items in
        the result

    Returns
    -------
    List(ResourceHandle)
        List of resource handle (one per subject in the object listing)
    """
    # Create listing query based on given arguments
    query = [
        QPARA_OFFSET + '=' + str(offset),
        QPARA_LIMIT + '=' + str(limit)
    ]
    # Add properties argument if property list is not None and not empty
    if not properties is None:
        if len(properties) > 0:
            query.append(QPARA_ATTRIBUTES + '=' + ','.join(properties))
    # Add query to Url.
    url = url + '?' + '&'.join(query)
    # Get subject listing Url for given SCO-API and decorate it with
    # given listing arguments. Then retrieve listing from SCO-API.
    json_obj = JsonResource(url).json
    # Convert result into a list of resource handles and return the result
    resources = []
    for element in json_obj['items']:
        resource = ResourceHandle(element)
        # Add additional properties to resource if list is given
        if not properties is None:
            resource.properties = {}
            for prop in properties:
                if prop in element:
                    resource.properties[prop] = element[prop]
        resources.append(resource)
    return resources


def has_tar_suffix(filename):
    """Check if given filename suffix is a valid tar-file suffix.

    Parameters
    ----------
    filename : string
        Name of file on disk

    Returns
    -------
    Boolean
        True, if filename ends with '.tar', '.tar.gz', or '.tgz'
    """
    for suffix in ['.tar', '.tar.gz', '.tgz']:
        if filename.endswith(suffix):
            return True
    return False


def references_to_dict(elements):
    """Convery a list of HATEOAS reference objects into a dictionary.
    Parameters
    ----------
    elements : List
        List of key value pairs, i.e., [{rel:..., href:...}].
    Returns
    -------
    Dictionary
        Dictionary of rel:href pairs.
    """
    dictionary = {}
    for kvp in elements:
        dictionary[str(kvp['rel'])] = str(kvp['href'])
    return dictionary


def to_local_time(utc):
    """Convert a datatime object from UTC time to local time.

    Adopted from:
    http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime

    Parameters
    ----------
    utc : datetime
        Datetime object expected to be in UTC time zone

    Returns
    -------
    datetime
        Datetime object in local time zone
    """
    # Get UTC and local time zone
    from_zone = tz.gettz('UTC')
    to_zone = tz.tzlocal()

    # Tell the utc object that it is in UTC time zone
    utc = utc.replace(tzinfo=from_zone)

    # Convert time zone
    return utc.astimezone(to_zone)
