import pandas as pd
import requests

# URL API NetBox
netbox_url = ''
# API-токен, полученный из интерфейса NetBox
api_token = ''  # Укажите ваш токен

# Путь к XLSX-файлу
xlsx_file_path = 'pref.xlsx'  # Укажите ваш файл

# Заголовки для аутентификации
headers = {
    "Authorization": f"Token {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def add_interface_template(prefix, description, comments):
    # Данные для добавления Interface Template
    data = {
        "prefix": prefix,
        "description": description,
        "comments": comments
    }

    # Отправка POST запроса на добавление элемента Interface Template
    url = f"{netbox_url}ipam/prefixes/"
    response = requests.post(url, json=data, headers=headers, verify='')

    # Проверка успешности запроса
    if response.status_code == 201:
        print(f"Префикс {prefix} успешно добавлен.")
    else:
        print(f"Ошибка при добавлении префикса {prefix}: {response.status_code}, {response.text}")

# Чтение XLSX-файла
df = pd.read_excel(xlsx_file_path)

# Обработка каждой строки
for index, row in df.iterrows():
    prefix = row['prefix']
    description = row['description']
    comments = row['comments']
    
    # Вызываем функцию добавления интерфейса
    add_interface_template(prefix, description, comments)
