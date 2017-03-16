"""Use SCO Client to run a local installation of the SCO predictive model with
all combinations of subjects and image groups from a SCO-API.
"""

import os

from neuropythy.freesurfer import add_subject_path
from sco import calc_sco
import scocli

# Connect to default SCO-API. Uses a temporary directory to store files in
# local cache
sco = scocli.SCOClient()

# Run sco_calc for each combination of subjects and image groups.
for s in sco.subjects_list(properties=['filename']):
    subject = sco.subjects_get(s.url)
    for ig in sco.image_groups_list():
        image_group = sco.image_groups_get(ig.url)
        # Set run options
        opts = {'gabor_orientations': 8, 'max_eccentricity' : 12}
        # Add image group options
        for attr in image_group.options:
            opts[attr] = image_group.options[attr]
        # Run predictive model for combination of subject and image group
        print 'RUN MODEL WITH:'
        print '\tSUBJECT: ' + subject.name
        print '\tIMAGES : ' + image_group.name
        print '\tOPTIONS: ' + str(opts)
        try:
            results = calc_sco(
                opts,
                subject=subject.data_directory,
                stimulus_image_filenames=image_group.images
            )
        except Exception as ex:
            print '\n!EXCEPTION: ' + str(ex) + '\n'
