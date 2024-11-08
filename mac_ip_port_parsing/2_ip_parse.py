from netmiko import ConnectHandler
import csv
import yaml
import logging
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor
import re  # Импорт для работы с регулярными выражениями

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Чтение параметров подключения из YAML-файла
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Чтение данных из входного CSV-файла
data = []
with open('mac.csv', 'r') as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        data.append(row)  # Сохранение всех колонок для output.csv

# Функция для подключения к устройству и выполнения команды
def check_mac_on_device(row):
    ip = row[0]       # IP-адрес устройства
    mac_address = row[2]  # MAC-адрес
    device_params['ip'] = ip

    try:
        # Подключение к устройству
        net_connect = ConnectHandler(**device_params)

        # Выполнение команды для конкретного MAC-адреса
        command = f'sh l2route mac-ip all | in {mac_address}'
        output = net_connect.send_command(command)

        # Отключение от устройства
        net_connect.disconnect()

        # Логирование успешного выполнения команды
        logging.info(f"Выполнена команда для MAC {mac_address} на устройстве {ip}")

        # Извлечение IP-адреса из вывода
        ip_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', output)
        if ip_match:
            result_ip = ip_match.group(0)
        else:
            result_ip = "IP-адрес не найден"

        # Возвращаем результат выполнения команды
        return row + [result_ip]
AdmiA
    except SSHException as e:
        error_msg = f"Ошибка SSH при подключении к {ip}: {e}"
        logging.error(error_msg)
        return row + [error_msg]

    except Exception as ex:
        error_msg = f"Ошибка при подключении к {ip}: {ex}"
        logging.error(error_msg)
        return row + [error_msg]

# Запись результатов в выходной CSV-файл
with open('output.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['IP-адрес устройства', 'Интерфейс', 'MAC-адрес', 'Результат команды'])

    # Цикл по каждой строке из входного файла
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_mac_on_device, row) for row in data]
        for future in futures:
            result_row = future.result()
            csvwriter.writerow(result_row)  # Запись результата в файл
