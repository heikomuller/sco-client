"""Print listings of subjects, image groups and experiments on SCO-API."""

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import scocli

# Connect to default SCO-API. Uses a temporary directory to store files in
# local cache
sco = scocli.SCOClient()

# List all subjects (including their filename)
for subj in sco.subjects_list(properties=['filename']):
    cols = [subj.identifier, subj.name, str(subj.timestamp), subj.properties['filename']]
    print '\t'.join(cols)

# List all image groups
for img_grp in sco.image_groups_list():
    cols = [img_grp.identifier, img_grp.name, str(img_grp.timestamp)]
    print '\t'.join(cols)

# List all experiments
for expr in sco.experiments_list():
    cols = [expr.identifier, expr.name, str(expr.timestamp)]
    print '\t'.join(cols)
