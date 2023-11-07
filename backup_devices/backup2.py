# Imports
from netmiko import ConnectHandler
import csv
import logging
import datetime
import multiprocessing as mp
import difflib
import filecmp
import sys
import os

# Module 'Global' variables
DEVICE_FILE_PATH = 'devices.csv'  # CSV file containing device information, including device_type
BACKUP_DIR_PATH = '/home/user'  # Complete path to backup directory

def enable_logging():
    # This function enables netmiko logging for reference
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    logger = logging.getLogger("netmiko")

def get_devices_from_file(device_file):
    # This function takes a CSV file with inventory and creates a python list of dictionaries out of it
    # Each dictionary contains information about a single device, including device_type

    # Creating empty structures
    device_list = list()
    device = dict()

    # Reading a CSV file with ',' as a delimiter
    with open(device_file, 'r') as f:
        reader = csv.DictReader(f, delimiter=',')

        # Every device is represented by a single row, which is a dictionary object with keys equal to column names.
        for row in reader:
            device_list.append(row)

    print("Got the device list from inventory")
    print('-*-' * 10)
    print()

    # Returning a list of dictionaries
    return device_list

def get_current_date_and_time():
    # This function returns the current date and time
    now = datetime.datetime.now()

    print("Got a timestamp")
    print('-*-' * 10)
    print()

    # Returning a formatted date string
    # Format: yyyy_mm_dd-hh_mm_ss
    return now.strftime("%Y_%m_%d-%H_%M_%S")

def connect_to_device(device):
    # This function opens a connection to the device using Netmiko
    # Requires a device dictionary as an input

    # Since there is a 'hostname' key, this dictionary can't be used as is
    connection = ConnectHandler(
        host=device['ip'],
        username=device['username'],
        password=device['password'],
        device_type=device['device_type'],
        secret=device['secret']
    )

    print('Opened connection to ' + device['ip'])
    print('-*-' * 10)
    print()

    # Returns a "connection" object
    return connection

def disconnect_from_device(connection, hostname):
    # This function terminates the connection to the device
    connection.disconnect()
    print('Connection to device {} terminated'.format(hostname))

def get_backup_file_path(hostname, timestamp):
    # This function creates a backup file name (a string)
    # Backup file path structure is hostname/hostname-yyyy_mm_dd-hh_mm

    # Checking if the backup directory exists for the device, creating it if not present
    if not os.path.exists(os.path.join(BACKUP_DIR_PATH, hostname)):
        os.mkdir(os.path.join(BACKUP_DIR_PATH, hostname))

    # Merging a string to form a full backup file name
    backup_file_path = os.path.join(BACKUP_DIR_PATH, hostname, '{}-{}.txt'.format(hostname, timestamp))
    print('Backup file path will be ' + backup_file_path)
    print('-*-' * 10)
    print()

    # Returning backup file path
    return backup_file_path

def create_backup(connection, backup_file_path, hostname, device_type):
    # This function pulls running configuration from a device and writes it to the backup file
    # Requires connection object, backup file path, a device hostname, and device_type as inputs

    try:
        # Sending a CLI command using Netmiko and printing an output
        connection.enable()
        if device_type == "cisco_ios" or device_type == "cisco_nxos":
            output = connection.send_command('sh run')
        elif device_type == "huawei":
            output = connection.send_command('display current-configuration')

        # Creating a backup file and writing command output to it
        with open(backup_file_path, 'w') as file:
            file.write(output)
        print("Backup of " + hostname + " is complete!")
        print('-*-' * 10)
        print()

        # If successfully done
        return True

    except Exception as e:
        # If there was an error
        print('Error! Unable to backup device ' + hostname)
        print(str(e))  # Print the exception for debugging
        return False

