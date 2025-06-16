#Загрузка конфигураций для Leaf и BorderLeaf отдельными template
from netmiko import ConnectHandler, NetMikoTimeoutException
import ipaddress
import yaml
import time
from paramiko.ssh_exception import SSHException
from jinja2 import Environment, FileSystemLoader
from concurrent.futures import ThreadPoolExecutor

# Cisco Leafs ODC - RDC
network_ranges = [
    '192.168.1.1/32', '192.168.1.2/32', '192.168.2.1/32', '192.168.2.2/32'
]

# Определяем IP-адреса для borderleaf (без масок)
BORDERLEAF_IPS = {
   '192.168.1.1, '192.168.1.2
}

# Загружаем параметры устройств
with open('device_params_nxos.yaml') as file:
    device_params = yaml.safe_load(file)  # Используем safe_load для безопасности

# Инициализируем Jinja2
env = Environment(loader=FileSystemLoader('.'), trim_blocks=True, lstrip_blocks=True)
borderleaf_template = env.get_template('template_borderleaf.j2')
vxlan_template = env.get_template('template_vxlan.j2')

def configure_device(ip_with_mask):
    """Функция для настройки одного устройства"""
    try:
        # Преобразуем строку в объект сети
        network = ipaddress.ip_network(ip_with_mask, strict=False)
        
        # Для /32 сети берем первый и единственный адрес
        ip_str = str(network.network_address)
        
        # Выбираем шаблон на основе IP
        if ip_str in BORDERLEAF_IPS:
            template = borderleaf_template
            print(f"Используется borderleaf шаблон для {ip_str}")
        else:
            template = vxlan_template
            print(f"Используется vxlan шаблон для {ip_str}")
        
        # Рендерим конфигурацию
        rendered_config = template.render()
        
        # Обновляем параметры подключения
        device_params['ip'] = ip_str
        
        # Подключаемся к устройству
        net_connect = ConnectHandler(**device_params)
        
        # Отправляем конфигурацию
        output = net_connect.send_config_set(rendered_config.splitlines())
        time.sleep(7)  # Пауза между командами
        
        # Закрываем соединение
        net_connect.disconnect()
        
        print(f"Конфигурация успешно применена на {ip_str}")
        return True
        
    except (SSHException, NetMikoTimeoutException) as e:
        print(f"Ошибка подключения к {ip_str}: {str(e)}")
        return False
    except Exception as ex:
        print(f"Неизвестная ошибка для {ip_str}: {str(ex)}")
        return False

# Главный цикл выполнения
if __name__ == "__main__":
    # Используем ThreadPoolExecutor для параллельного выполнения
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Создаем задачи для каждого устройства
        results = executor.map(configure_device, network_ranges)
        
        # Подсчитываем успешные операции
        success_count = sum(1 for result in results if result)
        print(f"\nИтог: Успешно настроено {success_count} из {len(network_ranges)} устройств")
