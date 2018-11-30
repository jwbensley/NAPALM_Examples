#!/usr/bin/python3

"""
Loop over a list of devices in a YAML file and run a list of commands on them.
Store command output from each command in a per-command file.
The commands being executed are stored in files with the device os type in the
fileaname e.g. "cmd_ios.txt" or "cmd_junos.txt" etc. The script will load the
file based on the 'os' value of the device in the inventory file. Commands
are run in the order they are listed in the input files.

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


def check_cmd_files_exist(args, inventory):

    # If running in target mode the -c option points to a single config file
    if args['target']:
        if not os.path.isfile(args['cmd_dir']):
            print("Target command file doesn't exist: {}".format(args['cmd_dir']))
            return False
        else:
            return True

    # If not running in single host / target mode, check if the config 
    # directory exists
    if not os.path.isdir(args['cmd_dir']):
        print("Path to command file(s) directory doesn't exist: {}".
               format(conf_dir))
        return False

    # Check all types of command files exist
    for dev, opt in inventory.items():

        if opt['os'] not in SUPPORTED_DRIVERS:
            continue

        cmd_file = args['cmd_dir']+'/cmd_'+opt['os']+'.txt'

        if not os.path.isfile(cmd_file):
            print("Command file doesn't exist: {}".format(cmd_file))
            return False

    return True


def check_log_path_exists(log_dir):

    if not os.path.isdir(log_dir):
        #print("Path to output logging directory doesn't exist: {}".
        #       format(log_dir))
        try:
            os.makedirs(log_dir, exist_ok=True)
            print("Created directory: {}".format(log_dir))
            return True
        except Exception as e:
            print("Couldn't create directory {}: {}".format(log_dir, e))
            return False
    else:
        return True


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


def load_cmds(args, opt):

    lines = []

    if args['target']:
        filename = args['cmd_dir']
    else:
        filename = args['cmd_dir']+'/cmd_'+opt['os']+'.txt'

    if not os.path.isfile(filename):
        print("Command file doesn't exist: {}".format(filename))
        return False

    try:
        with open(filename) as file:
            lines = [line.strip() for line in file]
    except Exception as e:
        print("Couldn't load command file {}: {}".format(filename, e))
        return False

    file.close()

    return lines


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
        description='Loop over a list of devices in a YAML file and run '
                    'a list of commands on them, saving the output from each '
                    'command into a seperate text file.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-c', '--cmd-dir',
        help='Path to the command file(s) directory. If using -t|--target '
             'this is a single file to run against that host.',
        type=str,
        default='./commands',
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
        '-l', '--log-dir',
        help='Path to the output logging directory',
        type=str,
        default='./logs',
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


def run_cmd(command, dev, device):

    try:
        output = device.cli(command)
        return output
    except Exception as e:
        print("Couldn't run a command on {}: {}".format(dev, e))
        return False


def save_output(cmd, dev, log_dir, output):

    cmd_safe = "".join(x for x in cmd if (x.isalnum() or x in "._- "))
    output_file = log_dir+'/'+cmd_safe+'.txt'
    try:
        output_log = open(output_file, "w")
    except Exception as e:
        print("Couldn't open output log file {}: {}".format(output_file, e))
        return False

    try:
        output_log.write('#'+cmd+'\n')
        # output is a dict, the key is the CLI command
        # and the val is the CLI output
        output_log.write(output[cmd]+'\n\n')
    except Exception as e:
        print("Couldn't save CLI output from {}: {}".format(dev, e))
        return False

    output_log.close()

    return True


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
    

    # If target mode isn't being used (an inventory file is being used) remove
    # any unsupported devices and check for any OS filter:
    if not args['target']:
        inventory = load_inv(args)
        if len(inventory.keys()) == 0:
            print("Empty device inventory, quitting")
        else:
            print("Loaded {} device(s) in inventory".format(len(inventory.keys())))

    # If target mode is being used, build a one-host-inventory.
    # First check the user has supplied the minimum required information:
    else:
        if not args['os']:
            print("-t option used without -o, can't configure {}".
                  format(args['target']))
            sys.exit(1)
       
        if not args['username']:
            print("-t option used without -u, can't configure {}".
                format(args['target']))
            sys.exit(1)
        
        if not args['password']:
            print("-t option used without password, can't configure {}".
                format(args['target']))
            sys.exit(1)

        inventory = {
                     args['target']: {
                      'hostname': args['target'],
                      'os': args['os'],
                      'username': args['username'],
                      'password': args['password'],
                     },
                    }


    if not check_cmd_files_exist(args, inventory):
        sys.exit(1)

    if not check_log_path_exists(args['log_dir']):
        sys.exit(1)

    
    ret_val = True
    for dev, opt in inventory.items():

        print("Trying {}...".format(dev))

        cmds = load_cmds(args, opt)
        if not cmds:
            ret_val = False
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
        if not dev_connect(device, opt, port, transport):
            ret_val = False
            continue

        log_dir = args['log_dir']+'/'+dev
        check_log_path_exists(log_dir)        
        # The list of commands loaded from the text file and passed to
        # device.cli() is processed as a single list, if one of the commands
        # fails to run the remaining commands in the list aren't run. The
        # output dict returned by device.cli() is blank meaning that output
        # for commands that did execute is lost. Pass each command
        # as a one item list to device.cli() to allow for commands to fail:
        for cmd in cmds:

            command = [cmd]
            output = run_cmd(command, dev, device)

            if not output:
                ret_val = False
                continue

            if not save_output(cmd, dev, log_dir, output):
                ret_val = False
                continue

        device.close()
        print("{} done".format(dev))


    if ret_val:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
