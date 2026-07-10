"""
NetBox Script: выгрузка свободного места в стойках.

Ссылка на XLSX выводится в начале лога (до списка стоек).
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

MEDIA_DIR_CANDIDATES = [
    lambda: os.path.join(settings.MEDIA_ROOT, "script-output"),
    "/opt/netbox/netbox/media/script-output",
    "/opt/netbox-4.5.7/netbox/media/script-output",
    "/opt/netbox-4.3.7/netbox/media/script-output",
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

    def _collect_rack_data(self):
        items = []

        for rack in Rack.objects.select_related("site", "tenant", "location").order_by(
            "site__name", "location__name", "name"
        ):
            units = self._calc_free_units(rack)
            items.append(
                (
                    rack,
                    units,
                    {
                        "site": rack.site.name if rack.site else "",
                        "tenant": rack.tenant.name if rack.tenant else "",
                        "location": rack.location.name if rack.location else "",
                        "rack": rack.name,
                        "total_units": units["total"],
                        "free_front": units["free_front"],
                        "free_rear": units["free_rear"],
                    },
                )
            )

        return items

    def _log_rack_details(self, items):
        for rack, units, _row in items:
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

    def _download_url(self, filename):
        media_url = settings.MEDIA_URL.rstrip("/")
        if media_url.startswith("http"):
            path = f"{media_url}/script-output/{filename}"
        else:
            if not media_url.startswith("/"):
                media_url = f"/{media_url}"
            path = f"{media_url}/script-output/{filename}"

        try:
            from netbox import configuration

            site_url = getattr(configuration, "SITE_URL", "").rstrip("/")
            if site_url and path.startswith("/"):
                return f"{site_url}{path}"
        except ImportError:
            pass

        return path

    def _resolve_output_dir(self):
        seen = set()
        errors = []

        for candidate in MEDIA_DIR_CANDIDATES:
            output_dir = candidate() if callable(candidate) else candidate
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
        filename = f"rack_space_report.{extension}"
        filepath = os.path.join(output_dir, filename)

        mode = "wb" if isinstance(content, bytes) else "w"
        kwargs = {"encoding": "utf-8-sig", "newline": ""} if mode == "w" else {}
        with open(filepath, mode, **kwargs) as handle:
            handle.write(content)

        os.chmod(filepath, 0o644)
        os.chmod(output_dir, 0o755)

        return filename, self._download_url(filename)

    def _log_download(self, row_count, url, label):
        self.log_success("=" * 60)
        self.log_success(f"ОТЧЁТ ГОТОВ — {row_count} стоек")
        self.log_success(f"[Скачать отчёт в {label}]({url})")
        self.log_info(f"Прямая ссылка: {url}")
        self.log_info(
            "Запасной вариант: вкладка Output → Download (CSV, переименуйте .txt в .csv)"
        )
        self.log_success("=" * 60)

    def run(self, data, commit):
        items = self._collect_rack_data()

        if not items:
            self.log_warning("Стойки не найдены.")
            return

        rows = [item[2] for item in items]
        csv_output = self._build_csv(rows)
        use_xlsx = Workbook is not None
        extension = "xlsx" if use_xlsx else "csv"
        label = "XLSX" if use_xlsx else "CSV"

        if not use_xlsx:
            self.log_warning("Модуль openpyxl не установлен — выгружен CSV вместо XLSX.")

        # Ссылка в начале лога — до длинного списка стоек
        try:
            file_content = self._build_xlsx(rows) if use_xlsx else csv_output
            _filename, url = self._save_file(file_content, extension)
            self._log_download(len(rows), url, label)
        except OSError as exc:
            self.log_failure(f"Не удалось сохранить файл в media:\n{exc}")
            self.log_info("Скачайте отчёт: вкладка Output → Download (переименуйте .txt в .csv)")

        self._log_rack_details(items)

        # NetBox всегда скачивает Output как .txt — отдаём CSV-текст для Excel
        return csv_output
