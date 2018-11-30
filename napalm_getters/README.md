## Overview

These scripts provide examples of how to use the built in NAPALM getters.

* [get_version.py](#get_versionpy)
* [napalm_getters.py](napalm_getterspy)


#### [get_version.py](get_version.py)

This script is an example script that shows how to use the built-in NAPALM 
getters, in this case using `get_facts()`, to loop over an inventory of 
devices and print their firmware version. 

Example output:
```bash
bensley@LT-10383(napalm_getters)$./get_version.py -u jbensley
Default password:
172.16.0.179: 15.1R5-S2.3
10.105.6.0: ASR900  Software (PPC_LINUX_IOSD-UNIVERSALK9_NPE-M), Version 15.6(2)SP3, RELEASE SOFTWARE (fc4)
10.105.6.2: ASR920 Software (PPC_LINUX_IOSD-UNIVERSALK9_NPE-M), Version 15.6(2)SP3, RELEASE SOFTWARE (fc4)
```


#### [napalm_getters.py](napalm_getters.py)
This script is a simple example showing how to use all the various built in  
"getters" within NAPALM. This allows one to gather data from network devices 
in a structured format.

Example output:
```bash
bensley@LT-10383(napalm_getters)$./napalm_getters.py -u jbensley
Default password:
Trying mx960...
mx960 done
Trying fan0.chu01...
fan0.chu01 done
Trying agn0.upo01...
agn0.upo01 done
```

```bash
bensley@LT-10383(napalm_getters)$head -n 21 logs/fan0.chu01_2018-11-07--11-36-05.yml
get_bgp_neighbors:
  global:
    peers:
      10.105.0.0:
        address_family:
          ipv4:
            accepted_prefixes: 11
            received_prefixes: 11
            sent_prefixes: 2
        description: ''
        is_enabled: true
        is_up: true
        local_as: 12345
        remote_as: 12345
        remote_id: 10.105.0.0
        uptime: 8035200
    router_id: 10.105.0.2
get_environment:
  cpu:
    0:
      '%usage': 5.0
```
