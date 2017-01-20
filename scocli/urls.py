"""Collection of methods and definitions related to the Standard Cortical
Observer Web API resources.
"""

# ------------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------------

"""HATEOAS reference identifier for Web API resources."""

# URL for file downloads
URL_DOWNLOAD = 'download'
# URL to list image groups
URL_IMAGEGROUPS = 'imageGroups'
# URL to list subjects
URL_SUBJECTS = 'subjects'

"""Query parameter for object listings."""

# List of attributes to include for each item in listings
QPARA_ATTRIBUTES = 'attr'
# Limit number of items in result
QPARA_LIMIT = 'limit'
# Set offset in collection
QPARA_OFFSET = 'offset'


# ------------------------------------------------------------------------------
#
# Helper Methods
#
# ------------------------------------------------------------------------------

def decorate_url(url, offset=-1, limit=-1, properties=None):
    """Decorate a given object listing Url with query arguments for offset,
    limit, and attributes.

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
    string
        Url for object listing
    """
    # List of query arguments
    query = []
    # Add offset argument if value is non-negative
    if offset >= 0:
        query.append(QPARA_OFFSET + '=' + str(offset))
    # Add limit argument is value is non-negative
    if limit >= 0:
        query.append(QPARA_LIMIT + '=' + str(limit))
    # Add attributes argument if property list is not None and not empty
    if not properties is None:
        if len(properties) > 0:
            query.append(QPARA_ATTRIBUTES + '=' + ','.join(properties))
    # Add query to Url if argument list is not empty. Otherwise return
    # given Url.
    if len(query) > 0:
        return url + '?' + '&'.join(query)
    else:
        return url
