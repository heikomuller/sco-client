"""Use SCO Client to run an existing experiment using a local installation of
the SCO predictive model.
"""

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

from neuropythy.freesurfer import add_subject_path
from sco import calc_sco
import scocli

add_subject_path('/home/heiko/projects/sco/sco-server/resources/env/subjects')

# Connect to default SCO-API. Uses a temporary directory to store files in
# local cache
sco = scocli.SCOClient()

# Get list of experiments. Exit if list is empty.
experiments = sco.experiments_list()
if len(experiments) == 0:
    print 'No experiment found'
    sys.exit(0)
# Take first entry an run SCO model locally for the associated subject and
# image group. Make sure to get the full experiment handle. The resource
# handle that is contained in the experiment listing does not have references
# to associated objects.
expr = sco.experiments_get(experiments[0].url)
subject = expr.subject
image_group = expr.image_group
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
        subject=subject.data_dir,
        stimulus_image_filenames=image_group.images
    )
except Exception as ex:
    print '\n!EXCEPTION: ' + str(ex) + '\n'
