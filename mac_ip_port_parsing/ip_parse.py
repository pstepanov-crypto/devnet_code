import pandas as pd
import subprocess
import re

# Загрузка данных из файла Excel
df = pd.read_excel('ip.xlsx', usecols=['IP-адрес устройства', 'Интерфейс', 'MAC-адрес', 'Результат команды'])

# Функция для выполнения nslookup и возврата второго совпадения с "sms"
def nslookup_by_ip(ip_address):
    try:
        # Выполнение nslookup для IP-адреса
        result = subprocess.run(['nslookup', ip_address], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        
        if result.returncode == 0:
            output = result.stdout.decode('cp866', errors='ignore').strip()
            print(f"Результат для {ip_address}:\n{output}")  # Вывод для отладки

            # Ищем все совпадения, содержащие "sms" и всё, что идёт после
            matches = re.findall(r'\bmms[\w\.-]*', output, re.IGNORECASE)
           

            # Возвращаем второй матч, если он есть
            if len(matches) >= 2:
                return matches[1]
            else:
                return "Второй матч не найден"
        else:
            return "Недоступен"
    except subprocess.TimeoutExpired:
        return "Недоступен"
    except Exception as e:
        print(f"Ошибка при выполнении nslookup для {ip_address}: {e}")
        return "Недоступен"

# Применение функции к каждому значению в колонке "Результат команды"
df['Имя хоста'] = df['Результат команды'].apply(nslookup_by_ip)

# Сохранение изменений в новом файле Excel
df.to_excel('nslookup_mms.xlsx', index=False)
