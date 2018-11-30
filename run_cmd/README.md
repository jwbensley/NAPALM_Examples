## Overview

This script can be used to run the same command on multiple devices. 

* [run_cmd.py](#run_cmdpy)


#### [run_cmd.py](run_cmd.py)
This script runs a single CLI command against a list of devices stored  
in an inventory file. The command is provided as a option to the script and  
each host in the inventory file must be the same type (otherwise the command  
will fail or the inventory file contains multiple device types it must be  
filtered to a single type using the `-o` flag).  

This script will by default loop over all the devices in the parsed inventory  
file and run the command against all that it can connect and authenticate  
against. If won't stop if it fails to connect or authenticate to any device.  

If the inventory file contains devices of many types one can limit the 
script to only run against devices of a specific type/os using the `-o` option 
e.g. `-o ios` to only run commands against IOS/IOS-XE devices or `-o junos`.  
These are NAPALM device types e.g. ios/junos/eos/iosxr/nxos etc.

Any devices with an unsupported NAPALM OS type will be skipped.

Below is example output from the script. The inventory file contained three  
hosts, two IOS devices and one Junos device. It was filtered for each run  
using `-o`:  

```bash
bensley@LT-10383(run_cmd)$./run_cmd.py -c "show clock" -o ios
Default password:
Loading inventory ./inventory.yml
Loaded 2 device(s) in inventory
Trying R3-IOSXE...
R3-IOSXE: *09:59:35.652 UTC Fri Nov 30 2018
R3-IOSXE done
Trying R1-IOS...
R1-IOS: *09:59:44.139 UTC Fri Nov 30 2018
R1-IOS done

bensley@LT-10383(run_cmd)$./run_cmd.py -c "show system uptime" -o junos
Default password:
Loading inventory ./inventory.yml
Loaded 1 device(s) in inventory
Trying R2-Junos...
R2-Junos:
Current time: 2018-11-30 09:50:09 UTC
System booted: 2018-11-29 17:15:19 UTC (16:34:50 ago)
Protocols started: 2018-11-29 17:15:53 UTC (16:34:16 ago)
Last configured: 2018-11-30 08:55:42 UTC (00:54:27 ago) by napalm
 9:50AM  up 16:35, 1 user, load averages: 0.08, 1.71, 1.53

R2-Junos done
```