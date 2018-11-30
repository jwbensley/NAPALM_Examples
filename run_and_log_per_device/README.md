## Overview

#### [run_and_log_per_device.py](run_and_log_per_device.py)
This script runs commands stored in a text file against a list of devices  
stored in an inventory file. The commands are stored in a file the name of 
which contains the device type. The format of the filename is `cmd_` +  os + `.txt`.
E.g. `cmd_ios.txt` for Cisco IOS/IOS-XE or `cmd_junos.txt` for Juniper Junos.

This script will by default loop over all the devices in the passed inventory 
file and if the device is an IOS devices for example, run all the commands in 
the `cmd_ios.txt` file against that devices, or if it is a Junos device, run 
all the commands in `cmd_junos.txt` and store the output in the specified log 
directory in a file with the name of the device as specified in the inventory 
file. If the inventory file contains devices of many types one can limit the 
script to only run against devices of a specific type/os using the `-o` option 
e.g. `-o ios` to only run commands against IOS/IOS-XE devices.

Any devices with an unsupported NAPALM OS or for which there is no `cmd_`  
text file will be skipped.  

Below is example output from the script. R2 is a Junos device and R3 is an IOS-XE device. Verbose output has been enabled on R3. An unsupported command is run on R3 to show what happens. R1 is an IOS device which is unreachable to again show what happens. A KeyMile device (ALD01) is present in the inventory to again show that unsupported devices are skipped:
```bash
bensley@LT-10383(run_and_log_per_device)$./run_and_log_per_device.py
Default password:
Trying R2-Junos...
R2-Junos done
Trying R3-IOSXE...
SSH connection established to 192.168.223.13:22
Interactive SSH session established
Couldn't run a command on R3-IOSXE: Unable to execute command "show environment"
R3-IOSXE done
Trying R1-IOS...
Unable to connect to: 192.168.223.11 using telnet on port 23
Trying ALD01...
ALD01 has an unsupported device OS type: km
```
```bash
bensley@LT-10383(run_and_log_per_device)$head -n 20 logs/R2-Junos_2018-10-23--10-57-30.txt
#set cli timestamp


Oct 23 10:56:53
CLI timestamp set to: %b %d %T


#show chassis alarms | no-more

No alarms currently active


#show chassis environment | no-more


#show log messages | last 200 | no-more

Jun 18 10:59:49   eventd[1967]: SYSTEM_ABNORMAL_SHUTDOWN: System abnormally shut down
Jun 18 10:59:49   eventd[1967]: SYSTEM_OPERATIONAL: System is operational
Jun 18 10:59:49   /kernel: Copyright (c) 1996-2014, Juniper Networks, Inc.
```
