#!/usr/bin/python3

"""
Run a config rollback on each device in the inventory.

sudo -H pip3 install napalm

example inventory.yml:
---
# required: hostname, os
# optional: username, password, timeout, optional_args
R1: 
  hostname: 192.168.223.2
  os: ios
R2:
  hostname: 192.168.188.2
  os: junos
"""


import argparse
from datetime import datetime
from getpass import getpass
from jnpr.junos.exception import ConnectAuthError as JuniperConnectAuthError
from jnpr.junos.exception import ConnectRefusedError as JuniperConnectRefusedError
from jnpr.junos.exception import ConnectUnknownHostError as JuniperConnectUnknownHostError
import napalm
from napalm._SUPPORTED_DRIVERS import SUPPORTED_DRIVERS
from napalm.base.exceptions import ConnectionException
from napalm.base.exceptions import LockError
from napalm.base.exceptions import MergeConfigException
from napalm.base.exceptions import ReplaceConfigException
from napalm.base.exceptions import UnlockError
from netmiko.ssh_exception import NetMikoAuthenticationException
from netmiko.ssh_exception import NetMikoTimeoutException
import os
from paramiko.ssh_exception import SSHException
from socket import error as SocketError
from socket import timeout as SocketTimeout
import sys
import yaml


def build_inventory(args):

    # If not running in single host / target mode, load an inventory file
    if not args['target']:
        inventory = load_inv(args)
        if len(inventory.keys()) == 0:
            print("Empty device inventory, quitting")
            return False
        else:
            print("Loaded {} device(s) in inventory".
                  format(len(inventory.keys())))
            return inventory

    # If target mode is being used, build a one-host-inventory.
    # First check the user has supplied the minimum required information:
    else:
        if not args['os']:
            print("-t option used without -o! Can't configure {}".
                  format(args['target']))
            return False

        if (not args['username']) or (not args['password']):
            print("Username and password not specified!")
            return False
            
        else:
            inventory = {
                         args['target']: {
                          'hostname': args['target'],
                          'os': args['os'],
                         },
                        }
            if not set_dev_opts(args, inventory[args['target']]):
                return False
            else:
                return inventory


def dev_connect(device, opt, port, transport):

    try:
       device.open()
    except (JuniperConnectAuthError, NetMikoAuthenticationException):
        print("Unable to authenticate to {} as {}".
              format(opt['hostname'], opt['username']))
        return False
    except (ConnectionException, JuniperConnectRefusedError, 
            JuniperConnectUnknownHostError, SocketError,
            SocketTimeout, SSHException):
        print("Unable to connect to {} using {} on port {}".
              format(opt['hostname'], transport, port))
        return False
    except ValueError as e:
        print("Unable to connect to {}: {}".format(opt['hostname'], e))
        return False

    return True


def filter_inv(inventory, os_type):

    # Filter the inventory down to the specified type:
    filtered_inv = {}
    for dev, opt in inventory.items():
        if opt['os'] == os_type:
            filtered_inv[dev] = opt

    return filtered_inv


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


