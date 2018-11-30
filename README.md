
## Overview
This repo contains scripts that use the NAPALM library to interact with network  
devices for running commands, pushing config, gathering stats etc. They are  
example of how to use NAPALM to automate basic network operations.  
The [network_change/network_change.py](network_change) script is a culmination  
of these scripts which ties them together to automate config automation.  

### Contents
* [Install](#install)
* [Inventory File](#inventory-file)
* [Scripts](#scripts)
  * [apply_config/apply_config.py](apply_config)
  * [diff_per_cmd_output/diff_per_cmd_output.py](diff_per_cmd_output/)
  * [napalm_getters/get_version.py](napalm_getters/)
  * [napalm_getters/napalm_getters.py](napalm_getters/)
  * [network_change/network_change.py](network_change/)
  * [rollback/rollback.py](rollback/)
  * [run_and_log_per_cmd/run_and_log_per_cmd.py](run_and_log_per_cmd)
  * [run_and_log_per_cmd/diff_per_cmd_output.py](run_and_log_per_cmd)
  * [run_and_log_per_device/run_and_log_per_device.py](run_and_log_per_device/)
  * [run_cmd/run_cmd.py](run_cmd/)
  * [run_commands_ntc/run_commands_ntc.py](run_commands_ntc/)
  * [syntax_check/syntax_check.py](syntax_check/)


### Install
The latest version of the NAPALM library should be installed to use these scritps:
```bash
$ sudo -H pip3 install napalm
```

### Inventory File
Most of these scripts expect an inventory file to be specified so that an  
action may be performed against a series of devices. This should be a  
standard YAML file with the various fields used by NAPALM defined.  

Mandatory fields in the inventory file are `hostname` and `os`.  

Examples of optional fields are as follows (see the NAPALM documentation for 
more info):
* `username` - per device username
* `password` - per device password (bad idea to have stored in a file!)
* `optional_args`- a dict of optional arguments for NAPALM
* `optional_args` -> `transport` - specify Telnet login instead of the default SSH
* `optional_args` -> `timeout` - specify login and command timeout (default is 60 seconds)
* `optional_args` -> `config_lock` - lock the configuration database whilst making changes (Junos only)

These scripts will always prompt for a password when run so that there is no  
need to save the password in the inventory file (storing the password is for  
testing only).  

The following is an example inventory file:
```yml
R1: # Example IOS devices which uses Telnet
  hostname: 192.168.223.11
  os: ios
  username: napalm
  password: napalm
  optional_args:
    transport: telnet

R2: # Example Junos device
  hostname: 192.168.223.12
  os: junos
  optional_args:
    config_lock: True
 
R3: # Example IOS-XE device
  hostname: 192.168.223.13
  os: ios
  optional_args:
    verbose: True

ALD01: # Example KeyMile device - this would be ignored based on 'os'
  hostname: 172.16.7.132
  os: km
```
All settings can also be set via the CLI, see `-h` for more info.  
Settings in the inventory, if defined, take precedence over any CLI args.
