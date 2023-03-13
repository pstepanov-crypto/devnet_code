import csv
from pprint import pprint
import yaml
from netmiko import (
    ConnectHandler,
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)


def send_show_command(device, commands):
    with ConnectHandler(**device) as ssh:
        ssh.enable()
        result = ssh.send_config_set(commands)
    return result


if __name__ == "__main__":
    with open("devices.yaml") as f, open("sw_data.csv") as d:
        devices = yaml.safe_load(f)
        reader = csv.reader(d) #variable witch data 
        for protocol,ip,direction in reader:
            print(protocol,ip,direction)
            for device in devices:
                result = send_show_command(device, ["ip access-list extended test", f"permit {protocol} host {ip} {direction}"])
            print(result)
