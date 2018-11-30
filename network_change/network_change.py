#!/usr/bin/python3

"""
* Syntax check the config to be applied to each device
* Check if any devices have active alarms on SolarWinds
* Checkout the network changes git repo
* Record the pre-change state of each device
* Apply the config to each device
* Record the post-change state of each device
* Generate a diff of the pre and post device state
* Check if any devices have a different alarm severity on SolarWinds from before the change
* Commit and push everything to the git repo
"""

import argparse
from getpass import getpass
import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import shlex
import subprocess
from napalm._SUPPORTED_DRIVERS import SUPPORTED_DRIVERS
import sys
import yaml


def apply_config(args, log_dir, inventory, scripts):

    passed = True

    for dev, opt in inventory.items():

        if args['target']:
            config_file = args['configs']
        elif args['host']:
            config_file = args['configs']+'/'+dev+'.txt'
        elif args['replace']:
            config_file = args['configs']+'replace_config_'+opt['os']+'.txt'
        else:
            config_file = args['configs']+'merge_config_'+opt['os']+'.txt'

        command = shlex.quote(scripts['apply'])
        command += " -c "+shlex.quote(config_file)
        
        if args['dry_run']:    
            command += " -d"

        command += " -t "+opt['hostname']

        command += " -l "+log_dir

        # Commit message is only supported on Junos
        if (args['note']) and (opt['os'] == 'junos'):
            command += " -n \""+args['note']+"\""

        elif opt['os'] == 'junos':
            command += " -n \""+args['ref']+"\""
        
        command += " -p "+opt['password']

        if args['replace']:
            command += " -r"

        command += " -o "+opt['os']

        command += " -u "+opt['username']

        # "commit check" only supported on Junos
        if opt['os'] == 'junos' and args['verify']:
            command += " -v"

        cmd = shlex.split(command)

        try:
            subprocess.run(cmd, check=True, timeout=300)
        except Exception as e:
            print("Error applying device config: {}".format(e))
            passed = False


    if not passed:
        asking = True
        while(asking):
            answer = input("Config changes have encountered errors, "
                           "do you want to continue? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False
    else:
        print("Config applied to all devices without issue.")
        return True


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


def check_change_files_exist(args, inventory):

    # Check that the diff filter exists
    if not os.path.isfile(args['filter']):
        print("Change diff filter is missing: {}".format(args['filter']))
        return False

    """
    If running in target mode the -checks option points to a single checks
    command file rather than a directory
    """
    if args['target']:
        if not os.path.isfile(args['checks']):
            print("Checks file doesn't exist: {}".format(args['checks']))
            return False
        else:
            return True


    # If using an inventory, check if the checks directory exists
    if not os.path.isdir(args['checks']):
      print("Checks directory doesn't exis: {}".format(args['checks']))
      return False

    # Check the per-os change pre/post check command files exist.
    # First built a list of OS types in the inventory:
    os_types = []
    for dev, opt in inventory.items():
      if opt['os'] not in os_types:
        os_types.append(opt['os'])

    # Then check there is a per OS check commands file
    for os_type in os_types:
        for file in os.listdir(args['checks']):

            filename = "checks_"+os_type+".txt"
            if (file.lower().endswith(".txt")) and (file.lower() == filename):
                break

        else:
            print("Missing checks file {} for {} devices".
                  format(os_type, filename))
            return False

    return True


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


def check_config_syntax(args, inventory, scripts):

    # Check the syntax of the config that will be applied to each device.
    passed = True

    # List of unique OS types in the inventory file
    os_types = []
    for dev, opt in inventory.items():
      if opt['os'] not in os_types:
        os_types.append(opt['os'])

    # Check the per-OS/type config file syntax or, if running in per-host mode,
    # check the per-host config file syntax
    for dev, opt in inventory.items():

        # Check single host/target config file
        if args['target']:
            config_file = args['configs']

        # Check the per host config file
        elif args['host']:
            config_file = args['configs']+'/'+dev+'.txt'

        # Or check if there is a matching replace config for this device os
        elif args['replace']:
            config_file = args['configs']+'/replace_config_'+opt['os']+'.txt'

        # Else assume the default mode of merging a partial config and check
        # for a partial config for this device os
        else:
            config_file = args['configs']+'/merge_config_'+opt['os']+'.txt'


        command = shlex.quote(scripts['syntax'])
        command += " -c "+shlex.quote(config_file)
        command += " -t "+opt['os']

        try:
            result = subprocess.getstatusoutput(command)
            if result[0] != 0:
                print(result[1])
                passed = False
        except Exception as e:
            print("Unable to check syntax for config file {}: {}".format(command, e))
            passed = False

    if not passed:
        asking = True
        while(asking):        
            answer = input("The config syntax checks have failed, "
                           "do you want to continue? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False
    else:
        print("All config syntax checks have passed.")
        return True


def check_script_files_exist(scripts_dir, scripts):

    if not os.path.isdir(scripts_dir):
        print("Scripts directory doesn't exist: {}".format(scripts_dir))
        return False

    for script_path in scripts.values():

      if not os.path.isfile(script_path):
          print("Script is missing: {}".format(script_path))
          return False

    return True


def check_log_path_exists(log_dir):

    dirs = [ log_dir,
             log_dir+"/pre",
             log_dir+"/config",
             log_dir+"/post",
             log_dir+"/diff",
            ]

    for d in dirs:

        if not os.path.isdir(d):
            #print("Required directory doesn't exist: {}".
            #       format(d))
            try:
                os.makedirs(d, exist_ok=True)
                print("Created directory: {}".format(d))
            except Exception as e:
                print("Couldn't create directory: {}\n{}".format(d, e))
                return False

    return True


def checkout_change_repo(url):

    git_dir = git_directory(url)
    print("Cloning/pulling git change repo to {}...".format(git_dir))

    # N.B: To disable SSL verify use "git -c http.sslVerify=false clone ..."

    # If the git directory exists, try to `git pull` rather than `git clone`
    if os.path.isdir(git_dir+"/.git"):

        raw_cmd = "git pull origin master"
        cmd = shlex.split(raw_cmd)

        try:
            subprocess.run(cmd, check=True, timeout=180, cwd=git_dir)
        except Exception as e:
            print("Git pull error {}: {}".format(cmd, e))
            return False

    # If the git directory doesn't exists but the target directory does exist,
    # we have to get fetch to use an existing target directory:
    elif os.path.isdir(git_dir):

        raw_cmds = [
            "git init",
            "git remote add origin "+url,
            "git pull origin master",
            "git reset --hard HEAD",
            ]

        for raw_cmd in raw_cmds:

            cmd = shlex.split(raw_cmd)

            try:
                subprocess.run(cmd, check=True, timeout=180, cwd=git_dir)
            except Exception as e:
                print("Git fetch error {}: {}".format(cmd, e))
                return False

    # If the git directory doesn't exist nor the target directory, a simple git
    # clone should work fine
    else:

        raw_cmd = "git clone "+shlex.quote(url)+" "+git_dir
        cmd = shlex.split(raw_cmd)

        try:
            subprocess.run(cmd, check=True, timeout=180)
        except Exception as e:
            print("Git clone error {}: {}".format(cmd, e))
            return False

    return git_dir


def check_solarwinds(sw_api_url, inventory):

    print("Checking SolarWinds for active alarms on inventory devices...")

    """
    get_solarwinds_alarms will return False is no alarms were found,
    it will return True if it had an issue checking for active alarms,
    if it finds active alarms for devices being changed, it returns the
    list of devices with active alarms on them.
    """
    alarm_hosts = get_solarwinds_alarms(sw_api_url, inventory)

    if alarm_hosts == False:
        print("No active alarms on SolarWinds for change device(s)")
        return True

    elif alarm_hosts == True:
        #asking = True
        #while(asking):
        #    answer = input("SolarWinds alarm checks have failed, "
        #                   "do you want to continue? [yes/no]: ")
        #    if answer == "yes":
        #        return True
        #    elif answer == "no":
        #        return False
        print("Failed to check SolarWinds alarms!")
        return False
    
    else:
        print("Alarms are active on these hosts: {}\n".format(alarm_hosts))
        asking = True
        while(asking):
            answer = input("do you want to continue? [yes/no]: ")
            if answer == "yes":
                return alarm_hosts
            elif answer == "no":
                return False


def commit_change(url, ref):

    print("Commit git changes to repo...")

    git_dir = git_directory(url)

    if not os.path.isdir(git_dir+"/.git"):
        print("The git repo hasn't been checked out!")
        return False

    raw_cmd = "git add *"
    cmd = shlex.split(raw_cmd)

    try:
        subprocess.run(cmd, check=True, timeout=60, cwd=git_dir)
    except Exception as e:
        print("Git add error {}: {}".format(cmd, e))
        return False


    raw_cmd = "git commit -m "+shlex.quote("change: "+ref)
    cmd = shlex.split(raw_cmd)

    try:
        subprocess.run(cmd, check=True, timeout=60, cwd=git_dir)
    except Exception as e:
        print("Git commit error {}: {}".format(cmd, e))
        # Don't return on error, we may have already committed and need to push

    # N.B: To disable SSL verify use "git -c http.sslVerify=false clone ..."
    raw_cmd = "git push origin master"
    cmd = shlex.split(raw_cmd)

    try:
        subprocess.run(cmd, check=True, timeout=60, cwd=git_dir)
    except Exception as e:
        print("Git push error {}: {}".format(cmd, e))
        return False

    return True


def filter_inv(inventory, os_type):

    # Filter the inventory down to the specified type:
    filtered_inv = {}
    for dev, opt in inventory.items():
        if opt['os'] == os_type:
            filtered_inv[dev] = opt

    return filtered_inv


def get_solarwinds_alarms(sw_api_url, inventory):

    """
    The SW API call below will return a JSON blob which lists all devices with
    an active alarm (device severity is > 0) and we simply check if any of the
    devices being changed are in this list.
    """

    ret_val = False

    sw_user = input("SolarWinds username: ")
    sw_pass = getpass("SolarWinds password: ")

    """
    These are my guestimates from probing the SW API:
    Severity 0 means no alarms
    Severity 1 means an active alert but not an active alarm. This happens for
    example when an interface ifIndex that was being polled is now returning an
    error becuase the interface has been deleted.
    Seveirty 100 and higher is an active alarm.
    Severity 1000 means the device is completely down.
    """
    
    # Get a JSON dict of all devices in SW with active alarms
    api_query = sw_api_url
    api_query += "/Query?query=SELECT+SysName+,+IPAddress+,+Severity+FROM+"
    api_query += "Orion.Nodes+WHERE+Severity+>+1"

    try:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        sw_nodes = requests.get(
            url=api_query,
            auth=(sw_user, sw_pass),
            verify=False,
            headers={'content-type' : 'application/json'},
        )
    except Exception as e:
        print("Failed to query SolarWinds API: {}".format(e))
        return True

    if sw_nodes.status_code is not requests.codes.ok:
        print('API GET failed, result code was: {}'.format(sw_nodes.status_code))
        return True

    if sw_nodes is None:
        return True

    try:
        sw_nodes = sw_nodes.json()
    except Exception as e:
        print("Couldn't decode SolarWinds API JSON: {}".format(e))
        return True

    alarm_hosts = []

    for dev, opt in inventory.items():

        for node in sw_nodes['results']:
            if ( (node['IPAddress'] == opt['hostname']) or 
                 (node['SysName'] == opt['hostname']) ):
                alarm_hosts.append(dev)
                continue

    if len(alarm_hosts) > 0:
        return alarm_hosts
    else:
        return ret_val


def generate_state_diff(diff_dir, diff_filter, inventory, pre_dir, post_dir,
                         scripts):

    for dev, opt in inventory.items():

        command = shlex.quote(scripts['diff'])
        command += " -d "+shlex.quote(diff_dir+"/"+opt['hostname']+".diff")
        command += " -f "+shlex.quote(diff_filter)
        command += " -o "+opt['os']
        command += " -pre "+shlex.quote(pre_dir+"/"+opt['hostname'])
        command += " -post "+shlex.quote(post_dir+"/"+opt['hostname'])

        cmd = shlex.split(command)

        try:
            subprocess.run(cmd, check=True, timeout=60)
        except Exception as e:
            print("Error generating state diff: {}".format(e))


def git_directory(url):

    """
    Assume URL format is
    git@git.lab.net:james.bensley/network-changes.git
    or
    https://git.lab.net/james.bensley/network-changes.git
    """
    git_dir = "./"+url.split("/")[-1].split(".")[0]+"/" # "./network-changes/"
    return git_dir


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
        description='Apply config to devices, record the before '
                    'and after state of the device, create a diff of the '
                    'state change.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-checks',
        help='Directory of pre/post check command files. When making a '
             'change to a single device with the -t|--target option, this is '
             'file not a directory.',
        type=str,
        default='./checks/',
    )
    parser.add_argument(
        '-configs',
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
        '-filter',
        help='Location of the pre/post checks diff filter.',
        type=str,
        default='./checks/diff_filter.yml',
    )
    parser.add_argument(
        '-g', '--git-url',
        help='URL of the change repo. Set to blank to disable, e.g. '
             '-g \'\'',
        type=str,
        default='https://git.example.com/network-changes.git',
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
        default='inventory.yml',
    )
    parser.add_argument(
        '-j', '--jump',
        help='Jump to a specific point in this scripts process:\n'
             '-j 0, jump to git checkout only.'
             '-j 1, jump to pre-checks only. '
             '-j 2, jump to applying config only. '
             '-j 3, jump to post-checks only.'
             '-j 4, jump to git commit only.',
        type=str,
        default=None,
    )
    parser.add_argument(
        '-n', '--note',
        help='Override the commit note/comment. Not all devices support commit '
             'comments and this script uses the change reference by default.',
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
        '-r', '--replace',
        help='Replace the full device configuration.\n'
             'Merge is the default operation when this option isn\'t used.',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '-ref',
        help='Change reference number.',
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        '-rollback',
        help='Rollback the most recent change.',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '-scripts', '--scripts-dir',
        help='Path to the root of this NAPALM repo.',
        type=str,
        default=os.path.dirname(os.path.realpath(__file__))+"/../",
    )
    parser.add_argument(
        '-sw', '--solar-winds',
        help='Base URL of SolarWinds API. Set it to blank to disable '
             'SolarWinds checks, e.g. -sw \'\'',
        type=str,
        default='https://solarwinds.example.com:17778/SolarWinds/InformationService/v3/Json',
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


def prompt(index):

    asking = True

    if index == 1:
        while(asking):
            answer = input("Ready to record pre-change device state? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False

    elif index == 2:
        while(asking):
            answer = input("Ready to apply config to devices? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False

    elif index == 3:
        while(asking):
            answer = input("Ready to record post-change device state? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False

    elif index == 4:
        while(asking):
            answer = input("Ready to commit change to git? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False

    else:
        return False


def rollback(inventory, scripts):

    ret_val = True

    for dev, opt in inventory.items():

        command = shlex.quote(scripts['rollback'])
        command += " -o "+opt['os']
        command += " -p "+opt['password']
        command += " -t "+opt['hostname']
        command += " -u "+opt['username']

        cmd = shlex.split(command)

        try:
            subprocess.run(cmd, check=True, timeout=300)
        except Exception as e:
            print("Error running rollback on {}: {}".format(dev, e))
            ret_val = False

    if not ret_val:
        print("There were errors with the rollback!")

    return ret_val


def run_checks(args, log_dir, inventory, scripts):

    passed = True

    for dev, opt in inventory.items():

        command = shlex.quote(scripts['log_cmd'])
        command += " -o "+opt['os']
        command += " -l "+log_dir
        command += " -p "+opt['password']
        command += " -t "+opt['hostname']
        command += " -u "+opt['username']

        """
        If running in single host/target mode this argument points to a file
        else, if points to a directrory
        """
        if args['target']:
            command += " -c "+shlex.quote(args['checks'])
        else:
            command += " -c "+shlex.quote(args['checks']+"/checks_"+opt['os']+".txt")

        cmd = shlex.split(command)

        try:
            subprocess.run(cmd, check=True, timeout=300)
        except Exception as e:
            print("Error running device check commands: {}".format(e))
            passed = False

    print("")

    if not passed:
        asking = True
        while(asking):
            answer = input("Gathering device outputs failed, continue? [yes/no]: ")
            if answer == "yes":
                return True
            elif answer == "no":
                return False
    else:
        print("All state outputs have been gathered.")
        return True


def script_apply_config(args, log_dir, inventory, scripts):

    if not prompt(2):
        sys.exit(1)
    if not apply_config(args, log_dir+"/config/", inventory, scripts):
        sys.exit(1)  ### If no, ask for rollback!


def script_git_checkout(args):

    # Optionally check out the network changes repo
    if args['git_url']:
        if not checkout_change_repo(args['git_url']):
            sys.exit(1)


def script_git_commit(args):
    
    # Optionally commit logs back to network change repo
    if not prompt(4):
        sys.exit(1)
    if args['git_url']:
        if not commit_change(args['git_url'], args['ref']):
            sys.exit(1)


def script_pre_checks(args, log_dir, inventory, scripts):

    if not prompt(1):
        sys.exit(1)
    if not run_checks(args, log_dir+"/pre/", inventory, scripts):
        sys.exit(1)


def script_pre_reqs(args, inventory, scripts):

    if not inventory:
        sys.exit(1)

    if not check_change_files_exist(args, inventory):
        sys.exit(1)

    if not check_config_files_exist(args, inventory):
        sys.exit(1)

    if not check_script_files_exist(args['scripts_dir'], scripts):
        sys.exit(1)

    if not check_config_syntax(args, inventory, scripts):             
        sys.exit(1)


def script_post_checks(args, log_dir, inventory, scripts):

    if not prompt(3):
        sys.exit(1)
    if not run_checks(args, log_dir+"/post/", inventory, scripts):
        sys.exit(1)

    generate_state_diff(log_dir+"/diff", args['filter'], inventory,
                        log_dir+"/pre/", log_dir+"/post", scripts)
    

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

    return True


def main():
    
    args = parse_cli_args()
    args['password'] = getpass("Default password:")

    inventory = build_inventory(args)
    if not inventory:
        sys.exit(1)

    scripts = {
        "apply": args['scripts_dir']+"/apply_config/apply_config.py",
        "log_cmd": args['scripts_dir']+"/run_and_log_per_cmd/run_and_log_per_cmd.py",
        "diff": args['scripts_dir']+"/diff_per_cmd_output/diff_per_cmd_output.py",
        "syntax": args['scripts_dir']+"/syntax_check/syntax_check.py",
        "rollback": args['scripts_dir']+"rollback/rollback.py"
    }

    # Perform a rollback on each device
    if args['rollback']:
        print("\nPerforming rollback...")
        rollback(inventory, scripts)
        print("All done!")
        return


    script_pre_reqs(args, inventory, scripts)
    print("")

    # Create logging directory if it doesn't already exist
    if args['git_url']:
        log_dir = git_directory(args['git_url'])+"/"+args['ref']+"/"
    else:
        log_dir = "./"+args['ref']+"/"
    if not check_log_path_exists(log_dir):
        sys.exit(1)
    print("")


    """
    If the user is running a specific step in the change process, jump to
    that function only:
    """
    if args['jump']:
        
        # Checkout network change git repo
        if int(args['jump']) == 0:
            script_git_checkout(args)
            return

        # Record pre-change state only
        if int(args['jump']) == 1:
            script_pre_checks(args, log_dir, inventory, scripts)
            return

        # Apply config only
        elif int(args['jump']) == 2:
            script_apply_config(args, log_dir, inventory, scripts)
            return

        # Record post-change state only
        elif int(args['jump']) == 3:
            script_post_checks(args, log_dir, inventory, scripts)
            return

        # Commit and push to network change git repo only
        elif int(args['jump']) == 4:
            script_git_commit(args)
            return

        else:
            print("Invalid option: -j {}!".format(args['jump']))
            return

    # Else, run all steps...

    # Optionally check SolarWinds for active alarms
    if args['solar_winds']:
        alarm_hosts_pre = check_solarwinds(args['solar_winds'], inventory)
        print("")
        if not alarm_hosts_pre:
            sys.exit(1)

    # This function creates the dict entry args['git_dir']
    #script_git_checkout(args)
    #print("")
    #script_pre_checks(args, log_dir, inventory, scripts)
    #print("")
    #script_apply_config(args, log_dir, inventory, scripts)
    #print("")
    #script_post_checks(args, log_dir, inventory, scripts)
    #print("")

    # Optioanlly check if same/new alarms are active
    if args['solar_winds']:
        alarm_hosts_post = check_solarwinds(args['solar_winds'], inventory)
        print("")
        if not alarm_hosts_post:
            sys.exit(1)
        else:
            if alarm_hosts_pre != alarm_hosts_post:
                print("Pre/Post alarms are different:")
                print("pre: {}".format(alarm_hosts_pre))
                print("post: {}".format(alarm_hosts_post))

    script_git_commit(args)
    print("")


    print("All done!")


if __name__ == '__main__':
    sys.exit(main())
