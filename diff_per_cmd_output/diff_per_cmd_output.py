#!/usr/bin/python3

'''
Loop over two sets of command outputs and diff the outputs.
Optionally use a diff filter.
'''


import argparse
import os
import re
import shlex
import subprocess
import sys
import yaml


def check_diff_path_exists(diff_dir):

    if not os.path.isdir(diff_dir):
        print("Path to diff directory doesn't exist: {}".
               format(diff_dir))
        try:
            os.makedirs(diff_dir, exist_ok=True)
            print("Created directory: {}".format(diff_dir))
            return True
        except Exception as e:
            print("Couldn't create directory {}: {}".format(diff_dir, e))
            return False
    else:
        return True


def check_path_exists(directory):

    if not os.path.isdir(directory):
        print("Path to directory doesn't exist: {}".format(directory))
        return False
    else:
        return True


def compare_files(cmd_filter, diff_file, os, pre_filename, post_filename):

    # Get the command that was executed from the output log
    cmd = get_cmd(pre_filename)
    if not cmd:
        return

    """
    Now that we have the original command that was run, if a command filter
    has been defined pass the command's output through the filter before
    the diff is made:
    """
    if cmd_filter:
        pre_filename, post_filename = filter_output(cmd_filter, cmd,
                                                    pre_filename,
                                                    post_filename)

    else:
        """
        If there is no diff filter defined, escape the filename, this would be
        done in the filter_output() function
        """
        pre_filename = shlex.quote(pre_filename)
        post_filename = shlex.quote(post_filename)


    if (not pre_filename) or (not post_filename):
        return

    command = "diff -y --suppress-common-lines "+pre_filename+" "+post_filename
    command += " | wc -l | tr -d '\\n'"

    try:        
        result = subprocess.getstatusoutput(command)
        if result[0] != 0:
            print("Couldn't check diff line count: {}\n{}".
                  format(command, result[1]))
            return
        diff_count = int(result[1])

    except Exception as e:
        print("Unable to check number of diff lines for command {}: {}"
              .format(cmd, e))
        return

    if diff_count == 0:
        return

    """
    If the number of changed lines is exactly 1, check that it isn't just
    the timestamp from the CLI. Try to match the IOS CLI timestamp and Junos
    timestamp patterns in the output.
    """
    if os == 'ios':
        """
        IOS Examples:
        No time source, *11:47:36.151 UTC Wed Nov 7 2018
        Time source is NTP, 13:57:04.417 UTC Wed Nov 7 2018
        Time source is hardware calendar, *16:40:11.691 UTC Fri Nov 23 2018
        """
        timestamp = "ime source.*([0-9][0-9]:){2}[0-9][0-9]\.[0-9][0-9][0-9] "
        timestamp += "[A-Z][A-Z][A-Z] [A-Z][a-z][a-z] [A-Z][a-z][a-z] "
        timestamp += "[0-9]{1,2} [0-9]{4}"
    elif os == 'junos':
        """
        Junos Examples:
        Oct 25 18:15:40
        Nov 07 14:01:37
        """
        timestamp = "^[A-Z][a-z][a-z] [0-9][0-9] ([0-9][0-9]:){2}[0-9][0-9]"
    else:
        timestamp = False

    if (diff_count == 1) and (timestamp): 

        command = "diff -y --suppress-common-lines "+pre_filename+" "
        command += post_filename+" | grep -E '"+timestamp+"' -c"

        result = subprocess.getstatusoutput(command)
        # ^ grep will return the count of lines that match the timestamp regex

        if (int(result[0]) == 0) and (int(result[1]) == 1):
            """
            grep matched exactly one occurance of the timestamp regex.
            If only one line changed and it matched the timestamp regex
            no command output has changed.
            """
            return

    """
    Otherwise, more than one line changed or the only line that changed
    wasn't a CLI timestamp, create a diff:
    """
    command = "diff -c "+pre_filename+" "+post_filename+" >> "+diff_file
    result = subprocess.getstatusoutput(command)
    """
    diff exit code is 1 when there is a difference between the two files,
    it is 0 when there is no difference, 2 if there is a problem.
    """
    if result[0] != 1:
        print("Couldn't create diff: {}\n{}".format(command, result[1]))
        return

    return


