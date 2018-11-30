## Overview

This script can be used to perform a mass rollback against many devices.

* [rollback.py](#rollbackpy)


#### [rollback.py](rollback.py)
This script will read a YAML inventory file to rollback multiple hosts or a  
single host can be specified using the `-t` option. The script will perform  
a rollback against each host in the inventory based on OS type.  
Currently only IOS and Junos are supported as an example, but others can be  
easily added.  

For Junos devices it effectively performs `rollback 1` and `commit`. For IOS  
device it tries to restore the config stored on the device in the file  
`flash:rollback_config.txt`. When config is pushed using the NAPALM IOS  
driver it by default creates an on device back of the running config stored  
at `flash:rollback_config.txt`.

Below is example output from the script. The inventory file contained three  
hosts, two IOS devices and one Junos device. R1 (an IOS device) has no local  
backup because the storage is broken `¯\_(ツ)_/¯`:  
```bash
bensley@LT-10383(rollback)$./rollback.py
Default password:
Loading inventory ./inventory.yml
Loaded 3 device(s) in inventory
Trying R2-Junos...
R2-Junos rolled back
R2-Junos done
Trying R1-IOS...
R1-IOS rollback failed: Error: Could not open file flash:rollback_config.txt for reading
R1-IOS done
Trying R3-IOSXE...
R3-IOSXE Total number of passes: 1
Rollback Done
R3-IOSXE done
```