def load_inv(args):

    print("Loading inventory {}".format(args['inventory_file']))

    # Load the initial inventory from a YAML file
    try:
        inventory_file = open(args['inventory_file'])
    except Exception as e:
        print("Couldn't open inventory file {}".format(e))
        sys.exit(1)

    try:
        raw_inventory = yaml.load(inventory_file)
    except Exception as e:
        print("Couldn't load inventory YAML: {}".format(e))
        sys.exit(1)

    inventory_file.close()

    # Filter the inventory to a specific device OS if specified
    if args['os']:
        filtered_inv = filter_inv(raw_inventory, args['os'])
    else:
        filtered_inv = raw_inventory

    inventory = filtered_inv.copy()

    for dev, opt in filtered_inv.items():

        # Remove any unsupported OS types from the inventory
        if opt['os'] not in SUPPORTED_DRIVERS:
            print("Removing {}, unsupported device OS type: {}".
                  format(dev, opt['os']))
            inventory.pop(dev)
            continue

        # Remove devices with invalid settings e.g. missing username/password
        if not set_dev_opts(args, opt):
            print("Removing {}".format(dev))
            inventory.pop(dev)

    return inventory


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Run a config rollback on each device in the inventory.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-i', '--inventory-file',
        help='Device inventory file (YAML formatted). This is the default mode. '
             'Use -t|--target to run this script against a single host (the '
             '-i option and any inventory file present will be ignored).',
        type=str,
        default='./inventory.yml',
    )
    parser.add_argument(
        '-o', '--os',
        help='Only process devices from the inventory file with the specific '
             'OS type e.g. ios or junos. This is optional with an inventory '
             'file but mandatory for a single device when using -t|--target.',
        type=str,
        default=None,
    )
    parser.add_argument(
        '-p', '--password',
        help='Specify a default password. If a per-device password is '
             'specified in the inventory file the inventory password is used. '
             'This is a default password for use when a per-device password '
             'hasn\'t been included in the inventory file. Storing passwords '
             'in an inventory file is insecure and only good for testing. '
             'This option is also not a good idea becuase your password might '
             'show up in your CLI history. Without this option the script '
             'will prompt for a default password, which is safer.',
        type=str,
        default=None,
    )
    parser.add_argument(
        '-t', '--target',
        help='Hostname or IP of target device to configure. When using this '
             'option you MUST specify the device OS type using -o|--os . '
             'This option overrides the -i option and any inventory file is '
             'ignored.',
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


def rollback_ios(dev, device):


    """
    When applying config using NAPALM the IOS driver by default makes a
    config backup on the device called rollback_config.txt, before any changes
    are made.
    """
    ios_cmd = "configure replace flash:rollback_config.txt force"

    try:
        device._file_prompt_quiet()
        output = device.cli([ios_cmd])
        if not output:
            print("{} rollback failed: {}".format(dev, output[ios_cmd]))
            return False
        elif "rror" in output[ios_cmd]:
            print("{} rollback failed: {}".format(dev, output[ios_cmd]))
            return False
        else:
            print("{} {}".format(dev, output[ios_cmd]))
            return True
    except Exception as e:
        print("Couldn't perform the rollback on {}: {}".format(dev, e))
        return False


def rollback_junos(dev, device):

    """
    NAPALM rollback() function runs `rollback 1` && `commit`.
    The other way to do this would be to use the PyEz library directly
    through NAPALMs instantiation of it:
    https://github.com/Juniper/py-junos-eznc/blob/master/lib/jnpr/junos/utils/config.py
    PyEz rollback() runs `rollback 1` then you need to commit().

    try:
        # PyEz rollback() returns a bool value of True on success
        rollback = device.device.cu.rollback(rb_id=1)
        if not rollback:
            print("{} rollback failed: {}".format(dev, rollback))
        # commit_config() doesn't return anything!
        device.commit_config()
    except JuniperCommitError as e:
        print("Couldn't commit rollback config on {} (JuniperCommitError): {}".format(dev, e))
    except JuniperRpcTimeoutError as e:
        print("Couldn't commit rollback config on {} (JuniperRpcTimeoutErroras): {}".format(dev, e))
    except JuniperUnlockError as e:
        print("Couldn't commit rollback config on {} (JuniperUnlockError): {}".format(dev, e))
    except MergeConfigException as e:
        print("Couldn't commit rollback config on {} (MergeConfigException): {}".format(dev, e))
    """

    try:
        # rollback() doesn't return anything!
        device.rollback()
        print("{} rolled back".format(dev))
        return True
    except Exception as e:
        print("Couldn't perform the rollback on {}: {}".format(dev, e))
        return False


def set_dev_opts(args, opt):

    if 'username' not in opt:
        if not args['username']:
            print ("No username specified")
            return False
        else:   
            opt['username'] = args['username']

    if ('password' not in opt) or (not opt['password']):
        opt['password'] = args['password']
        if opt['password'] == "":
            print("No password specified")
            return False

    if 'optional_args' not in opt:
        opt['optional_args'] = None

    return True


def main():
    
    args = parse_cli_args()
    if not args['password']:
        args['password'] = getpass("Default password:")

    inventory = build_inventory(args)
    if not inventory:
        sys.exit(1)

    ret_val = True
    for dev, opt in inventory.items():

        print("Trying {}...".format(dev))

        driver = napalm.get_network_driver(opt['os'])
        
        # If Kwargs doesn't have exactly the keys required (no extras)
        # driver() will throw an exception
        os = opt['os']
        opt.pop('os')
        device = driver(**opt)

        # Try to get the transport port number and type for debug messages
        port = get_port(device)
        transport = get_transport(device)

        # Connect to the device
        if not dev_connect(device, opt, port, transport):
            ret_val = False
            continue

        if os == 'ios':
            output = rollback_ios(dev, device)
        elif os == 'junos':
            output = rollback_junos(dev, device)
        else:
            print("Unsupported device type {}, skipping {}!".format(os, dev))

        if not output:
            ret_val = False

        device.close()
        print("{} done".format(dev))


    if ret_val:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
