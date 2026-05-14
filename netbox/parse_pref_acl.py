import sys
import ipaddress
import requests
import urllib3

# Отключаем предупреждения SSL для самоподписанных сертификатов
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К NETBOX
NETBOX_URL = ""
TOKEN = ""
SSL_CERT = "/root/project/"

HEADERS = {
      "Authorization": f"Token {TOKEN}",
      "Accept": "application/json"
}

def get_acl_by_ip_or_prefix(target):
     params = {}

     # 1. Валидация входных данных
     try:
         if "/" in target:
             ipaddress.ip_network(target, strict=False)
             params["prefix"] = target  # Поиск точного совпадения префикса
         else:
             ipaddress.ip_address(target)
             params["contains"] = target  # Поиск всех подсетей, куда входит IP
     except ValueError:
         print(f"❌ Ошибка: '{target}' не является валидным IP или префиксом.")
         sys.exit(1)

     # 2. Выполнение запроса к NetBox API
     try:
         response = requests.get(NETBOX_URL, headers=HEADERS, params=params, verify=SSL_CERT)

         if response.status_code != 200:
             print(f"❌ Ошибка API! Код ответа: {response.status_code}")
             print(f"Ответ сервера: {response.text}")
             sys.exit(1)

         data = response.json()

         if data.get("count", 0) == 0:
             print(f" Для '{target}' префикс в NetBox не найден.")
             sys.exit(0)

         # 3. Извлечение списка всех найденных префиксов
         all_prefixes = data["results"]

         # 4. Сортировка по длине маски подсети (от меньшей к большей).
         # Превращает строку "192.168.0.0/24" -> берет "24" -> конвертирует в int для сравнения.
         all_prefixes.sort(key=lambda x: int(x.get("prefix","").split('/')[-1]))

         # 5. Выбор самого специфичного (последнего в отсортированном списке) префикса
         matched_prefix_obj = all_prefixes[-1]

         # 6. Чтение кастомных полей
         custom_fields = matched_prefix_obj.get("custom_fields", {})
         acl_value = custom_fields.get("ACL")

         # 7. Вывод результата в консоль
         if acl_value:
             print(acl_value)
         else:
             print("ACL_NOT_DEFINED")

     except requests.exceptions.ConnectionError as ce:
         print(f"❌ Ошибка подключения: {ce}")
         sys.exit(1)
     except Exception as e:
         print(f"❌ Непредвиденная ошибка: {e}")
         sys.exit(1)

if __name__ == "__main__":
     # Проверка аргументов командной строки
     if len(sys.argv) < 2:
         print(" Использование: python3 query.py <IP_адрес_или_Префикс>")
         print(" Пример:    python3 query.py 192.168.1.1")
         print(" Пример 2:   python3 query.py 192.168.0.0/24")
         sys.exit(1)

     user_input = sys.argv[1]
     get_acl_by_ip_or_prefix(user_input)
