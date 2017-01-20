"""Standard Cortical Observer - Web API client

Client to interact with the Standard Cortical Observer Web API.
"""

from urllib2 import urlopen
import json

import db
import urls
import utils


# ------------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------------

# Url of default SCO Web API hosted at NYU
DEFAULT_SCO_API = 'http://cds-swg1.cims.nyu.edu/sco-server/api/v1'


# ------------------------------------------------------------------------------
#
# Standard Cortical Observer - Client API
#
# ------------------------------------------------------------------------------

class SCOClient(object):
    """Standard Cortical Observer Web API (SCO-API) Client interacts with an
    existing SCO-API server. The client provides access to SCO-API resources
    such as subjects (Anatomy MRI data) and image groups.

    The client may access files that are associated with SCO-API resources
    directly via URL's or cache them in a local directory to improve performance
    when using files multiple times.

    """
    def __init__(self, api_url=DEFAULT_SCO_API, data_dir=None, use_cache=True):
        """Initialize the client. Connects to the SCO-API identified by the
        given URL to retrieve relevant references. If a data directory is given,
        this directory will be used to cache downloaded files. The cache will
        not be cleared by the client to ensure persistency throughout multiple
        invocation. Files on the SCO-API are not expected to change at this
        point, thus the cached files cannot become invalid. Note: This may
        change when image groups can be updated!

        Parameters
        ----------
        server_url : string, optional
            Base URL of a SCO Web API. Use to create new resources when no
            API is specified.
        data_dir : string, optional
            Optional directory for caching files. Directory will be created if
            it does not exists. Defaults to ~/.sco if None and caching is used.
        use_cache : Boolean, optional
            Flag indicating whether a local file cache will be used for Web
            resources. If False, data_dir will be ignored.
        """
        # Set the default API Url. This is the API that will be used to create
        # new resources if no API is specified explicitly.
        self.api_url = api_url
        # If the data directory is given use a local disk cache file manager.
        # Otherwise use the default file manager that downloads a file each
        # time it is accessed by the client
        if use_cache:
            self.file_manager = db.DownloadCacheManager(data_dir)
        else:
            self.file_manager = db.DefaultFileManager()

        # Get user home directoy if no data dir is given but caching is active
    def image_groups_get(self, identifier):
        """Get image group resource with given identifier from Web API.

        Parameters
        ----------
        identifier : string
            Unique image group identifier

        Returns
        -------
        ResourceHandle
            Handle for image group resource with given identifier
        """
        # Construct image group Url by concatenating listing Url and identifier.
        # This assumes that server Url's are always constructed in the same
        # way as initially defined. Need to adjust this code if the Url pattern
        # for the server changes.
        url = self.links[urls.URL_IMAGEGROUPS] + '/' + identifier
        return self.to_resource(JsonResource(url).json)

    def image_groups_list(self, offset=-1, limit=-1, properties=None):
        """Get list of image group resources from Web API.

        Parameters
        ----------
        offset : int, optional
            Starting offset for returned list items
        limit : int, optional
            Limit the number of items in the result
        properties : List(string)
            List of additional object properties to be included for items in
            the result

        Returns
        -------
        List(db.ResourceHandle)
            List of resource handle (one per subject in the object listing)
        """
        # Construct Url for image groups listing
        url = self.links[urls.URL_IMAGEGROUPS]
        url = urls.decorate_url(url, offset=offset, limit=limit, properties=properties)
        # Retrieve object listing from Web API
        result = JsonResource(url)
        return self.to_resource_list(result.json)

    def subjects_get(self, identifier):
        """Get subjects resource with given identifier from Web API.

        Parameters
        ----------
        identifier : string
            Unique subject identifier

        Returns
        -------
        ResourceHandle
            Handle for subject resource with given identifier
        """
        # Construct subject Url by concatenating listing Url and identifier.
        # This assumes that server Url's are always constructed in the same
        # way as initially defined. Need to adjust this code if the Url pattern
        # for the server changes.
        url = self.links[urls.URL_SUBJECTS] + '/' + identifier
        return self.to_resource(JsonResource(url).json)

    def subjects_list(self, offset=-1, limit=-1, properties=None):
        """Get list of subject resources from Web API.

        Parameters
        ----------
        offset : int, optional
            Starting offset for returned list items
        limit : int, optional
            Limit the number of items in the result
        properties : List(string)
            List of additional object properties to be included for items in
            the result

        Returns
        -------
        List(db.ResourceHandle)
            List of resource handle (one per subject in the object listing)
        """
        # Construct Url for subject listing
        url = self.links[urls.URL_SUBJECTS]
        url = urls.decorate_url(url, offset=offset, limit=limit, properties=properties)
        # Retrieve object listing from Web API
        result = JsonResource(url)
        return self.to_resource_list(result.json)

    def to_resource(self, json_obj):
        """Covert the result of a Web API list objects request into a list
        of resource handles.

        Parameters
        ----------
        json_obj : Json object
            Json representation of Web API list object

        Returns
        -------
        db.ResourceHandle
            Resource handle for given Web API object
        """
        return db.ResourceHandle(json_obj, self.file_manager)

    def to_resource_list(self, json_obj):
        """Covert the result of a Web API list objects request into a list
        of resource handles.

        Parameters
        ----------
        json_obj : Json object
            Response object from Web API list objects request

        Returns
        -------
        List(db.ResourceHandle)
            List of resource handle (one per resource in the object listing)
        """
        resources = []
        # Test if the item list is empty
        if json_obj['count'] > 0:
            # Convert each element in the item list into a resource handle
            for element in json_obj['items']:
                resources.append(self.to_resource(element))
        return resources



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

        Parameters
        ----------
        url : string
            Url of resource to be read
        """
        self.response = urlopen(url)
        self.json = json.loads(self.response.read())
