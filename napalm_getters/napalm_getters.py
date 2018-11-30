#!/usr/bin/python3

"""
Loop over a list of devices in a YAML inventory file and run all the the built
in NAPALM getters against each device. Log the output to a per-device file as
structed YAML data.

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
    port: 23 # Default is 22
    verbose: True # Default is False
R2:
  hostname: 192.168.188.2
  os: junos
  optional_args:
    config_lock: True
"""


import argparse
from datetime import datetime
from getpass import getpass
from jnpr.junos.exception import ConnectAuthError as JuniperConnectAuthError
from jnpr.junos.exception import ConnectRefusedError as JuniperConnectRefusedError
import napalm
from napalm._SUPPORTED_DRIVERS import SUPPORTED_DRIVERS
from napalm.base.exceptions import ConnectionException
from napalm.base.exceptions import LockError
from napalm.base.exceptions import MergeConfigException
from napalm.base.exceptions import ReplaceConfigException
from napalm.base.exceptions import UnlockError
from netmiko.utilities import get_structured_data
from netmiko.ssh_exception import NetMikoAuthenticationException
import os
from paramiko.ssh_exception import SSHException
import pprint
from socket import error as SocketError
from socket import timeout as SocketTimeout
import sys
import yaml


def check_log_path_exists(log_dir):

    if not os.path.isdir(log_dir):
        print("Path to output logging directory doesn't exist: {}".
               format(log_dir))
        try:
            os.mkdir(log_dir)
            print("Created directory: {}".format(log_dir))
            return True
        except Exception:
            print("Couldn't create directory: {}".format(log_dir))
            return False
    else:
        return True


def get_port(device):

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

    return port


def get_transport(device):

    transport = "unknown"
    try:
        if device.transport:
            transport = device.transport
    except (AttributeError):
        pass

    return transport


def load_inv(filename, type=None):

    try:
        inventory_file = open(filename)
    except Exception:
        print("Couldnt open inventory file {}".format(filename))
        sys.exit(1)

    try:
        inventory = yaml.load(inventory_file)
    except Exception as e:
        print("Couldn't load YAML file {}: {}".format(filename, e))
        sys.exit(1)

    inventory_file.close()

    # Filter the inventory down to the specified type if one is supplied
    if type:
        filtered_inventory = {}
        for dev, opt in inventory.items():
            if opt['os'] == type:
                filtered_inventory[dev] = opt
    else:
        filtered_inventory = inventory

    return filtered_inventory


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Loop over a list of devices in an inventory file log '
                    'the structured output of every NAPALM getter to a file.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-i', '--inventory-file',
        help='Input YAML inventory file',
        type=str,
        default='inventory.yml',
    )
    parser.add_argument(
        '-l', '--log-dir',
        help='Path to the output logging directory',
        type=str,
        default='./logs',
    )
    parser.add_argument(
        '-t', '--type',
        help='Only process devices with the specific OS type e.g. ios or junos',
        type=str,
        default=None,
    )
    parser.add_argument(
        '-u', '--username',
        help='Default username for device access',
        type=str,
        default=None,
    )

    return vars(parser.parse_args())


def set_dev_opts(args, opt):

    if 'username' not in opt:
        if not args['username']:
            print ("No username specified")
            return False
        else:   
            opt['username'] = args['username']

    if 'password' not in opt:
        opt['password'] = args['password']
        if opt['password'] == "":
            print("No password specified")
            return False

    if 'optional_args' not in opt:
        opt['optional_args'] = None

    return True


