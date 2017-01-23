import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import scocli

sco = scocli.SCOClient(data_dir='/home/heiko/.sco')
#
# LIST SUBJECTS
#
for subj in sco.subjects_list(properties=['filename']):
    cols = [subj.identifier, subj.name, str(subj.timestamp), subj.properties['filename']]
    print '\t'.join(cols)
    s = sco.subjects_get(subj.url)
    print s.data_dir
#sco.cache_clear()
#
# LIST IMAGE GROUPS
#
for img_grp in sco.image_groups_list():
    cols = [img_grp.identifier, img_grp.name, str(img_grp.timestamp)]
    print '\t'.join(cols)
    ig = sco.image_groups_get(img_grp.url)
    for img in ig.images:
        print img
        print os.path.isfile(img)
#
# LIST EXPERIMENTS
#
for expr in sco.experiments_list():
    cols = [expr.identifier, expr.name, str(expr.timestamp)]
    print '\t'.join(cols)
    e = sco.experiments_get(expr.url)
    print '\t\t' + e.subject.data_dir
    for img in e.image_group.images:
        print '\t\t' + img
