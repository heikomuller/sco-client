import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import scocli.client as scocli

def print_resource_list(title, resources, func):
    print title
    for res in resources:
        print_resource(res)
        print_resource(func(res.identifier))

def print_resource(res):
    print res.identifier + '\t' + res.name + '\t' + str(res.timestamp) + '\t' + str(res.properties)
    if res.has_file:
        f = res.file
        print 'Got ' + str(f.name)

sco = scocli.SCOClient('http://localhost:5050/sco/api/v1', data_dir='/home/heiko/.sco')

print_resource_list('Image Groups', sco.image_groups_list(properties=['filename']), sco.image_groups_get)
print_resource_list('Subjects', sco.subjects_list(), sco.subjects_get)
