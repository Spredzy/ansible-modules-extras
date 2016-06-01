#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Yanis Guenane <yanis+ansible@guenane.org>
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from ansible.module_utils.basic import *

import os

class ResourceRecord(object):

    def __init__(self, **kwargs):

        if not kwargs.get('name') and not kwargs.get('origin'):
            # NOTE: Raise an exception
            pass
        elif not kwargs.get('name') and kwargs.get('origin'):
            self.full_name = kwargs.get('origin')
        elif kwargs.get('name') and not kwargs.get('origin'):
            self.full_name = kwargs.get('name')
        else:
            if kwargs.get('origin') == '.':
                self.full_name = '%s%s' % (kwargs.get('name'), kwargs.get('origin', ''))
            else:
                self.full_name = '%s.%s' % (kwargs.get('name'), kwargs.get('origin', ''))

        self.name = kwargs.get('name')
        self.ttl = kwargs.get('ttl')
        self.rr_class = kwargs.get('rr_class')
        self.type = kwargs.get('type')
        self.value = kwargs.get('value')

        # For records of type: SRV, MX
        self.priority = kwargs.get('priority')

        # For records of type: SRV
        self.weight = kwargs.get('weight')
        self.port = kwargs.get('port')


def load_zone_file(module, file_path, origin):
    '''Load the zone file.'''

    zone = []

    # If the zone file does not exist create it
    if not os.path.exists(file_path):
        return zone

    # If the file is empty return an empty array
    if os.stat(file_path).st_size == 0:
        return zone

    # Else load the zone file
    for line in open(file_path):
        current_line =  line.rstrip('\n').split()
        name, ttl, rr_class, type = current_line[:4]
        data = current_line[4:]


        if name == origin:
            name = None
        else:
            name = name[:name.find(origin) - 1]


        priority = None
        weight = None
        port = None

        if type == 'MX':
            priority, value = data
        elif type == 'SRV':
            priority, weight, port, value = data
        else:
            value = data[0]
               
        rr = {
          'name': name,
          'origin': origin,
          'ttl': ttl,
          'rr_class': rr_class,
          'type': type,
          'value': value,
          'priority': priority,
          'weight': weight,
          'port': port
        }
    
        zone.append(ResourceRecord(**rr))

    return zone


def main():

    module = AnsibleModule(
        argument_spec = dict(
            state=dict(default='present', choices=['present', 'absent'], type='str'),
            zone_file=dict(required=True, type='path'),
            origin=dict(default='.', type='str'),
            name=dict(type='str'),
            ttl=dict(default=86400, type='int'),
            rr_class=dict(default='IN', choices=['IN', 'CH', 'HS'], type='str'),
            type=dict(required=True, choices=['A', 'AAAA', 'CNAME', 'SRV', 'PTR', 'NS', 'MX', 'SOA', 'TXT'], type='str'),
            value=dict(required=True, type='str'),

            # For records of type: SRV, MX
            priority=dict(default=0, type='int'),

            # For records of type: SRV
            weight=dict(type='int'),
            port=dict(type='int'),
        )
    )

    rrs = load_zone_file(module, module.params['zone_file'], module.params['origin'])

    rr_obj = {
      'name': module.params['name'],
      'origin': module.params['origin'],
      'ttl': module.params['ttl'],
      'rr_class': module.params['rr_class'],
      'type': module.params['type'],
      'value': module.params['value'],
      'priority': module.params['priority'],
      'weight': module.params['weight'],
      'port': module.params['port']
    }
    rr = ResourceRecord(**rr_obj)

    if rr.type not in ['MX', 'SRV', 'NS']:
        if not any(l_rr.full_name == rr.full_name and l_rr.type == rr.type for l_rr in rrs):
            rrs.append(rr)
        else:
            for l_rr in rrs :
                if l_rr.full_name == rr.full_name and l_rr.type == rr.type:
                    l_rr.ttl = rr.ttl
                    l_rr.value = rr.value
    elif rr.type in ['NS', 'MX', 'SRV']:
        if not any(l_rr.full_name == rr.full_name and l_rr.type == rr.type and l_rr.value == rr.value  for l_rr in rrs):
            rrs.append(rr)


    with open(module.params['zone_file'], 'w') as f:
        for l_rr in rrs:
            if l_rr.type not in ['MX', 'SRV']:
                f.write('%s\t%s\t%s\t%s\t%s\n' % (l_rr.full_name, l_rr.ttl, l_rr.rr_class, l_rr.type, l_rr.value))
            elif l_rr.type == 'MX':
                f.write('%s\t%s\t%s\t%s\t%s\t%s\n' % (l_rr.full_name, l_rr.ttl, l_rr.rr_class, l_rr.type, l_rr.priority, l_rr.value))
            elif l_rr.type == 'SRV':
                f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (l_rr.full_name, l_rr.ttl, l_rr.rr_class, l_rr.type, l_rr.priority, l_rr.weight, l_rr.port, l_rr.value))

   
    module.exit_json(changed=True, rr=rr.__dict__)


if __name__ == '__main__':
    main()
