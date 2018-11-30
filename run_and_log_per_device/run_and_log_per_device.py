#!/usr/bin/python3

"""
Loop over a list of devices in a YAML file and run a list of commands on them.
Store all the output from each device in a per-device file.
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
from netmiko.ssh_exception import NetMikoAuthenticationException
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
            print("Target config file doesn't exist: {}".format(args['cmd_dir']))
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
        cmd_file = open(filename)
    except Exception:
        print("Couldn't open comand file {}".format(filename))
        return False

    try:
        with open(filename) as file:
            lines = [line.strip() for line in file]
    except Exception as e:
        print("Couldn't load command file {}: {}".format(filename, e))
        return False

    cmd_file.close()

    return lines


def load_inv(filename, dev_os=None):

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
    if dev_os:
        filtered_inventory = {}
        for dev, opt in inventory.items():
            if opt['os'] == dev_os:
                filtered_inventory[dev] = opt
    else:
        filtered_inventory = inventory

    return filtered_inventory


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Loop over a list of devices in a YAML file and run '
                    'a list of commands on them.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-c', '--cmd-dir',
        help='Path to the command file(s) directory. If using -t|--target '
             'this is a single file to run against that host.',
        type=str,
        default='./configs',
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
    args['password'] = getpass("Default password:")
    

    # If an inventory file isn't being used, build a single-host-inventory
    if not args['target']:
        inventory = load_inv(args['inventory_file'], args['os'])
    else:
        if not args['os']:
            print("-t option used without -o! Can't configure {}".
                  format(args['target']))
            sys.exit(1)
        else:
            inventory = {
                         args['target']: {
                          'hostname': args['target'],
                          'os': args['os'],
                         },
                        }


    if not check_cmd_files_exist(args, inventory):
        sys.exit(1)

    if not check_log_path_exists(args['log_dir']):
        sys.exit(1)


    for dev, opt in inventory.items():

        print("Trying {}...".format(dev))

        if opt['os'] not in SUPPORTED_DRIVERS:
            print("{} has an unsupported device OS type: {}".format(dev, opt['os']))
            continue

        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        output_file = args['log_dir']+'/'+dev+'_'+timestamp+'.txt'
        try:
            output_log = open(output_file, "w")
        except Exception as e:
            print("Couldn't open output log file {}: {}".format(output_file, e))
            continue

        if not set_dev_opts(args, opt):
            continue

        cmds = load_cmds(args, opt)
        if not cmds:
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

        # The list of commands loaded from the text file and passed to
        # device.cli() is processed as a single list, if one of the commands
        # fails to run the remaining commands in the list aren't run. The
        # output cli dict can no longer be saved to a file. Pass each command
        # as a one item list to device.cli() to allow for commands to fail
        cli_output = {}
        for cmd in cmds:
            command = [cmd]
            try:
                output = device.cli(command)
                cli_output[cmd] = output[cmd]
            except Exception as e:
                print("Couldn't run a command on {}: {}".format(dev, e))
                cli_output[cmd] = ""

        try:
            # cli_output dict is unordered, use the original command list to
            # write the command output in the same order the commands where
            # executed
            for cmd in cmds:
                output_log.write('#'+cmd+'\n')
                output_log.write(cli_output[cmd]+'\n\n')
        except Exception as e:
            print("Couldn't save CLI output from {}: {}".format(dev, e))

        output_log.close()
        device.close()

        print("{} done".format(dev))

    return


if __name__ == '__main__':
    sys.exit(main())
