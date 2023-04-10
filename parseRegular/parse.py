import csv
from pprint import pprint
import yaml
import re
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
    with open("devices.yaml") as f, open("write.csv", "w") as s:
        devices = yaml.safe_load(f)
        writer = csv.writer(s) #a variable for writing in csv
        for device in devices:
          result = send_show_command(device, ["sh arp"])
          match = re.findall(r"Internet  (\S+)", result) #regular expression can change 
          writer.writerow([device['host'],[match]]) # parse and writing in csv file 
        print(match)
