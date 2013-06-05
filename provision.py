#!/usr/bin/env python
#
# Filename: provision.py
# Author: Stan Brinkerhoff
#
# Commission up some hosts.
#

import ConfigParser
import logging
import sys
import time

import rackspace_auth_openstack.plugin
from novaclient.v1_1 import client
import paramiko


logging.basicConfig(level=logging.INFO)

__VER__ = '0.0.1'

API_KEY = 'Gr33neggs'
USERNAME = 'stanbrinkerhoff'

ENDPOINT = rackspace_auth_openstack.plugin.auth_url_us()

config = {
    'environment': {
        'dev1': {
            'hosts': {
                'dev.web1': {
                    'image': 'e4dbdba7-b2a4-4ee5-8e8f-4595b6d694ce', # Ubuntu LTS 12.04
                    'flavor': 2 # 512
                },
                'dev.web2': {
                    'image': 'e4dbdba7-b2a4-4ee5-8e8f-4595b6d694ce', # Ubuntu LTS 12.04
                    'flavor': 2 # 512
                },
                'dev.web3': {
                    'image': 'e4dbdba7-b2a4-4ee5-8e8f-4595b6d694ce', # Ubuntu LTS 12.04
                    'flavor': 2 # 512
                },
                'dev.middle1': {
                'image': 'e4dbdba7-b2a4-4ee5-8e8f-4595b6d694ce', # Ubuntu LTS 12.04
                'flavor': 2 # 512
                }
            }
        }
    }
}



def main():

    config = ConfigParser.ConfigParser()
    config.read('settings.ini')


    nova = client.Client(config.get('provision','username'),
                         config.get('provision','password'),
                         None,
                         ENDPOINT,
                         region_name=config.get('provision','region'),
                         http_log_debug=1
    )

    idrsa = open(config.get('provision','idrsa')).readlines()[0]
    vm_password = config.get('provision','vm_password')


    # Provision any un-provisioned hosts
    provision(nova)
    wait_all_built(nova)
    set_password(nova, vm_password)
    print_server_ip(nova)
    add_ssh_key_all_hosts(nova, vm_password, idrsa)

def print_server_ip(nova):
    f = open('provision.hosts', 'w')
    f.write('[frontend]\n')
    for server in nova.servers.list():
        # @todo, the public field has a ipv4 and ipv6 ip address encoded in it.  this isnt a safe way
        # to get the ip.
        logging.info("Server: %s, ip: %s" % (server.name, server.networks['public'][0]))
        f.write('%s\n' % server.networks['public'][0])

def set_password(nova, vm_password):
    for server in nova.servers.list():
        server.change_password(vm_password) # @todo load from settings file

def add_ssh_key_all_hosts(nova, vm_password, idrsa):
    for server in nova.servers.list():
        try:
            add_ssh_key(server.networks['public'][0], vm_password, idrsa)
        except:
            raise
 
def add_ssh_key(ip, password, idrsa):
    t = paramiko.SSHClient()
    t.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    t.connect(ip, username='root', password=password)
    t.exec_command("mkdir .ssh")
    t.exec_command("chmod 755 .ssh")
    t.exec_command("echo '%s' >> .ssh/authorized_keys" % idrsa) 
    

def wait_all_built(nova):

    all_built = False

    while not all_built:
        all_built = True
        known_hosts = nova.servers.list()
        for host in known_hosts:
            print host.status
            if host.status !=  'ACTIVE':
                all_built = False

        if not all_built:
            time.sleep(30)

def provision(nova):

    known_hosts = [s.name for s in nova.servers.list()]

    for environment in config['environment'].iterkeys():
        logging.info("Provision: Processing %s " % environment)
        hosts = config['environment'][environment]['hosts']

        for host in hosts.iterkeys():
            if host not in known_hosts:
                logging.info('Provision: Creating new host %s' % host)
                a = nova.servers.create(host, hosts[host]['image'], hosts[host]['flavor'])

if __name__ == "__main__":
    main()


