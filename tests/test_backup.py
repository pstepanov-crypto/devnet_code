import csv
import importlib.util
from pathlib import Path
import sys
import types

import pytest

# Provide a stub for the optional dependency used in backup.py
sys.modules.setdefault("netmiko", types.SimpleNamespace(ConnectHandler=None))

backup_module_path = Path(__file__).resolve().parents[1] / "backup_devices" / "backup.py"
spec = importlib.util.spec_from_file_location("backup", backup_module_path)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)
get_devices_from_file = backup.get_devices_from_file


def test_get_devices_from_file_returns_list_of_dicts(tmp_path):
    data = [
        {
            "ip": "10.0.0.1",
            "username": "admin",
            "password": "pass",
            "device_type": "cisco_ios",
            "secret": "secret1",
        },
        {
            "ip": "10.0.0.2",
            "username": "user",
            "password": "pass2",
            "device_type": "juniper",
            "secret": "secret2",
        },
    ]
    csv_file = tmp_path / "devices.csv"
    with csv_file.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    devices = get_devices_from_file(str(csv_file))
    assert devices == data


def test_get_devices_from_file_missing_file():
    with pytest.raises(FileNotFoundError):
        get_devices_from_file("no_such_file.csv")