def filter_output(cmd_filter, cmd, pre_filename, post_filename):

    if cmd in list(cmd_filter['head_cmds'].keys()):

        count = str(cmd_filter['head_cmds'][cmd])

        command = "head -n "+count+" "+shlex.quote(pre_filename)
        command += " > "+shlex.quote(pre_filename+".tmp")

        result = subprocess.getstatusoutput(command)
        if result[0] != 0:
            print("Couldn't `head` pre-change file: {}\n{}".
                  format(command, result[1]))
            return False, False


        command = "head -n "+count+" "+shlex.quote(post_filename)
        command += " > "+shlex.quote(post_filename+".tmp")

        result = subprocess.getstatusoutput(command)
        if result[0] != 0:
            print("Couldn't `head` post-change file: {}\n{}".
                  format(command, result[1]))
            return False, False

        pre_filename = shlex.quote(pre_filename+".tmp")
        post_filename = shlex.quote(post_filename+".tmp")

        return (pre_filename, post_filename)


    elif cmd in cmd_filter['exclude_cmds']:

        return False, False

    else:

        pre_filename = shlex.quote(pre_filename)
        post_filename = shlex.quote(post_filename)

        return (pre_filename, post_filename)


def get_cmd(pre_filename):

    try:
        pre_file = open(pre_filename, 'r')
    except Exception:
        print("Couldn't open pre-change file {}".format(pre_filename))
        return

    try:
        first_line = pre_file.readline()
    except Exception:
        print("Couldn't read first line of pre-change file {}".
              format(pre_filename))
        return

    pre_file.close()

    """
    The first line in the text file is the original command that was run,
    prefixed with a hash "#" character
    """
    cmd = first_line.translate({ord("#"): None, ord("\n"): None})

    return cmd


def load_filter(filename):

    try:
        filter_file = open(filename)
    except Exception as e:
        print("Couldn't open filter file {}: {}".format(filename, e))
        sys.exit(1)

    try:
        cmd_filter = yaml.load(filter_file)
    except Exception as e:
        print("Couldn't load YAML file {}: {}".format(filename, e))
        sys.exit(1)

    filter_file.close()

    return cmd_filter


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Loop over two sets of command outputs and diff the '
                    'outputs. Optionally, use a passed filter file to filter '
                    'the command output.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-d', '--diff',
        help='Output diff filename.',
        type=str,
        default='diff.txt',
    )
    parser.add_argument(
        '-f', '--filter-file',
        help='Filter file for filtering command output',
        type=str,
        default='./diff_filter.yml',
    )
    parser.add_argument(
        '-o', '--os',
        help='The device OS that produced the logs being compared. '
             'This is the NAPALM device type e.g. ios or junos etc.',
        type=str,
        required=True,
        default=None,
    )
    parser.add_argument(
        '-post',
        help='Directory which contains post-change command output files.',
        type=str,
        default='./post/',
    )
    parser.add_argument(
        '-pre',
        help='Directory which contains pre-change command output files.',
        type=str,
        default='./pre/',
    )

    return vars(parser.parse_args())


def main():

    args = parse_cli_args()

    if not args['os']:
        print("Device OS is required with -o option!")
        sys.exit(1)

    if args['filter_file']:
        cmd_filter = load_filter(args['filter_file'])
    else:
        cmd_filter = None

    if not check_path_exists(args['pre']):
        sys.exit(1)

    if not check_path_exists(args['post']):
        sys.exit(1)

    if not check_diff_path_exists(os.path.dirname(args['diff'])):
        sys.exit(1)

    diff_file = args['diff']
    if os.path.isfile(diff_file):
        print("{} already exists, will be appended to!".
              format(diff_file))
    
    print("Comparing {} to {}...".format(args['pre'], args['post']))

    for file in os.listdir(args['pre']):

        pre_file = args['pre']+"/"+file
        post_file = args['post']+"/"+file

        # Don't try to compare any other files in the same directory
        if file.lower().endswith(".txt"):
            if os.path.isfile(post_file):

                compare_files(cmd_filter, diff_file, args['os'], pre_file,
                              post_file)
            else:
                print("Can't find matching post-change file for pre-change"
                      " file: {}".format(post_file))
                continue

    print("done")


if __name__ == '__main__':
    sys.exit(main())