def get_previous_backup_file_path(hostname, current_backup_file_path):
    # This function looks for the previous backup file in a directory
    # Requires a hostname and the latest backup file name as an input

    # Removing the full path
    current_backup_filename = current_backup_file_path.split('/')[-1]

    # Creating an empty dictionary to keep backup file names
    backup_files = {}

    # Looking for previous backup files
    for file_name in os.listdir(os.path.join(BACKUP_DIR_PATH, hostname)):
        # Select files with the correct extension and names
        if file_name.endswith('.txt') and file_name != current_backup_filename:
            # Getting backup date and time from filename
            filename_datetime = datetime.datetime.strptime(file_name.strip('.txt')[len(hostname) + 1:], '%Y_%m_%d-%H_%M_%S')
            # Adding backup files to dict with the key equal to datetime in Unix format
            backup_files[filename_datetime.strftime('%s')] = file_name

    if len(backup_files) > 0:
        # Getting the previous backup filename
        previous_backup_key = sorted(backup_files.keys(), reverse=True)[0]
        previous_backup_file_path = os.path.join(BACKUP_DIR_PATH, hostname, backup_files[previous_backup_key])
        print("Found a previous backup ", previous_backup_file_path)
        print('-*-' * 10)
        print()

        # Returning the previous backup file
        return previous_backup_file_path
    else:
        return False

def compare_backup_with_previous_config(previous_backup_file_path, backup_file_path):
    # This function compares the created backup with the previous one and writes delta to the changelog file
    # Requires a path to the last backup file and a path to the previous backup file as an input

    # Creating a name for the changelog file
    changes_file_path = backup_file_path.strip('.txt') + '.changes'

    # Checking if files differ from each other
    if not filecmp.cmp(previous_backup_file_path, backup_file_path):
        print('Comparing configs:')
        print('\tCurrent backup: {}'.format(backup_file_path))
        print('\tPrevious backup: {}'.format(previous_backup_file_path))
        print('\tChanges: {}'.format(changes_file_path))
        print('-*-' * 10)
        print()

        # If they do differ, open files in read mode and open the changelog in write mode
        with open(previous_backup_file_path, 'r') as f1, open(backup_file_path, 'r') as f2, open(changes_file_path, 'w') as f3:
            # Looking for delta
            delta = difflib.unified_diff(f1.read().splitlines(), f2.read().splitlines())
            # Writing discovered delta to the changelog file
            f3.write('\n'.join(delta))
        print('\tConfig state: changed')
        print('-*-' * 10)
        print()
    else:
        print('Config was not changed since the latest version.')
        print('-*-' * 10)
        print()

def process_target(device, timestamp):
    # This function will be run by each of the processes in parallel
    # This function implements a logic for a single device using other functions defined above:
    # - connects to the device,
    # - gets a backup file name and a hostname for this device,
    # - creates a backup for this device
    # - terminates connection
    # - compares a backup to the golden configuration and logs the delta
    # Requires a connection object and a timestamp string as an input

    connection = connect_to_device(device)
    backup_file_path = get_backup_file_path(device['hostname'], timestamp)
    backup_result = create_backup(connection, backup_file_path, device['hostname'], device['device_type'])
    disconnect_from_device(connection, device['hostname'])

    # If the script managed to create a backup, then look for a previous one
    if backup_result:
        previous_backup_file_path = get_previous_backup_file_path(device['hostname'], backup_file_path)

        # If the previous one exists, compare
        if previous_backup_file_path:
            compare_backup_with_previous_config(previous_backup_file_path, backup_file_path)
        else:
            print('Unable to find previous backup file to find changes.')
            print('-*-' * 10)
            print()

def main():
    # This is the main function

    # Enable logs
    enable_logging()

    # Getting the timestamp string
    timestamp = get_current_date_and_time()

    # Getting a device list from the file in a Python format
    device_list = get_devices_from_file(DEVICE_FILE_PATH)

    # Creating an empty list
    processes = list()

    # Running workers to manage connections
    with mp.Pool(4) as pool:
        # Starting several processes...
        for device in device_list:
            processes.append(pool.apply_async(process_target, args=(device, timestamp)))
        # Waiting for results...
        for process in processes:
            process.get()

if __name__ == '__main__':
    # Checking if we run independently
    main()
