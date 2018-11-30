#!/usr/bin/python3

"""
Loop over a list of devies in a YAML file and apply the config stored in a
config file. The configuration can be applied to all devices as a merge
operation or all devices as a full replace operation, the two modes can't be
mixed. The config to be applied should be stored in a file with the type of the
device specified in the filename, E.g. merge_config_ios.txt for Cisco IOS or
merge_config_junos.txt for Juniper Junos. Call the files "replace_" to perform
a replace operation, E.g. replace_config_junos.txt or replace_config_ios.txt.

sudo -H pip3 install napalm

example inventory.yml:
---
# required: hostname, os
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
from jnpr.junos.exception import CommitError as JuniperCommitError
from jnpr.junos.exception import RpcTimeoutError as JuniperRpcTimeoutError
from jnpr.junos.exception import UnlockError as JuniperUnlockError
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


def check_config_files_exist(args, inventory):

    # If running in target mode the -c option points to a single config file
    if args['target']:
        if not os.path.isfile(args['configs']):
            print("Target config file doesn't exist: {}".format(args['configs']))
            return False
        else:
            return True

    # If not running in single host / target mode, check if the config 
    # directory exists
    if not os.path.isdir(args['configs']):
        print("Path to config file(s) directory doesn't exist: {}".
               format(conf_dir))
        return False

    # Check all types of command files exist within the config directory
    for dev, opt in inventory.items():

        if opt['os'] not in SUPPORTED_DRIVERS:
            continue

        if args['host']:
            config_file = args['configs']+'/'+dev+'.txt'
        elif args['replace']:
            config_file = args['configs']+'/replace_config_'+opt['os']+'.txt'
        else:
            config_file = args['configs']+'/merge_config_'+opt['os']+'.txt'

        if not os.path.isfile(config_file):
            if args['host']:
                print("Host config file {} doesn't exist".format(config_file))
            elif args['replace']:
                print("Replace config file {} doesn't exist".format(config_file))
            else:
                print("Merge config file {} doesn't exist".format(config_file))
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


def commit_check(dev, device):

    """
    NAPALM uses the PyEZ library. NAPALM has no "commit check" feature
    however, there is one available within the PyEz library. Below this is
    accessed directly through NAPALMs instantiation of the PyEZ library
    https://github.com/Juniper/py-junos-eznc/blob/master/lib/jnpr/junos/utils/config.py
    """

    try:
        check = device.device.cu.commit_check()
        if not check:
            print("Commit check failed on {}: {}".format(dev, check))
        else:
            print("Commit check passed on {}".format(dev))
    except JuniperCommitError as e:
        print("Commit check failed on {}: {}".format(dev, e))
    except Exception as e:
        print("Couldn't run commit check on {}: {}".format(dev, e))


def filter_inv(inventory, os_type):

    # Filter the inventory down to the specified type:
    filtered_inv = {}
    for dev, opt in inventory.items():
        if opt['os'] == os_type:
            filtered_inv[dev] = opt

    return filtered_inv


def get_diff(dev, device):

    try:
        return device.compare_config()
    except Exception as e:
        print("Couldn't generate diff on device {}: {}".format(dev, e))
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


def load_merge(config_file, dev, device):

    try:
        device.load_merge_candidate(filename=config_file)
        print("Loaded merge config")
        return True
    except MergeConfigException as e:
        print("Couldn't load merge config for {}: {}".format(dev, e))
        return False
    except LockError as e:
        print("Lock error during load_merge\n"
              "Is there uncommited config present on {}\n"
              "{}".format(dev, e))
        return False


def load_replace(config_file, dev, device):

    try:
        device.load_replace_candidate(filename=config_file)
        print("Loaded replace config")
        return True
    except (ReplaceConfigException, FileNotFoundError) as e:
        print("Couldn't load replace config for {}: {}".format(dev, e))
        return False
    except LockError as e:
        print("Lock error during load_replace\n"
              "Is there uncommited config present on {}\n"
              "{}".format(dev, e))
        return False


def merge_config(dev, device, note):

    try:
        device.commit_config(message=note)
        print("Merged")
    except JuniperCommitError as e:
        print("Couldn't merge config on {} (JuniperCommitError): {}".format(dev, e))
    except JuniperRpcTimeoutError as e:
        print("Couldn't merge config on {} (JuniperRpcTimeoutErroras): {}".format(dev, e))
    except JuniperUnlockError as e:
        print("Couldn't merge config on {} (JuniperUnlockError): {}".format(dev, e))
    except MergeConfigException as e:
        print("Couldn't merge config on {} (MergeConfigException): {}".format(dev, e))


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Loop over a list of devices in a YAML file and either '
                    'merge a partial config or replace a full config, loaded '
                    'from a file.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-c', '--configs',
        help='Directory where the merge/replace/or per-host configs are stored. '
             'In -t|--target mode this is a single config file.',
        type=str,
        default='./configs/',
    )
    parser.add_argument(
        '-d', '--dry-run',
        help='Perform a dry run, only generate a diff for each device.',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '--host',
        help='Switch to per-host config mode, the default is per-type/os. '
             'In per-host mode an individual config file must exist for each '
             'device in the inventory file rather than a per-os/type config.'
             'When using -t|--target option to configure a single host the '
             '--host option is ignored, it only applies to an inventory.',
        default=False,
        action='store_true',
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
        help='Path to the output logging directory.',
        type=str,
        default='./logs/',
    )
    parser.add_argument(
        '-n', '--note',
        help='Set the commit note/comment. Not all devices support commit '
             'comments.',
        type=str,
        default=None,
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
        '-r', '--replace',
        help='Replace the full device configuration.\n'
             'Merge is the default operation when this option isn\'t used.',
        default=False,
        action='store_true',
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
        help='Default username for device access.',
        type=str,
        default=None,
    )
    parser.add_argument(
        '-v', '--verify',
        help='Run \'commit check\' on Junos devices before applying. If the '
              'check fails, the config isn\'t merged/replaced. Good with the '
              ' -d | --dry-run option!',
        default=False,
        action='store_true',
    )

    return vars(parser.parse_args())


def replace_config(dev, device, note):

    try:
        device.commit_config(message=note)
        print("Replaced")
    except JuniperCommitError as e:
        print("Couln't replace config on {} (JuniperCommitError): {}".format(dev, e))
    except JuniperRpcTimeoutError as e:
        print("Couldn't replace config on {} (JuniperRpcTimeoutErroras): {}".format(dev, e))
    except JuniperUnlockError as e:
        print("Couldn't replace config on {} (JuniperUnlockError): {}".format(dev, e))
    except ReplaceConfigException as e:
        print("Couldn't replace config on {} (ReplaceConfigException): {}".format(dev, e))


def set_dev_opts(args, opt):

    if 'username' not in opt:
        if not args['username']:
            print ('No username specified')
            return False
        else:   
            opt['username'] = args['username']

    if ('password' not in opt) or (not opt['password']):
        if args['password']:
            opt['password'] = args['password']
        else:
            print("No password specified")
            return False

    if 'optional_args' not in opt:
        opt['optional_args'] = None
    
    """
    Default timeout is 60 seconds,
    raise to 180 if nonde is set:
    """
    if 'timeout' not in  opt:
         opt['timeout'] = 180

    return True


def main():
    
    args = parse_cli_args()
    if not args['password']:
        args['password'] = getpass("Default password:")

    inventory = build_inventory(args)
    if not inventory:
        sys.exit(1)

    if not check_config_files_exist(args, inventory):
        sys.exit(1)

    if not check_log_path_exists(args['log_dir']):
        sys.exit(1)


    if args['dry_run']:
        print("Dry run enabled!")


    ret_val = True
    for dev, opt in inventory.items():

        print("")
        print("Trying {}...".format(dev))


        if args['target']:
            config_file = args['configs']
        elif args['host']:
            config_file = args['configs']+'/'+dev+'.txt'
        elif args['replace']:
            config_file = args['configs']+'replace_config_'+opt['os']+'.txt'
        else:
            config_file = args['configs']+'merge_config_'+opt['os']+'.txt'


        timestamp = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
        output_file = args['log_dir']+'/'+dev+'_'+timestamp+'.txt'

        try:
            output_log = open(output_file, "w")
        except Exception as e:
            print("Couldn't open output log file {}: {}".format(output_file, e))
            ret_val = False
            continue


        if ( (args['note'] != None) and (opt['os'] != 'junos') ):
            # Commit message is only supported on Junos
            args['note'] = None


        # Record if this is a junos device to allow the user of "commit check"
        if opt['os'] == 'junos':
            junos = True
        else:
            junos = False


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
            print("Couldn't authenticate to {} as {}".
                  format(opt['hostname'], opt['username']))
            ret_val = False
            continue
        except (ConnectionException, JuniperConnectRefusedError, 
                JuniperConnectUnknownHostError, SocketError,
                SocketTimeout, SSHException):
            print("Couldn't connect to: {} using {} on port {}".
                  format(opt['hostname'], transport, port))
            ret_val = False
            continue
        except LockError:
            print("Couldn't lock configuration for {}".format(dev))
            ret_val = False
            continue
        

        # Perform a full device configuration replace operation
        if args['replace']:
            
            if not load_replace(config_file, dev, device):
                ret_val = False
                continue

            diff = get_diff(dev, device)
            if not diff:
                print("No config changes for {}".format(dev))
            elif diff == False: # get_diff returned an error
                device.close()
                ret_val = False
                continue
            else:
                print("{} diff:\n{}".format(dev, diff))
                output_log.write('#'+dev+'\n')
                output_log.write(diff+'\n\n')

            if args['verify'] and junos:
                commit_check(dev, device)

            if not args['dry_run']:
                print("Replacing config...")
                replace_config(dev, device, args['note'])


        # Perform a merge config operation
        else:

            if not load_merge(config_file, dev, device):
                ret_val = False
                continue

            diff = get_diff(dev, device)
            if not diff:
                print("No config changes for {}".format(dev))
            elif diff == False: # get_diff returned an error
                device.close()
                ret_val = False
                continue
            else:
                print("{} diff:\n{}".format(dev, diff))
                output_log.write('#'+dev+'\n')
                output_log.write(diff+'\n\n')

            if args['verify'] and junos:
                commit_check(dev, device)

            if not args['dry_run']:
                print("Merging config...")
                merge_config(dev, device, args['note'])


        device.discard_config()
        output_log.close()

        try:
            device.close()
        except UnlockError:
            print("Unable to unlock config for {}".format(dev))

        print("{} done".format(dev))


    if ret_val:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
