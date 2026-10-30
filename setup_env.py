"""Install dependencies only into this project's dedicated virtual environment."""
from pathlib import Path
import os
import subprocess
import sys
import venv

root = Path(__file__).resolve().parent
if sys.version_info < (3, 11):
    raise SystemExit("ScrapLab needs Python 3.11 or newer; tested with Python 3.14.7.")
temp = root / "work" / "tmp"
temp.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(temp)
os.environ["TMP"] = str(temp)
environment = root / ".venv"
python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.exists():
    venv.create(environment, with_pip=True)
subprocess.check_call([str(python), "-m", "pip", "install", "--index-url", "https://pypi.org/simple", "--only-binary=:all:", "--disable-pip-version-check", "-r", str(root / "requirements.txt")])
print("ScrapLab is ready. Run launch.cmd or .venv\\Scripts\\python.exe main.py")
