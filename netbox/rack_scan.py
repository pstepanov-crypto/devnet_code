"""
NetBox Script: выгрузка свободного места в стойках.

После запуска — ссылка «Скачать XLSX» в логе.
Зависимость: openpyxl (pip install openpyxl в venv NetBox).
"""

import csv
import os
from io import BytesIO, StringIO

from dcim.models import Device, Rack
from django.conf import settings
from extras.scripts import Script

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font
except ImportError:
    Workbook = None

HEADERS = [
    "Site",
    "Tenant",
    "Location",
    "Rack",
    "Всего U",
    "Свободно (front)",
    "Свободно (rear)",
]


class RackUnitSpaceExport(Script):
    class Meta:
        name = "Выгрузка свободного места в стойках"
        description = (
            "Excel-отчёт (.xlsx): Site, Tenant, Location, Rack и количество "
            "свободных юнитов (front / rear) с учётом full-depth устройств."
        )

    def _calc_free_units(self, rack):
        total_units = rack.u_height or 0
        occupied_front = 0
        occupied_rear = 0

        for device in Device.objects.filter(rack=rack, position__isnull=False):
            device_type = device.device_type
            device_height = device_type.u_height if device_type else 0
            is_full_depth = device_type.is_full_depth if device_type else False

            if is_full_depth:
                occupied_front += device_height
                occupied_rear += device_height
            elif device.face == "front":
                occupied_front += device_height
            elif device.face == "rear":
                occupied_rear += device_height

        return {
            "total": total_units,
            "free_front": total_units - occupied_front,
            "free_rear": total_units - occupied_rear,
        }

    def _rack_rows(self):
        rows = []

        for rack in Rack.objects.select_related("site", "tenant", "location").order_by(
            "site__name", "location__name", "name"
        ):
            units = self._calc_free_units(rack)

            rows.append(
                {
                    "site": rack.site.name if rack.site else "",
                    "tenant": rack.tenant.name if rack.tenant else "",
                    "location": rack.location.name if rack.location else "",
                    "rack": rack.name,
                    "total_units": units["total"],
                    "free_front": units["free_front"],
                    "free_rear": units["free_rear"],
                }
            )

            if units["free_front"] > 0 or units["free_rear"] > 0:
                self.log_success(
                    f"Свободных юнитов (передняя): {units['free_front']} из {units['total']}, "
                    f"(задняя): {units['free_rear']} из {units['total']}.",
                    rack,
                )
            else:
                self.log_warning(
                    "Нет свободных юнитов ни на передней, ни на задней стороне.",
                    rack,
                )

        return rows

    def _row_values(self, row):
        return [
            row["site"],
            row["tenant"],
            row["location"],
            row["rack"],
            row["total_units"],
            row["free_front"],
            row["free_rear"],
        ]

    def _build_xlsx(self, rows):
        wb = Workbook()
        ws = wb.active
        ws.title = "Rack Space"
        ws.append(HEADERS)

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for row in rows:
            ws.append(self._row_values(row))

        for column in ws.columns:
            max_length = max(len(str(cell.value or "")) for cell in column)
            ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def _build_csv(self, rows):
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(HEADERS)

        for row in rows:
            writer.writerow(self._row_values(row))

        return "\ufeff" + buffer.getvalue()

    def _media_url(self, filename):
        media_url = settings.MEDIA_URL.rstrip("/")
        if media_url.startswith("http"):
            return f"{media_url}/script-output/{filename}"
        if not media_url.startswith("/"):
            media_url = f"/{media_url}"
        return f"{media_url}/script-output/{filename}"

    def _resolve_output_dir(self):
        candidates = [
            os.path.join(settings.MEDIA_ROOT, "script-output"),
            "/opt/netbox/netbox/media/script-output",
            "/opt/netbox-4.3.7/netbox/media/script-output",
        ]

        seen = set()
        errors = []

        for output_dir in candidates:
            if output_dir in seen:
                continue
            seen.add(output_dir)

            try:
                os.makedirs(output_dir, exist_ok=True)
                test_path = os.path.join(output_dir, ".write_test")
                with open(test_path, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(test_path)
                return output_dir
            except OSError as exc:
                errors.append(f"{output_dir}: {exc}")

        raise OSError(
            "нет доступа на запись в media. Выполните на сервере:\n"
            "mkdir -p /opt/netbox/netbox/media/script-output\n"
            "chown -R netbox:netbox /opt/netbox/netbox/media\n"
            "chmod 755 /opt/netbox/netbox/media\n\n"
            + "\n".join(errors)
        )

    def _save_file(self, content, extension):
        output_dir = self._resolve_output_dir()
        # Общий файл — одна ссылка для всех пользователей
        filename = f"rack_space_report.{extension}"
        filepath = os.path.join(output_dir, filename)

        mode = "wb" if isinstance(content, bytes) else "w"
        kwargs = {"encoding": "utf-8-sig", "newline": ""} if mode == "w" else {}
        with open(filepath, mode, **kwargs) as handle:
            handle.write(content)

        os.chmod(filepath, 0o644)
        os.chmod(output_dir, 0o755)

        return filename, self._media_url(filename)

    def run(self, data, commit):
        rows = self._rack_rows()

        if not rows:
            self.log_warning("Стойки не найдены.")
            return

        try:
            if Workbook is not None:
                filename, url = self._save_file(self._build_xlsx(rows), "xlsx")
                self.log_success(
                    f"Сформирован отчёт по {len(rows)} стойкам. "
                    f"[Скачать отчёт в XLSX]({url})"
                )
            else:
                filename, url = self._save_file(self._build_csv(rows), "csv")
                self.log_warning(
                    "Модуль openpyxl не установлен — выгружен CSV вместо XLSX."
                )
                self.log_success(
                    f"Сформирован отчёт по {len(rows)} стойкам. "
                    f"[Скачать отчёт в CSV]({url})"
                )
        except OSError as exc:
            self.log_failure(f"Не удалось сохранить файл в media:\n{exc}")
