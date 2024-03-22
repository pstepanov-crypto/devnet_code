########## upgrade_script.py - start ##########
#1. скачать new version - wget https://github.com/netbox-community/netbox/archive/v3.6.4.tar.gz
#2. after - sudo tar -xzf v3.6.4.tar.gz -C /opt
#3. текущую папку netbox нужно переименовать в netbox-5.7.0 ,а новую версию (3.6.4) в просто netbox
#4. и затем запускай скрипт с позиции sudo cp /opt/netbox-5.7.0/netbox/netbox/local_requirements.txt /opt/netbox/netbox/netbox/
#5. Не забудь отключить плагины перед обновлением
####python3 netbox_update.py -f 5.7.0 -t 3.6.4
import argparse
parser = argparse.ArgumentParser(description='A simple script to help with netbox upgrades')
parser.add_argument("-f",help="Version of netbox you're looking to upgrade FROM 'ex 5.7.0'")
parser.add_argument("-t",help="Version of netbox you're looking to upgrade TO 'ex 3.6.4'")

args = parser.parse_args()
goFrom = str(args.f)
goTo = str(args.t)

print ("### BEGIN NETBOX UPGRADE CODE ###")
print ("sudo cp /opt/netbox-" + goFrom + "/local_requirements.txt /opt/netbox/")
print ("sleep 3")
print ("sudo cp /opt/netbox-" + goFrom + "/netbox/netbox/configuration.py /opt/netbox/netbox/netbox/")
print ("sleep 3")
print ("sudo cp /opt/netbox-" + goFrom + "/netbox/netbox/ldap_config.py /opt/netbox/netbox/netbox/")
print ("sleep 3")
print ("sudo cp -pr /opt/netbox-" + goFrom + "/netbox/media/ /opt/netbox/netbox/")
print ("sleep 3")
print ("sudo cp -r /opt/netbox-" + goFrom + "/netbox/scripts /opt/netbox/netbox/")
print ("sleep 3")
print ("sudo cp -r /opt/netbox-" + goFrom + "/netbox/reports /opt/netbox/netbox/")
print ("sleep 3")
print ("sudo cp /opt/netbox-" + goFrom + "/gunicorn.py /opt/netbox/") 
print ("sleep 3")
print ("sudo /opt/netbox/upgrade.sh")
print ("sleep 3")
print ("sudo systemctl restart netbox netbox-rq") 
print ("sleep 3")
print ("#### END NETBOX UPGRADE CODE ####")

########## upgrade_script.py - end ##########