def main():
    
    args = parse_cli_args()
    args['password'] = getpass("Default password:")
    
    inventory = load_inv(args['inventory_file'], args['type'])

    if not check_log_path_exists(args['log_dir']):
        sys.exit(1)


    for dev, opt in inventory.items():

        print("Trying {}...".format(dev))

        if opt['os'] not in SUPPORTED_DRIVERS:
            print("{} has an unsupported device OS type: {}".format(dev, opt['os']))
            continue

        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        output_file = args['log_dir']+'/'+dev+'_'+timestamp+'.yml'
        try:
            output_log = open(output_file, 'w')
        except Exception:
            print("Couldn't open output log file {}".format(output_log))
            continue

        if not set_dev_opts(args, opt):
            continue

        driver = napalm.get_network_driver(opt['os'])
        
        # If Kwargs doesn't have exactly the keys required (no extras)
        # driver() will throw an exception
        opt.pop('os')
        device = driver(**opt)

        # Try to get the transport port number and type for debug messages
        port = get_port(device)
        transport = get_transport(device)

        # Connect to the device
        try:
           device.open()
        except (JuniperConnectAuthError, NetMikoAuthenticationException):
            print("Unable to authenticate to {} as {}".
                  format(opt['hostname'], opt['username']))
            continue
        except (ConnectionException, JuniperConnectRefusedError, SocketError,
                SocketTimeout, SSHException):
            print("Unable to connect to: {} using {} on port {}".
                  format(opt['hostname'], transport, port))
            continue


        structured_output = {}


        try:
            bgp_neighbours = device.get_bgp_neighbors()
            structured_output['get_bgp_neighbors'] = bgp_neighbours
        except Exception:
            print("Couldn't get BGP neighbours from {}".
                  format(opt['hostname']))
        

        '''
        # IOS bugs when the neighour is UP?!
        # Also only supports IPv4/IPv6 unicast AFI/SAFI
        
        structured_output['get_bgp_neighbors_detail'] = {}

        # table will be a tuple,
        # entry 0 is the routerID
        # entry 1 is the dict of peers
        for table in bgp_neighbours.items():
            
            # Each 'peer' will be a dict,
            # key is the BGP peer IP and val is a defaultdict,
            # with a single entry which is also default dict,
            # which contains all the BGP peer details
            if table[1]['peers']:
                for neighbour in table[1]['peers'].keys():
                    try:
                        bgp_neighbours_detailed = device.get_bgp_neighbors_detail(neighbour)
                        for k1, v1 in bgp_neighbours_detailed.items():
                            for k2, v2 in v1.items():
                                structured_output['get_bgp_neighbors_detail'][neighbour] = v2[0]
                    except Exception as e:
                        print("Couldn't get detailed BGP neighbour information"
                              " from {} for {}".format(opt['hostname'], neighbour))
                        print(e)
                        sys.exit(1)
                        #continue
        '''

        try:
            environment = device.get_environment()
            structured_output['get_environment'] = environment
        except Exception:
            print("Couldn't get environment details from {}".
                  format(opt['hostname']))

        try:
            facts = device.get_facts()
            structured_output['get_facts'] = facts
        except Exception:
            print("Couldn't get facts from {}".
                  format(opt['hostname']))

        try:
            interfaces = device.get_interfaces()
            structured_output['get_interfaces'] = interfaces
        except Exception:
            print("Couldn't get interfaces from {}".
                  format(opt['hostname']))

        try:
            interface_counters = device.get_interfaces_counters()
            structured_output['get_interfaces_counters'] = interface_counters
        except Exception:
            print("Couldn't get interface counters from {}".
                  format(opt['hostname']))

        try:
            interface_ips = device.get_interfaces_ip()
            structured_output['get_interfaces_ip'] = interface_ips
        except Exception:
            print("Couldn't get interface IPs from {}".
                  format(opt['hostname']))

        try:
            vrfs = device.get_network_instances()
            structured_output['get_network_instances'] = vrfs
        except Exception:
            print("Couldn't get VRFs from {}".
                  format(opt['hostname']))

        try:
            optics = device.get_optics()
            structured_output['get_optics'] = optics
        except Exception:
            print("Couldn't get optics from {}".
                  format(opt['hostname']))
        try:
            snmp = device.get_snmp_information()
            structured_output['get_snmp_information'] = snmp
        except Exception:
            print("Couldn't get optics from {}".
                  format(opt['hostname']))

        try:
            ntp_servers = device.get_ntp_servers()
            structured_output['get_ntp_servers'] = ntp_servers
        except Exception:
            print("Couldn't get optics from {}".
                  format(opt['hostname']))

        try:
            ntp_stats = device.get_ntp_stats()
            structured_output['get_ntp_stats'] = ntp_stats
        except Exception:
            print("Couldn't get optics from {}".
                  format(opt['hostname']))


        try:
            yaml.dump(structured_output, output_log, default_flow_style=False)
        except Exception:
            print("Couldn't serialise CLI output to YAML")


        output_log.close()
        device.close()

        print("{} done".format(dev))

    return


if __name__ == '__main__':
    sys.exit(main())
