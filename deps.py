import sys
import subprocess
import os
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

def get_anki_venv_site_packages():
    if sys.platform == "win32" or sys.platform == "cygwin":  # Windows
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        path = os.path.join(local_app_data, "AnkiProgramFiles", ".venv", "Lib", "site-packages")
        return path if os.path.exists(path) else None
    
    elif sys.platform == "darwin": # macOS
        base_dir = os.path.expanduser("~/Library/Application Support/AnkiProgramFiles/.venv")
        # Match lib/python3.x/site-packages regardless of exact minor version
        matches = glob.glob(os.path.join(base_dir, "lib", "python*", "site-packages"))
        return matches[0] if matches else None
        
    else: # Linux
        base_dir = os.path.expanduser("~/.local/share/AnkiProgramFiles/.venv")
        matches = glob.glob(os.path.join(base_dir, "lib", "python*", "site-packages"))
        return matches[0] if matches else None

def add_site_packages_to_sys_path():
    site_packages_dir = get_anki_venv_site_packages()
    if site_packages_dir and site_packages_dir not in sys.path:
        sys.path.insert(0, site_packages_dir)

def get_anki_venv_python():
    if sys.platform == "win32" or sys.platform == "cygwin":  # Windows
        local_app_data = os.environ.get("LOCALAPPDATA")
        print(f"Local App Data: {local_app_data}")
        return os.path.join(local_app_data, "AnkiProgramFiles", ".venv", "Scripts", "python.exe")
    elif sys.platform == "darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/AnkiProgramFiles/.venv/bin/python")
    else:  # Linux
        return os.path.expanduser("~/.local/share/AnkiProgramFiles/.venv/bin/python")

# Package versions: {'numpy': '2.3.4', 'scipy': '1.16.3', 'sklearn': '1.7.2', 'fastcluster': '1.3.0'}
def print_package_versions():
    versions = {}
    for package in PACKAGES:
        try:
            module = __import__(package)
            versions[package] = module.__version__
        except ImportError:
            versions[package] = "Not installed"
    print("Package versions:", versions)
    return versions

def is_valid_python_runner(exe_path):
    if not exe_path or not os.path.exists(exe_path):
        return False
    try:
        res = subprocess.run([exe_path, "-c", "import pip"], capture_output=True, timeout=5, text=True)
        return res.returncode == 0
    except Exception:
        return False

def install_deps():
    candidates = []
    if sys.executable:
        candidates.append(sys.executable)

    venv_python = get_anki_venv_python()
    if venv_python and venv_python not in candidates:
        candidates.append(venv_python)

    errors = []
    for exe in candidates:
        if not is_valid_python_runner(exe):
            errors.append(f"[{exe}] Invalid or missing pip support.")
            continue

        cmd = [exe, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir"] + list(REQUIRED.values())

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            mw.taskman.run_on_main(lambda: showInfo("Dependencies installed successfully. Please restart Anki."))
            return
        except subprocess.CalledProcessError as e:
            errors.append(f"[{exe}] Failed:\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")
        except Exception as e:
            errors.append(f"[{exe}] Error: {str(e)}")
            
    err_msg = "\n\n".join(errors)
    mw.taskman.run_on_main(lambda: showWarning(f"Failed to install dependencies:\n{err_msg}"))

def check_and_install_deps():
    try:
        for package in PACKAGES:
            __import__(package)
        return True
    except ImportError:
        add_site_packages_to_sys_path()  # Ensure site-packages is in sys.path
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