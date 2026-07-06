import sys
import subprocess
from aqt import mw
from aqt.utils import showInfo, showWarning, askUser
from .constants import MENU_NAME

PACKAGES = ["numpy", "scipy", "sklearn", "fastcluster"] # List of required packages
REQUIRED = {
    "numpy": "numpy",
    "scipy": "scipy",
    "sklearn": "scikit-learn",
    "fastcluster": "fastcluster",
}

def install_deps():
    try:
        cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir"] + list(REQUIRED.values())
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        mw.taskman.run_on_main(lambda: showInfo("Dependencies installed. Please restart Anki."))
    except Exception as e:
        err_msg = str(e)
        mw.taskman.run_on_main(lambda: showWarning(f"Failed to install dependencies:\n{err_msg}"))

def check_and_install_deps():
    try:
        for package in PACKAGES:
            __import__(package)
        return True
    except ImportError:
        msg = (
            f"The '{MENU_NAME}' add-on requires:\n\n{', '.join(PACKAGES)}\n\n"
            "Install now? (Anki may freeze briefly)"
        )
        if not askUser(msg):
            showWarning("Installation canceled.")
            return False
        mw.progress.start(label="Installing dependencies...", immediate=True)
        mw.taskman.run_in_background(install_deps, lambda _: mw.progress.finish())
        return False