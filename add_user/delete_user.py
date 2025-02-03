from netmiko import ConnectHandler, NetMikoTimeoutException
import ipaddress
import yaml
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor

# Define the network ranges
network_ranges = ['192.168.0.0/24', '192.168.1.0/24']

# Define the device parameters
with open('device_params_ios.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Define the username to delete
username_to_delete = 'user1'

def delete_user_from_device(ip, device_params, username):
    device_params['ip'] = ip
    try:
        # Connect to the device
        net_connect = ConnectHandler(**device_params)

        # Send command to delete the user
        config_commands = [
            f"no username {username}"
        ]
        output = net_connect.send_config_set(config_commands)

        # Save the configuration (write memory)
        net_connect.save_config()

        # Determine the hostname
        hostname = net_connect.find_prompt().strip('#>')
        print(f"User {username} deleted from {hostname} ({ip})")

        # Disconnect from the device
        net_connect.disconnect()

    except (SSHException, NetMikoTimeoutException) as e:
        print(f"Connection Error to {ip}: {e}")
    except Exception as ex:
        print(f"An error occurred on {ip}: {ex}")

# Threads for multiple network ranges
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            executor.submit(delete_user_from_device, str(ip), device_params, username_to_delete)
