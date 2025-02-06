import requests
from datetime import datetime
import urllib3

# Отключение предупреждений о небезопасных запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Укажите URL вашего NetBox и API токен
NETBOX_URL = ''
API_TOKEN = ''

# Заголовки для авторизации
headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

# Функция для получения всех префиксов
def get_all_prefixes():
    prefixes = []
    url = f"{NETBOX_URL}ipam/prefixes/"  # Убрал лишний слэш
    while url:
        response = requests.get(url, headers=headers, verify=False)  # Отключена проверка SSL
        data = response.json()
        prefixes.extend(data['results'])
        url = data['next']  # Пагинация, если префиксов много
    return prefixes

# Функция для удаления префикса по ID
def delete_prefix(prefix_id):
    url = f"{NETBOX_URL}ipam/prefixes/{prefix_id}/"  # Убрал лишний слэш
    response = requests.delete(url, headers=headers, verify=False)  # Отключена проверка SSL
    if response.status_code == 204:
        print(f"Deleted prefix with ID {prefix_id}")
    else:
        print(f"Failed to delete prefix with ID {prefix_id}: {response.status_code}")

# Получаем все префиксы
prefixes = get_all_prefixes()

# Создаем словарь для группировки префиксов по значению
prefix_dict = {}
for prefix in prefixes:
    prefix_str = prefix['prefix']
    if prefix_str not in prefix_dict:
        prefix_dict[prefix_str] = []
    prefix_dict[prefix_str].append(prefix)

# Проходим по словарю и удаляем более старые дубликаты
for prefix_str, prefix_list in prefix_dict.items():
    if len(prefix_list) > 1:
        # Сортируем префиксы по дате создания (created)
        prefix_list.sort(key=lambda x: x['created'])
        # Оставляем самый новый префикс, удаляем остальные
        for prefix in prefix_list[:-1]:  # Все, кроме последнего (самого нового)
            print(f"Deleting duplicate prefix {prefix['prefix']} (ID: {prefix['id']}, created: {prefix['created']})")
            delete_prefix(prefix['id'])
