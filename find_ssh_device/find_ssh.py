#Скрипт для поиска ssh устройств по подсетям
import ipaddress
import yaml
from netmiko import ConnectHandler, NetMikoTimeoutException
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor


def check_ssh_device(ip, device_params):
    """
    Проверяет доступность устройства по SSH
    """
    device_params_copy = device_params.copy()
    device_params_copy['ip'] = ip
    
    try:
        # Пытаемся подключиться к устройству
        net_connect = ConnectHandler(**device_params_copy)
        
        # Если подключение успешно - получаем базовую информацию
        hostname = net_connect.find_prompt().replace('#', '').replace('>', '')
        net_connect.disconnect()
        
        print(f"✓ Устройство найдено: {ip} ({hostname})")
        return ip
        
    except NetMikoTimeoutException:
        # Таймаут подключения - устройство не отвечает или SSH не доступен
        print(f"✗ Таймаут подключения: {ip}")
        return None
        
    except SSHException as e:
        # Ошибка SSH (неправильный пароль, алгоритмы шифрования и т.д.)
        print(f"✓ Устройство с SSH найдено: {ip} (ошибка аутентификации: {str(e)[:50]}...)")
        return ip
        
    except Exception as e:
        # Другие ошибки
        print(f"? Ошибка подключения к {ip}: {str(e)[:50]}...")
        return None


def main():
    # Диапазоны сетей для сканирования
    network_ranges = ['192.168.0.0/24', '192.168.1.0/24']  # добавьте нужные сети
    
    # Параметры подключения из YAML файла
    try:
        with open('device_params_cisco.yaml') as file:
            device_params = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        print("Ошибка: Файл device_params_cisco.yaml не найден!")
        return
    
    # Параметры для сканирования (упрощенные, только для проверки доступности)
    scan_params = {
        'device_type': device_params.get('device_type', 'cisco_ios'),
        'username': device_params.get('username', ''),
        'password': device_params.get('password', ''),
        'secret': device_params.get('secret', ''),
        'timeout': 5,  # короткий таймаут для сканирования
        'fast_cli': True,  # ускоренное подключение
    }
    
    print("Начинаем сканирование сети на наличие SSH устройств...")
    print("=" * 50)
    
    found_devices = []
    
    # Сканируем сети с использованием многопоточности
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        
        for network_range in network_ranges:
            try:
                network = ipaddress.ip_network(network_range)
                print(f"Сканируем сеть: {network_range}")
                
                # Сканируем каждый IP в сети
                for ip in network.hosts():  # hosts() исключает network и broadcast адреса
                    future = executor.submit(check_ssh_device, str(ip), scan_params)
                    futures.append(future)
                    
            except ValueError as e:
                print(f"Ошибка в формате сети {network_range}: {e}")
                continue
        
        # Собираем результаты
        for future in futures:
            result = future.result()
            if result:
                found_devices.append(result)
    
    print("=" * 50)
    print(f"Сканирование завершено! Найдено устройств с SSH: {len(found_devices)}")
    
    if found_devices:
        print("Найденные устройства:")
        for device_ip in sorted(found_devices):
            print(f"  - {device_ip}")
    else:
        print("Устройства с SSH не найдены.")


if __name__ == "__main__":
    main()

