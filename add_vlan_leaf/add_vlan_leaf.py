from netmiko import ConnectHandler, NetMikoTimeoutException
import ipaddress
import yaml
from paramiko.ssh_exception import SSHException
from jinja2 import Environment, FileSystemLoader
from concurrent.futures import ThreadPoolExecutor


#Try to use address range for future
#[ipaddr for ipaddr in ipaddress.summarize_address_range(ipaddress.IPv4Address('192.168.0.1'),ipaddress.IPv4Address('192.168.0.2'))]

# Define the network ranges
network_ranges = ['192.168.0.1/32', '192.168.0.2/32']

# Define the device parameters
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Jinja2 Environment setup
env = Environment(loader=FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)
template = env.get_template('config_template.j2')

# Render J2 template for the same command
rendered_config = template.render()

# Iterate over network ranges
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)

                # Render J2 template for different command
                #liverpool = {"id": "11", "name": "Liverpool", "int": "Gi1/0/17", "ip": "10.1.1.10"}
                #rendered_config = template.render(liverpool)

                # Send rendered configuration
                output = net_connect.send_config_set(rendered_config.splitlines())

                # Determine the hostname
                hostname = device_params['ip']
                print(f"Configuration sent successfully to {hostname}")

                # Disconnect from the device
                net_connect.disconnect()

            except SSHException as e:
                print(f"SSH Connection Error: {e}")

            except Exception as ex:
                print(f"An error occurred: {ex}")
