## Overview

These scripts can be used to run commands on a device and save the output.  

* [run_and_log_per_cmd.py](#run_and_log_per_cmdpy)


#### [run_and_log_per_cmd.py](run_and_log_per_cmd.py)
This script runs commands stored in a text file against a list of devices  
stored in an inventory file. The commands are stored in a file the name of 
which contains the device type. The format of the filename is `cmd_`+os+`.txt`.

E.g. `cmd_ios.txt` for Cisco IOS/IOS-XE or `cmd_junos.txt` for Juniper Junos.  

This script will by default loop over all the devices in the parsed inventory  
file and if the device is an IOS devices for example, run all the commands in  
the `cmd_ios.txt` file against that devices, or if it is a Junos device, run  
all the commands in `cmd_junos.txt`. The output is stored in the specified  
log directory in a file with the name of the device as specified in the  
inventory file. If the inventory file contains devices of many types one can  
limit the script to only run against devices of a specific type/os using the  
`-o` option e.g. `-o ios` to only run commands against IOS/IOS-XE devices.  

Any devices with an unsupported NAPALM OS or for which there is no `cmd_`  
text file will be skipped.  

Below is example output from the script. R2 is a Junos device and R3 is an  
IOS-XE device. Verbose output has been enabled on R3. Some unsupported  
commands are run on R3 (because it is a virtual router) to show what happens.  
R1 is an IOS device which is unreachable to again show what happens.  
A KeyMile device (ALD01) is present in the inventory to again show what  
happens in that case:

```bash
bensley@LT-10383(run_and_log_per_cmd)$./run_and_log_per_cmd.py
Default password:
Path to output logging directory doesn't exist: ./logs
Created directory: ./logs
Trying R1-IOS...
Unable to connect to: 192.168.223.11 using telnet on port 23
Trying R3-IOSXE...
SSH connection established to 192.168.223.13:22
Interactive SSH session established
Path to output logging directory doesn't exist: ./logs/R3-IOSXE
Created directory: ./logs/R3-IOSXE
Couldn't run a command on R3-IOSXE: Unable to execute command "show platform hardware pp active resource-usage summary 0"
Couldn't run a command on R3-IOSXE: Unable to execute command "show platform hardware pp active tcam usage"
Couldn't run a command on R3-IOSXE: Unable to execute command "show environment"
Couldn't run a command on R3-IOSXE: Unable to execute command "show environment | exclude mV"
R3-IOSXE done
Trying R2-Junos...
Path to output logging directory doesn't exist: ./logs/R2-Junos
Created directory: ./logs/R2-Junos
R2-Junos done
Trying ALD01...
ALD01 has an unsupported device OS type: km
```

```bash
bensley@LT-10383(run_and_log_per_cmd)$ls logs/R2-Junos/
file list detail vartmp  no-more.txt                     show mpls interface  no-more.txt
set cli timestamp.txt                                    show ospf interface  no-more.txt
show bfd session  no-more.txt                            show ospf neighbor  no-more.txt
show bfd session summary  no-more.txt                    show route forwarding-table summary family inet6  no-more.txt
show bgp summary  no-more.txt                            show route forwarding-table summary family inet  no-more.txt
show chassis alarms  no-more.txt                         show route forwarding-table summary  no-more.txt
show chassis environment  no-more.txt                    show route summary  no-more.txt
show chassis fpc  no-more.txt                            show rsvp interface  no-more.txt
show chassis hardware detail  no-more.txt                show rsvp neighbor  no-more.txt
show chassis routing-engine  no-more.txt                 show system alarms  no-more.txt
show configuration  display set  no-more.txt             show system boot-messages  no-more.txt
show configuration  no-more.txt                          show system commit  no-more.txt
show interfaces descriptions  no-more.txt                show system memory  no-more.txt
show interfaces terse routing-instance all  no-more.txt  show system processes brief  no-more.txt
show isis adjacency  no-more.txt                         show system processes extensive  no-more.txt
show isis interface  no more.txt                         show system resource-monitor summary.txt
show ldp interface  no more.txt                          show system storage  no-more.txt
show ldp session  no-more.txt                            show system virtual-memory  no-more.txt
show log messages  last 200  no-more.txt                 show version  no-more.txt
```
