"""Handle for local copies of experiment resources."""

import json
import os
import urllib2

from modelrun import ModelRunDescriptor
from scoserv import ResourceHandle, JsonResource
from scoserv import references_to_dict
from scoserv import REF_EXPERIMENTS_RUNS_CREATE, REF_EXPERIMENTS_RUNS_LISTING
from scoserv import REF_SELF, QPARA_ATTRIBUTES, QPARA_LIMIT, QPARA_OFFSET


class ExperimentHandle(ResourceHandle):
    """Resource handle for SCO experiment resource. Experiments are not directly
    associated with any downloadable data files. However, the experiment refers
    to associated subject and image group resources that are cached on local
    disk.

    Attributes
    ----------
    fmri_url : string
        Url for associated fMRI resource. None if no fMRI is associated with
        this experiment
    image_group_url : string
        Url for associated image group resource.
    runs_url : string
        Url for associated model runs
    subject_url : string
        Url for associated subject resource
    """
    def __init__(self, json_obj, sco):
        """Initialize image group handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        sco : SCOClient
            Client to access associated resources.
        """
        super(ExperimentHandle, self).__init__(json_obj)
        # Maintain reference to SCO client to access subject and image group
        # resources when requested
        self.sco = sco
        # Maintain Urls for associated subject, image group, fMRI, and model
        # run resources
        self.subject_url = references_to_dict(
            json_obj['subject']['links']
        )[REF_SELF]
        self.image_group_url = references_to_dict(
            json_obj['images']['links']
        )[REF_SELF]
        if 'fmri' in json_obj:
            self.fmri_url = references_to_dict(
                json_obj['fmri']['links']
            )[REF_SELF]
        else:
            self.fmri_url = None
        self.runs_url = self.links[REF_EXPERIMENTS_RUNS_LISTING]

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
                        obj_props.append({'key':key, 'value':properties[key]})
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

    @property
    def fmri_data(self):
        """Functional MRI data resource that is associated with this experiment.
        The result is None if no fMRI data has been associated with the
        experiment.

        Returns
        -------
        FunctionalDataHandle
            Handle for associated funcrional MRI data resource
        """
        if not self.fmri_url is None:
            return self.sco.experiments_fmri_get(self.fmri_url)
        else:
            return None

    @property
    def image_group(self):
        """Image group resource that is associated with this experiment.

        Returns
        -------
        ImageGroupHandle
            Handle for associated image group resource
        """
        return self.sco.image_groups_get(self.image_group_url)

    def run(self, model_id, name, arguments={}, properties=None):
        """Create a new model run with given name, arguments, and properties.
        Parameters
        ----------
        model_id : string
            Unique model identifier
        name : string
            User-defined name for experiment
        arguments : Dictionary
            Dictionary of arguments for model run
        properties : Dictionary, optional
            Set of additional properties for created mode run.

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of created model run resource
        """
        return self.sco.experiments_predictions_create(
            model_id,
            name,
            self.links[REF_EXPERIMENTS_RUNS_CREATE],
            arguments=arguments,
            properties=properties
        )

    def runs(self, offset=0, limit=-1, properties=None):
        """Get a list of run descriptors associated with this expriment.

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
        List(scoserv.ModelRunDescriptor)
            List of model run descriptors
        """
        return get_run_listing(
            self.runs_url,
            offset=offset,
            limit=limit,
            properties=properties
        )

    @property
    def subject(self):
        """Subject resource that is associated with this experiment.

        Returns
        -------
        SubjectHandle
            Handle for associated subject resource
        """
        return self.sco.subjects_get(self.subject_url)


# ------------------------------------------------------------------------------
#
# Helper Methods
#
# ------------------------------------------------------------------------------

def get_run_listing(listing_url, offset, limit, properties):
    """Get list of experiment resources from a SCO-API.

    Parameters
    ----------
    listing_url : string
        url for experiments run listing.
    offset : int
        Starting offset for returned list items
    limit : int
        Limit the number of items in the result
    properties : List(string)
        List of additional object properties to be included for items in
        the result

    Returns
    -------
    List(scoserv.ModelRunDescriptor)
        List of model run descriptors
    """
    # Create listing query based on given arguments
    query = [
        QPARA_OFFSET + '=' + str(offset),
        QPARA_LIMIT + '=' + str(limit)
    ]
    # Ensure that the run state is included in the listing as attribute
    props = ['state']
    # Add properties argument if property list is not None and not empty
    if not properties is None:
        for prop in properties:
            if not prop in props:
                props.append(prop)
    query.append(QPARA_ATTRIBUTES + '=' + ','.join(props))
    # Add query to Url.
    url = listing_url + '?' + '&'.join(query)
    # Get subject listing Url for given SCO-API and decorate it with
    # given listing arguments. Then retrieve listing from SCO-API.
    json_obj = JsonResource(url).json
    # Convert result into a list of resource handles and return the result
    resources = []
    for element in json_obj['items']:
        resource = ModelRunDescriptor(element)
        # Add additional properties to resource if list is given
        if not properties is None:
            resource.properties = {}
            for prop in properties:
                if prop in element:
                    resource.properties[prop] = element[prop]
        resources.append(resource)
    return resources
