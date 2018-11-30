## Overview

These scripts can be used to run commands on a device and save the output.  

* [diff_per_cmd_output.py](#diff_per_cmd_outputpy)


### [diff_per_cmd_output.py](diff_per_cmd_output.py)
This script processes output from the [run_and_log_per_cmd.py](/run_and_log_per_cmd) script.  
It will check if each file in the `-pre` path exists in the `-post` path. If a  
file exists in both paths it will be `diff`'ed and the diff output is saved.  
A single diff file is built per device with which contains the diff output  
from each command that was run against the device using the  
[run_and_log_per_cmd.py](run_and_log_per_cmd.py) script.  

An optional filer can be used to either skip commands or only diff the first  
N lines of a command's output. For an example of what this should look like  
see the [diff_filter.yml](diff_filter.yml) file. It is in YAML format.  
To disable the diff filter add the option `-f ''`.  

To use the diff filter to only diff the first N lines of command output, add a  
key/value pair under `head_cmds`. The key is the command you want to filter  
and the value is the number of lines to include in the diff from the start of  
the output. To exclude the output of a command from the diff output simply  
add the command as a list item under `exclude_cmds`.

The type of device output being `diff`'ed must be specified, which is a  
NAPALM type, e.g. 'ios' or 'junos' using the `-o` option.  

Example output is shown below:
```bash
# Assume run_and_log_per_cmd.py has been run twice already, e.g. before and after a change:
bensley@LT-10383(run_and_log_per_cmd)$./run_and_log_per_cmd.py -l logs/before/
bensley@LT-10383(run_and_log_per_cmd)$./run_and_log_per_cmd.py -l logs/after/

bensley@LT-10383(diff_per_cmd_output)$./diff_per_cmd_output.py -pre logs/before/R2-Junos/ -post logs/after/R2-Junos/ -d logs/diff/R2.diff -o junos
Path to diff directory doesn't exist: logs/diff
Created directory: logs/diff
Comparing logs/before/R2-Junos/ to logs/after/R2-Junos/...
done

bensley@LT-10383(diff_per_cmd_output)$./diff_per_cmd_output.py -pre logs/before/R3-IOSXE/ -post logs/after/R3-IOSXE/ -d logs/diff/R3.diff -o ios
Comparing logs/before/R3-IOSXE/ to logs/after/R3-IOSXE/...
done
```

```bash
bensley@LT-10383(diff_per_cmd_output)$head -n 14 logs/diff/R3.diff
*** "logs/before/R3-IOSXE/show bgp ipv4 unicast summary  begin Neighbor.txt"    2018-11-07 11:47:33.378515200 +0000
--- "logs/after/R3-IOSXE/show bgp ipv4 unicast summary  begin Neighbor.txt"     2018-11-07 11:55:38.407425600 +0000
***************
*** 1,5 ****
  #show bgp ipv4 unicast summary | begin Neighbor
  Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
  10.0.0.1        4            1       0       0        1    0    0 never    Idle
! 10.0.0.2        4            1      60      59        1    0    0 00:26:01        0

--- 1,5 ----
  #show bgp ipv4 unicast summary | begin Neighbor
  Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
  10.0.0.1        4            1       0       0        1    0    0 never    Idle
! 10.0.0.2        4            1      79      76        1    0    0 00:34:06        0
```