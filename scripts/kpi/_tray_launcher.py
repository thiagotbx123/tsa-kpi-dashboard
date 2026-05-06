"""Wrapper to launch kpi_tray.py and capture any crash."""
import traceback
import os
import sys

LOG = os.path.join(os.path.expanduser('~'), 'Downloads', 'kpi-serve', 'crash.log')
os.makedirs(os.path.dirname(LOG), exist_ok=True)

try:
    # Clear old crash log
    if os.path.exists(LOG):
        os.remove(LOG)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        '__main__',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kpi_tray.py')
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = '__main__'
    spec.loader.exec_module(mod)
except SystemExit:
    pass
except Exception:
    with open(LOG, 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
