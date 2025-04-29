#Скрипт модуль, для Netbox, проходит по всем стойкам и выводит не занятые юниты
from extras.reports import Report
from dcim.models import Rack, Device

class RackUnitSpaceReport(Report):
    description = "Отчет о количестве свободных юнитов в front и rear стойках с учетом устройств full depth."

    def test_rack_space(self):
        # Проходим по всем стойкам
        for rack in Rack.objects.all():
            total_units = rack.u_height or 0
            occupied_units_front = 0
            occupied_units_rear = 0

            # Получаем все устройства в данной стойке
            for device in Device.objects.filter(rack=rack, position__isnull=False):
                # Получаем высоту устройства в юнитах
                device_height = device.device_type.u_height if device.device_type else 0
                is_full_depth = device.device_type.is_full_depth if device.device_type else False

                # Если устройство full depth, его высота добавляется к обеим сторонам
                if is_full_depth:
                    occupied_units_front += device_height
                    occupied_units_rear += device_height
                else:
                    # Проверяем сторону, где установлено устройство, и суммируем его высоту для каждой стороны отдельно
                    if device.face == 'front':
                        occupied_units_front += device_height
                    elif device.face == 'rear':
                        occupied_units_rear += device_height

            # Подсчитываем свободные юниты для передней и задней сторон
            free_units_front = total_units - occupied_units_front
            free_units_rear = total_units - occupied_units_rear

            # Логируем результаты для каждой стороны
            if free_units_front > 0 or free_units_rear > 0:
                self.log_success(
                    rack, 
                    f"Свободных юнитов (передняя сторона): {free_units_front} из {total_units}, "
                    f"(задняя сторона): {free_units_rear} из {total_units}."
                )
            else:
                self.log_warning(rack, "Нет свободных юнитов ни на передней, ни на задней стороне.")
