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
import yaml

import rackspace_auth_openstack.plugin
from novaclient.v1_1 import client
import paramiko


logging.basicConfig(level=logging.INFO)

__VER__ = '0.0.2'

ENDPOINT = rackspace_auth_openstack.plugin.auth_url_us()

def main():

    config = ConfigParser.ConfigParser()
    config.read('settings.ini')

    server_config = yaml.load(open('provision.cfg').read())

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
    provision(nova, server_config)
    wait_all_built(nova)
    tag_hosts(nova, server_config)
    set_password(nova, vm_password)
    print_server_ip(nova)
    add_ssh_key_all_hosts(nova, vm_password, idrsa)

def tag_hosts(nova, server_config):

    for server in nova.servers.list():
        try:
            group = server_config['environment']['dev1']['hosts'][server.name]['group']  #@todo fix hardcoded dev1
            nova.servers.set_meta(server, {'group': group})
        except Exception, ex:
            print "Exception in tag_hosts: %s" % ex


def print_server_ip(nova):
    f = open('provision.hosts', 'w')
    
    groups = {}

    f.write('[frontend]\n')
    for server in nova.servers.list():
        group = server.metadata['group']
        try:
            groups[group] = groups[group] + (server.networks['public'][0],)
        except:
            groups[group] = (server.networks['public'][0],)
        
        # @todo, the public field has a ipv4 and ipv6 ip address encoded in it.  this isnt a safe way
        # to get the ip.

    for group in groups.keys():
        f.write('[%s]\n' % group)
        for item in groups[group]:
            f.write('%s\n' % item)

def set_password(nova, vm_password):
    for server in nova.servers.list():
        server.change_password(vm_password)

def add_ssh_key_all_hosts(nova, vm_password, idrsa):
    for server in nova.servers.list():
        try:
            add_ssh_key(server.networks['public'][0], vm_password, idrsa)
        except:
            raise
 
def add_ssh_key(ip, password, idrsa):
    """ @todo make this only insert the authorized key once.. """
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
            if host.status !=  'ACTIVE':
                all_built = False

        if not all_built:
            time.sleep(30)

def provision(nova, server_config):

    known_hosts = [s.name for s in nova.servers.list()]

    for environment in server_config['environment'].iterkeys():
        logging.info("Provision: Processing %s " % environment)
        hosts = server_config['environment'][environment]['hosts']

        for host in hosts.iterkeys():
            if host not in known_hosts:
                logging.info('Provision: Creating new host %s' % host)
                a = nova.servers.create(host, hosts[host]['image'], hosts[host]['flavor'])
                
if __name__ == "__main__":
    main()


