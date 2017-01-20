"""Collection of helper methods."""

from datetime import datetime
from dateutil import tz
import os


def create_dir(directory):
    """Create given directory, if doesn't exist.

    Parameters
    ----------
    directory : string
        Directory path (can be relative or absolute)

    Returns
    -------
    string
        Absolute directory path
    """
    if not os.access(directory, os.F_OK):
        os.makedirs(directory)
    return os.path.abspath(directory)


def from_list(elements, label_key='key', label_value='value'):
    """Convert a list of key-value pairs into a dictionary. The value that is
    associated with the key of each key-value pair will be the dictionary key.

    Parameters
    ----------
    elements : List
        List of key value pairs, i.e., [{label_key:..., label_value:...}].
    label_key : string
        Label for the key entry of key-value pairs in elements.
    label_value : string
        Label for the value entry of key-value pairs in elements.

    Returns
    -------
    Dictionary
        Dictionary of values.
    """
    dictionary = {}
    for kvp in elements:
        dictionary[str(kvp[label_key])] = str(kvp[label_value])
    return dictionary


def to_list(dictionary, label_key='key', label_value='value'):
    """Convert a dictionary into a list of dictionary, e.g., HATEOAS references,
    where each element is a dictionary with two entries: key and value.

    Parameters
    ----------
    dictionary : Dictionary
        Dictionary of values that is to be converted into a list of key-value
        pairs.
    label_key : string
        Label for the key entry of each generated key-value pair.
    label_value : string
        Label for the value entry of each generated key-value pair.

    Returns
    -------
    List
        List of key value pairs, i.e., [{label_key:..., label_value:...}]
    """
    attributes = []
    for key in dictionary:
        attributes.append({label_key : key, label_value : dictionary[key]})
    return attributes


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
