#The script is parse sfp based on regular expression and used command - show inventory | include SFP | SN
from netmiko import ConnectHandler
import ipaddress
import re
import csv
from paramiko.ssh_exception import SSHException

# Define the network range
network = ipaddress.ip_network('192.168.0.0/24')

# Define the device parameters
device_params = {
    'device_type': 'cisco_ios',
    'username': 'cisco',
    'password': 'cisco'
}

# Loop through each IP address in the network range
for ip in network:
    device_params['ip'] = str(ip)
    try:
        # Connect to the device
        net_connect = ConnectHandler(**device_params)

        # Send the command to get sfp information
        output = net_connect.send_command('show inventory | include SFP | SN')

        # Regular expression to extract SFP information
        match = re.findall(r'(SFP-\S+) (?:\s*,\s*VID:\s*[^,]+,\s*) (SN:\s*[^\s]+)', output)

        # Determine the hostmame
        hostname = device_params['ip']

        # Write to CSV
        with open("sfp.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            for sfp_info in match:
                writer.writerow([hostname, sfp_info[0], sfp_info[1]])

        print(f"Data written to CSV for {hostname}")

        # Disconnect from the device
        net_connect.disconnect()

    except SSHException as e:
        print(f"SSH Connection Error: {e}")

    except Exception as ex:
        print(f"An error occurred: {ex}")
