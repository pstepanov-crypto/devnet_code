import ipaddress
import re
import yaml
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor

# Загрузка параметров устройств
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Ввод искомого MAC-адреса от пользователя
target_mac = input("Введите MAC-адрес для поиска (формат xxxx.xxxx.xxxx): ").strip().lower()

# Проверка формата MAC-адреса
if not re.match(r'^[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}$', target_mac):
    print("Ошибка: Некорректный формат MAC-адреса.")
    exit(1)

# Подсеть для поиска
network_ranges = ['192.168.0.0/24']

# Функция поиска MAC-адреса на устройстве
def find_mac_on_device(ip):
    try:
        device_params['ip'] = str(ip)
        net_connect = ConnectHandler(**device_params)
        output = net_connect.send_command("show mac address-table")

        # Регулярное выражение для поиска MAC-адреса и интерфейса
        pattern = rf"({target_mac})\s+\S+\s+(\S+)"
        match = re.search(pattern, output, re.IGNORECASE)

        if match:
            mac_address, interface = match.groups()
            print(f"MAC-адрес {mac_address} найден на устройстве {ip} на интерфейсе {interface}")
        net_connect.disconnect()
    except:
        pass  # Игнорируем ошибки

# Основная логика
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)
        executor.map(find_mac_on_device, [str(ip) for ip in network.hosts()])
