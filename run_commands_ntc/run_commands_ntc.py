#!/usr/bin/python3

"""
Loop over a list of devices in a YAML file and run a list of commands on them.
Place commands in files with the os type called "cmd_ios.txt" and 
"cmd_junos.txt" etc. and the script will load the file based on the 'os' value
of the device in the inventory file.

This script will try to pass the CLI output through an NTC template if one 
exists and save the output as structured data (YAML).

sudo -H pip3 install napalm
git clone https://github.com/networktocode/ntc-templates.git
export NET_TEXTFSM=/full/path/to/ntc-templates

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
from socket import error as SocketError
from socket import timeout as SocketTimeout
import sys
import yaml


def check_cmd_files_exist(args, inventory):

    # Check all types of command files exist
    for dev, opt in inventory.items():

        if opt['os'] not in SUPPORTED_DRIVERS:
            continue

        cmd_file = args['cmd_dir']+'/cmd_'+opt['os']+'.txt'

        if not os.path.isfile(cmd_file):
            print("Command file doesn't exist: {}".format(cmd_file))
            return False

    return True


def check_files_path_exists(cmd_dir):

    if not os.path.isdir(cmd_dir):
        print("Path to command file(s) directory doesn't exist: {}".
               format(cmd_dir))
        return False
    else:
        return True


def check_log_path_exists(log_dir):

    if not os.path.isdir(log_dir):
        print("Path to output logging directory doesn't exist: {}".
               format(log_dir))
        try:
            os.makedirs(log_dir, exist_ok=True)
            print("Created directory: {}".format(log_dir))
            return True
        except Exception:
            print("Couldn't create directory: {}".format(log_dir))
            return False
    else:
        return True


def get_ntc_type(os):

    # Convert NAPALM device types to NTC Template device types

    if os == 'ios':
        return 'cisco_ios'
    elif os == 'iosxr':
        return 'cisco_xr'
    elif os == 'junos':
        return 'juniper_junos'
    else:
        return False


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
        description='Loop over a list of devices in a YAML file and run '
                    'a list of commands on them, stored the output in a '
                    'structured format.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-c', '--cmd-dir',
        help='Path to the command file(s) directory',
        type=str,
        default='./configs',
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
    
    inventory = load_inv(args['inventory_file'], args['type'])

    if not check_files_path_exists(args['cmd_dir']):
        sys.exit(1)

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
        output_file = args['log_dir']+'/'+dev+'_'+timestamp+'.yml'
        try:
            output_log = open(output_file, 'w')
        except Exception:
            print("Couldn't open output log file {}".format(output_log))
            continue

        if not set_dev_opts(args, opt):
            continue

        cmds = load_cmds(args, opt)
        if not cmds:
            continue

        device_type = get_ntc_type(opt['os'])
        #if not device_type:
        #    continue

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

        # cli() returns a dict, the key is the cli command and the value is
        # the raw output
        ##cli_output = device.cli(cmds)
        #
        # If there is a command that is not like any other command, e.g.
        # "foo-bar" - this will fail to execute and the CLI output will
        # contain an error string like "Unknown command" from Junos or
        # "invalid command" from IOS. If the command is similar to a real
        # command, e.g. "show foo-bar", an IOS device / Netmiko will
        # throw and exception and no output for any of the commands that
        # did successfully execute are returned.
        # For this reason we need loop over othe command list and build
        # the output dict manually:
        cli_output = {}
        for cmd in cmds:
            try:
                raw_output = device.cli([cmd])
                cli_output[cmd] = raw_output[cmd]
            except Exception as e:
                print("Coudn't execute CLI commands: {}".format(e))
                cli_output[cmd] = None

        dev_structured_output = {}
        
        for cmd in cmds:
            cmd_output = cli_output[cmd]
            # get_structured_data() returns a list of dicts, each dict is
            # the structured form of the commmand output (e.g. one dict
            # per interface when running "show interfaces")
            structured_output = get_structured_data(cmd_output, platform=device_type, command=cmd)
            dev_structured_output[cmd] = structured_output


        try:
            yaml.dump(dev_structured_output, output_log, default_flow_style=False)
        except Exception:
            print("Couldn't serialise CLI output to YAML")
            #continue

        output_log.close()
        device.close()

        print("{} done".format(dev))

    return


if __name__ == '__main__':
    sys.exit(main())
