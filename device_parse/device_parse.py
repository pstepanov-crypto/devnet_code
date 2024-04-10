from netmiko import ConnectHandler
import ipaddress
import re
import csv
import yaml
from paramiko.ssh_exception import SSHException
from itertools import repeat
from concurrent.futures import ThreadPoolExecutor

# Define the network ranges
network_ranges = ['192.168.0.0/24', '192.168.1.0/24']


# Define the device parameters
with open('device_params_ios.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Loop through each network range
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)

                # Send the command to get sfp information
                output = net_connect.send_command('show inventory')
                
                # Regular expression to extract device information
                match = re.search(r'PID:\s*(\S+)\s*,.*SN:\s*(\S+)', output)
                if match:
                  pid = match.group(1)
                  sn = match.group(2)
                

                # Determine the hostname
                hostname = device_params['ip']
                
                # Check if the serial number is not already in the CSV file
                with open("mcod.csv", mode="r+") as file:
                    reader = csv.reader(file)
                    serial_in_file = [row[2] for row in reader]

                if sn not in serial_in_file:
                    # Append the data to the CSV file
                   with open("mcod.csv", mode="a", newline="") as file:
                       writer = csv.writer(file)
                       writer.writerow([hostname, pid, sn])
                else:
                    print(f"Serial Number {sn} already in file, skipping.")
                

                print(f"Data written to CSV for {hostname}")

                # Disconnect from the device
                net_connect.disconnect()

            except SSHException as e:
                print(f"SSH Connection Error: {e}")

            except Exception as ex:
                print(f"An error occurred: {ex}")
