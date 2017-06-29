"""Handle for local copies of model resources."""

from scodata.attribute import AttributeDefinition
from scoengine.model import ModelOutputs
from scoserv import ResourceHandle


class ModelHandle(ResourceHandle):
    """Resource handle for SCO model resource. Models are not associated with
    any downloadable data files.

    Attributes
    ----------
    outputs : scoengine.model.ModelOutputs
        Description of the output files that the model creates
    parameters : list(scodata.attribute.AttributeDefinition)
        List of attribute definitions for model run parameters
    """
    def __init__(self, json_obj):
        """Initialize image group handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        """
        super(ModelHandle, self).__init__(json_obj)
        # Create model output descriptions
        self.outputs = ModelOutputs.from_json(json_obj['outputs'])
        # Create list of model parameter definitions
        self.parameters = [
            AttributeDefinition.from_json(el) for el in json_obj['parameters']
        ]
