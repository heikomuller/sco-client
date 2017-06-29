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

"""Resource properties."""
# Name of the functional data file in a fMRI resource archive
PROPERTY_FUNCDATAFILE = 'funcdatafile'

"""HATEOAS reference keys."""
# SCO-API create experiment
REF_EXPERIMENTS_CREATE = 'experiments.create'
# SCO-API Upload fMRI for experiment
REF_EXPERIMENTS_FMRI_CREATE = 'fmri.upload'
# SCO-API experiments listing
REF_EXPERIMENTS_LISTING = 'experiments.list'
# SCO-API list experiments runs
REF_EXPERIMENTS_RUNS_CREATE = 'predictions.run'
# SCO-API list experiments runs
REF_EXPERIMENTS_RUNS_LISTING = 'predictions.list'
# SCO-API create image group
REF_IMAGE_GROUPS_CREATE = 'images.upload'
# SCO-API image groups listing
REF_IMAGE_GROUPS_LIST = 'images.groups.list'
# Base Url for model run attachments
REF_MODEL_RUN_ATTACHMENTS = 'attachments.create'
# SCO-API list models
REF_MODELS_LIST = 'models.list'
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
# Update model run state
REF_UPDATE_STATE_ACTIVE = 'state.active'
REF_UPDATE_STATE_ERROR = 'state.error'
REF_UPDATE_STATE_SUCCESS = 'state.success'
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
# Classes
#
# ------------------------------------------------------------------------------

class Attribute(object):
    """Attributes are name value pairs. Attributes are used to represent image
    group options and model run arguments.

    Attributes
    ----------
    name : string
        Property name
    value : any
        Associated value for the property. Can be of any type
    """
    def __init__(self, name, value):
        """Initialize the type property instance by passing arguments for name
        and value.

        Parameters
        ----------
        name : string
            Property name

        value : any
            Associated value for the property. Can be of any type
        """
        self.name = name
        self.value = value


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
    def __init__(self, json_obj):
        """Initialize the resource handle using the Json object for the resource
        in the listing result returned by the Web API.

        Parameters
        ----------
        json_obj : Json object
            Json object for resources as returned by Web API
        """
        # Get resource attributes from the Json object
        self.identifier = json_obj['id']
        self.name = json_obj['name']
        # Convert object's creation timestamp from UTC to local time
        self.timestamp = to_local_time(json_obj['timestamp'])
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

def download_file(url, suffix=''):
    """Download attached file as temporary file.

    Parameters
    ----------
    url : string
        SCO-API download Url
    suffix : string, optional
        If suffix is specified, the name of the downloaded file will end with
        that suffix, otherwise there will be no suffix.

    Returns
    -------
    string, string
        Path to downloaded file and file suffix
    """
    r = urllib2.urlopen(url)
    # Save attached file in temp file and return path to temp file
    fd, f_path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, r.read())
    os.close(fd)
    return f_path, suffix


def get_resource_listing(url, offset, limit, properties):
    """Gneric method to retrieve a resource listing from a SCO-API. Takes the
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


def to_local_time(timestamp):
    """Convert a datatime object from UTC time to local time.

    Adopted from:
    http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime

    Parameters
    ----------
    timestamp : string
        Default string representation of timestamps expected to be in
        UTC time zone

    Returns
    -------
    datetime
        Datetime object in local time zone
    """
    utc = dt.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')
    # Get UTC and local time zone
    from_zone = tz.gettz('UTC')
    to_zone = tz.tzlocal()

    # Tell the utc object that it is in UTC time zone
    utc = utc.replace(tzinfo=from_zone)

    # Convert time zone
    return utc.astimezone(to_zone)
