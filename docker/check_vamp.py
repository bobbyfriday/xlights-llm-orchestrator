"""Build-time check: every required VAMP plugin loads and is visible to the python host.

On failure, prints what's in VAMP_PATH, each library's dlopen result and `ldd` output, so a
broken plugin build is diagnosable from the CI log alone."""

import ctypes
import os
import subprocess
import sys
from pathlib import Path

import vamp
from xlights_core.audio.extractors.vamp_host import REQUIRED_PLUGIN_LIBS

path = os.environ.get("VAMP_PATH", "")
found = {p.split(":", 1)[0] for p in vamp.list_plugins()}
missing = REQUIRED_PLUGIN_LIBS - found
print(f"VAMP_PATH={path!r}; host sees libraries: {sorted(found)}")
if not missing:
    print("vamp plugins OK")
    sys.exit(0)
for d in path.split(":"):
    for so in sorted(Path(d).glob("*.so")) if d else []:
        try:
            lib = ctypes.CDLL(str(so))
            print(f"{so}: dlopen OK, vampGetPluginDescriptor={hasattr(lib, 'vampGetPluginDescriptor')}")
        except OSError as exc:
            print(f"{so}: dlopen FAILED: {exc}")
        print(subprocess.run(["ldd", str(so)], capture_output=True, text=True).stdout)
    if d:
        print(f"{d}: {sorted(os.listdir(d)) if os.path.isdir(d) else 'MISSING'}")
sys.exit(f"missing VAMP plugin libraries: {sorted(missing)}")
