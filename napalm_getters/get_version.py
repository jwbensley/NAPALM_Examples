#!/usr/bin/python3

"""
Loop over a list of devies in a YAML file and print their OS version

sudo -H pip3 install napalm

example inventory.yml:
---
# required: hostname, os
# optional: username, password, timeout, optional_args
R1: 
  hostname: 192.168.223.2
  os: ios
  username: admin
  password: admin
  timeout: 15 # Default is 60 seconds
  optional_args:
    secret: enable
    transport: telnet # Default is SSH
    port: 23
    verbose: True
R2:
  hostname: 192.168.188.2
  os: ios
"""


import argparse
from getpass import getpass
from jnpr.junos.exception import ConnectAuthError as JuniperConnectAuthError
from jnpr.junos.exception import ConnectRefusedError as JuniperConnectRefusedError
import napalm
from napalm.base.exceptions import ConnectionException
from netmiko.ssh_exception import NetMikoAuthenticationException
from paramiko.ssh_exception import SSHException
from socket import error as SocketError
from socket import timeout as SocketTimeout
import sys
import yaml


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Loop over a list of devices in a YAML file and print the device firmware version',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-i', '--inventory-file',
        help='Input YAML inventory file',
        type=str,
        default='inventory.yml',
    )
    parser.add_argument(
        '-u', '--username',
        help='Default username for device access',
        type=str,
        default=None,
    )

    return vars(parser.parse_args())


def main():
    
    args = parse_cli_args()
    args['password'] = getpass("Default password:")
    

    try:
        inventory_file = open(args['inventory_file'])
    except Exception:
        print('Couldn\'t open inventory file {}'.format(args['inventory_file']))

    try:
        inventory = yaml.load(inventory_file)
    except Exception as e:
        print("Failed to load YAML: {}".format(e))
        return 1

    inventory_file.close()


    for dev, opt in inventory.items():

        if 'username' not in opt:
            if not args['username']:
                print ('No username specified')
                return 1
            else:   
                opt['username'] = args['username']

        if 'password' not in opt:
            opt['password'] = args['password']

        if 'optional_args' not in opt:
            opt['optional_args'] = None

        driver = napalm.get_network_driver(opt['os'])
        
        # If Kwargs doesn't have exactly the keys required (no extras)
        # driver() will throw an exception
        opt.pop('os')

        device = driver(**opt)


        # Try to get the transport port number and type
        port = "unknown"
        try:
            if device.netmiko_optional_args['port']:
                port = device.netmiko_optional_args['port']
        except (AttributeError, KeyError):
            pass
        try:
            if device.port:
                port = device.port
        except AttributeError:
            pass

        transport = "unknown"
        try:
            if device.transport:
                transport = device.transport
        except (AttributeError):
            pass
        

        # Connect to the device
        try:
           device.open()
        except (JuniperConnectAuthError, NetMikoAuthenticationException):
            print("Unable to authenticate to {} as {}".format(opt['hostname'], opt['username']))
            continue
        except (ConnectionException, JuniperConnectRefusedError, SocketError, SocketTimeout, SSHException):
            print("Unable to connect to: {} using {} on port {}".
                  format(opt['hostname'], transport, port))
            continue
        
        try:
            facts = device.get_facts() # ['os_version']
            print("{}: {}".format(opt['hostname'], facts['os_version']))
        except Exception:
            print("Couldn't get facts from {}".format(opt['hostname']))
            device.close()
            continue

        device.close()

    return


if __name__ == '__main__':
    sys.exit(main())
