## Overview

#### [run_commands_ntc.py](run_commands_ntc.py)
This script is the same as the [run_and_log_per_device.py](run_and_log_per_device.py) script except  
that the output is parsed through an NTC template if one exists, to create  
structured output from the CLI.  

NTC templates use different a naming convention to NAPALM for device types so  
NAPALM types are mapped to NTC types in the get_ntc_type() function. 

Before this script can be used the NTC templates must be downloaded and an  
environment variable set that points to their full path:
```bash
$ git clone https://github.com/networktocode/ntc-templates.git
$ export NET_TEXTFSM=`pwd`/ntc-templates
```

```bash
bensley@LT-10383(run_commands_ntc)$./run_commands_ntc.py
Default password:
Trying R2-Junos...
R2-Junos done
Trying ALD01...
ALD01 has an unsupported device OS type: km
Trying R1-IOS...
Coudn't execute CLI commands: Unable to execute command "show processes cpu platform sorted"
Coudn't execute CLI commands: Unable to execute command "show processes memory platform sorted"
Coudn't execute CLI commands: Unable to execute command "show platform resources"
Coudn't execute CLI commands: Unable to execute command "show bridge-domain"
R1-IOS done
Trying R3-IOSXE...
SSH connection established to 192.168.223.13:22
Interactive SSH session established
Coudn't execute CLI commands: Unable to execute command "show environment"
R3-IOSXE done
```

```bash
bensley@LT-10383(run_commands_ntc)$grep -A 12 "show ip ospf nei" logs/R1-IOS_2018-10-23--12-37-52.yml
show ip ospf neighbor:
- address: 10.0.13.3
  dead_time: 00:00:39
  interface: FastEthernet0/1
  neighbor_id: 10.0.0.3
  priority: '0'
  state: FULL/  -
- address: 10.0.12.2
  dead_time: 00:00:31
  interface: FastEthernet0/0
  neighbor_id: 10.0.0.2
  priority: '0'
  state: FULL/  -
```
