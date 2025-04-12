import pandas as pd
import requests
import json
import re

# URL API NetBox
netbox_url = ''
# API-токен NetBox
api_token = ''

# Путь к Excel-файлу
xlsx_file_path = 'cable.xlsx'

# Заголовки для запросов
headers = {
    "Authorization": f"Token {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Словарь замен кириллических символов
cyr_to_lat = {
    'А': 'A', 'В': 'B', 'С': 'C', 'Е': 'E', 'К': 'K',
    'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'Т': 'T',
    'Х': 'X', 'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o',
    'р': 'p', 'х': 'x'
}

def transliterate(text):
    return ''.join([cyr_to_lat.get(char, char) for char in text])

# Получить объект устройства по имени
def get_device_id(name):
    name = transliterate(name)
    response = requests.get(f"{netbox_url}dcim/devices/?name={name}", headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
    if response.status_code == 200:
        results = response.json()['results']
        return results[0]['id'] if results else None
    return None

# Получить интерфейс устройства
def get_interface(device_name, interface_name):
    device_name = transliterate(device_name)
    interface_name = transliterate(interface_name)
    response = requests.get(f"{netbox_url}dcim/interfaces/?device={device_name}&name={interface_name}", headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
    if response.status_code == 200:
        data = response.json()['results']
        if len(data) == 1:
            return data[0]
    return None

# Создать интерфейс, если его нет
def create_interface(device_name, interface_name):
    device_id = get_device_id(device_name)
    if not device_id:
        print(f"[✗] Устройство не найдено: {device_name}")
        return None
    data = {
        "device": device_id,
        "name": transliterate(interface_name),
        "type": "1000base-t"  # Пример типа
    }
    response = requests.post(f"{netbox_url}dcim/interfaces/", json=data, headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
    if response.status_code == 201:
        print(f"[✔] Интерфейс создан: {device_name} / {interface_name}")
        return response.json()
    else:
        print(f"[✗] Не удалось создать интерфейс {device_name} / {interface_name}: {response.status_code}, {response.text}")
        return None

# Чтение файла Excel
df = pd.read_excel(xlsx_file_path)

# Проверка на наличие обязательных колонок
required_columns = ['side_a_device', 'side_a_name', 'side_a_type', 'label', 'side_b_device', 'side_b_name', 'side_b_type', 'tenant']
for col in required_columns:
    if col not in df.columns:
        raise Exception(f"Отсутствует обязательная колонка в Excel: {col}")

# Загрузка кабелей
for index, row in df.iterrows():
    label = transliterate(str(row['label']))
    a_device = transliterate(str(row['side_a_device']))
    a_name = transliterate(str(row['side_a_name']))
    a_type = str(row['side_a_type'])
    b_device = transliterate(str(row['side_b_device']))
    b_name = transliterate(str(row['side_b_name']))
    b_type = str(row['side_b_type'])
    tenant = str(row['tenant'])

    print(f"[∙] Обработка кабеля: {label}")

    a_iface = get_interface(a_device, a_name)
    if not a_iface:
        print(f"[!] Интерфейс не найден: {a_device} / {a_name}")
        a_iface = create_interface(a_device, a_name)

    b_iface = get_interface(b_device, b_name)
    if not b_iface:
        print(f"[!] Интерфейс не найден: {b_device} / {b_name}")
        b_iface = create_interface(b_device, b_name)

    if not a_iface or not b_iface:
        print(f"[!] Пропускаем кабель {label} — не удалось получить интерфейсы")
        continue

    payload = {
        "label": label,
        "a_terminations": [{
            "object_type": a_type,
            "object_id": a_iface['id']
        }],
        "b_terminations": [{
            "object_type": b_type,
            "object_id": b_iface['id']
        }]
    }

    response = requests.post(f"{netbox_url}dcim/cables/", json=payload, headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
    if response.status_code == 201:
        print(f"[✔] Кабель {label} успешно создан.")
    else:
        print(f"[✗] Ошибка создания кабеля '{label}': {response.status_code}, {response.text}")
