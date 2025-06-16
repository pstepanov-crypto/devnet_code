#создание cables внутри netbox из файла exel и связывание device, так же создает интерфейсы внутри девайсов если их нет
import pandas as pd
import requests
import json
import re
from requests.exceptions import RequestException

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
    try:
        response = requests.get(f"{netbox_url}dcim/devices/?name={name}", headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
        if response.status_code == 200:
            results = response.json()['results']
            return results[0]['id'] if results else None
    except RequestException as e:
        print(f"[✗] Ошибка при получении устройства {name}: {str(e)}")
    return None

# Получить интерфейс устройства
def get_interface(device_name, interface_name):
    device_name = transliterate(device_name)
    interface_name = transliterate(interface_name)
    try:
        response = requests.get(f"{netbox_url}dcim/interfaces/?device={device_name}&name={interface_name}", headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
        if response.status_code == 200:
            data = response.json()['results']
            return data[0] if data else None
    except RequestException as e:
        print(f"[✗] Ошибка при получении интерфейса {device_name}/{interface_name}: {str(e)}")
    return None

# Создать интерфейс
def create_interface(device_name, interface_name, interface_type):
    device_id = get_device_id(device_name)
    if not device_id:
        return None
    data = {
        "device": device_id,
        "name": transliterate(interface_name),
        "type": interface_type
    }
    try:
        response = requests.post(f"{netbox_url}dcim/interfaces/", json=data, headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
        if response.status_code == 201:
            return response.json()
        else:
            print(f"[✗] Ошибка создания интерфейса: {response.text}")
    except RequestException as e:
        print(f"[✗] Ошибка при создании интерфейса: {str(e)}")
    return None

# Получить tenant ID по имени
def get_tenant_id(name):
    if pd.isnull(name) or not name.strip():
        return None
    try:
        response = requests.get(f"{netbox_url}tenancy/tenants/?name={name}", headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
        if response.status_code == 200:
            results = response.json()['results']
            return results[0]['id'] if results else None
    except RequestException as e:
        print(f"[✗] Ошибка при получении tenant {name}: {str(e)}")
    return None

# Чтение файла Excel
df = pd.read_excel(xlsx_file_path)

# Проверка обязательных колонок
required_columns = [
    'side_a_device', 'side_a_name', 'side_a_type', 'side_b_device',
    'side_b_name', 'side_b_type', 'label', 'type', 'status', 'length',
    'length_unit', 'color', 'tenant'
]
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    raise Exception(f"Отсутствуют обязательные колонки: {', '.join(missing_columns)}")

# Добавляем новые колонки если их нет
if 'type_interface_a' not in df.columns:
    df['type_interface_a'] = ''
if 'type_interface_b' not in df.columns:
    df['type_interface_b'] = ''

# Логирование ошибок
error_logs = []

# Обработка кабелей
for index, row in df.iterrows():
    row_errors = {}
    try:
        label = transliterate(str(row['label']))
        a_device = transliterate(str(row['side_a_device']))
        a_name = transliterate(str(row['side_a_name']))
        b_device = transliterate(str(row['side_b_device']))
        b_name = transliterate(str(row['side_b_name']))
        tenant_name = str(row['tenant']) if pd.notnull(row['tenant']) else ''
        
        # Определение типа интерфейса для стороны A
        if pd.notnull(row['type_interface_a']) and row['type_interface_a'] != '':
            a_type = str(row['type_interface_a'])
        else:
            a_type = str(row['side_a_type'])
            
        # Определение типа интерфейса для стороны B
        if pd.notnull(row['type_interface_b']) and row['type_interface_b'] != '':
            b_type = str(row['type_interface_b'])
        else:
            b_type = str(row['side_b_type'])

        # Получаем tenant ID
        tenant_id = get_tenant_id(tenant_name)
        if tenant_name and not tenant_id:
            raise Exception(f"Tenant '{tenant_name}' не найден")

        # Обработка интерфейсов
        a_iface = get_interface(a_device, a_name)
        if not a_iface:
            a_iface = create_interface(a_device, a_name, a_type)
            if not a_iface:
                raise Exception(f"Не удалось создать интерфейс {a_device}/{a_name}")

        b_iface = get_interface(b_device, b_name)
        if not b_iface:
            b_iface = create_interface(b_device, b_name, b_type)
            if not b_iface:
                raise Exception(f"Не удалось создать интерфейс {b_device}/{b_name}")

        # Подготовка данных кабеля
        cable_data = {
            "label": label,
            "a_terminations": [{"object_type": "dcim.interface", "object_id": a_iface['id']}],
            "b_terminations": [{"object_type": "dcim.interface", "object_id": b_iface['id']}],
            "type": row['type'],
            "status": row['status'],
            "length": row['length'],
            "length_unit": row['length_unit'],
            "color": row['color'].strip() if pd.notnull(row['color']) else None,
            "tenant": tenant_id
        }
        cable_data = {k: v for k, v in cable_data.items() if v is not None}

        # Создание кабеля
        response = requests.post(f"{netbox_url}dcim/cables/", json=cable_data, headers=headers, verify='/root/project/netbox_sirius_api/netbox.pem')
        if response.status_code != 201:
            raise Exception(f"Ошибка API: {response.text}")

    except Exception as e:
        error_logs.append({
            "row": index + 2,
            "error": str(e),
            **{col: row.get(col, '') for col in df.columns}
        })
        print(f"[✗] Ошибка в строке {index + 2}: {str(e)}")

# Сохранение лога ошибок
if error_logs:
    error_df = pd.DataFrame(error_logs)
    error_df.to_excel('error_log.xlsx', index=False)
    print(f"[✔] Найдено {len(error_logs)} ошибок. Лог сохранен в error_log.xlsx")
else:
    print("[✔] Обработка завершена без ошибок")
