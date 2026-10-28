# import sys
# import subprocess
# import os
# import glob
# from aqt import mw
# from aqt.utils import showInfo, showWarning, askUser
# from .constants import MENU_NAME

# PACKAGES = ["numpy", "scipy", "sklearn", "fastcluster"] # List of required packages
# REQUIRED = {
#     "numpy": "numpy",
#     "scipy": "scipy",
#     "sklearn": "scikit-learn",
#     "fastcluster": "fastcluster",
# }

# def get_anki_venv_site_packages():
#     if sys.platform == "win32" or sys.platform == "cygwin":  # Windows
#         local_app_data = os.environ.get("LOCALAPPDATA", "")
#         path = os.path.join(local_app_data, "AnkiProgramFiles", ".venv", "Lib", "site-packages")
#         return path if os.path.exists(path) else None
#     elif sys.platform == "darwin": # macOS
#         base_dir = os.path.expanduser("~/Library/Application Support/AnkiProgramFiles/.venv")
#         # Match lib/python3.x/site-packages regardless of exact minor version
#         matches = glob.glob(os.path.join(base_dir, "lib", "python*", "site-packages"))
#         return matches[0] if matches else None 
#     else: # Linux
#         base_dir = os.path.expanduser("~/.local/share/AnkiProgramFiles/.venv")
#         matches = glob.glob(os.path.join(base_dir, "lib", "python*", "site-packages"))
#         return matches[0] if matches else None

# def add_site_packages_to_sys_path():
#     site_packages_dir = get_anki_venv_site_packages()
#     if site_packages_dir and site_packages_dir not in sys.path:
#         sys.path.insert(0, site_packages_dir)

# def get_anki_venv_python():
#     if sys.platform == "win32" or sys.platform == "cygwin":  # Windows
#         local_app_data = os.environ.get("LOCALAPPDATA")
#         print(f"Local App Data: {local_app_data}")
#         return os.path.join(local_app_data, "AnkiProgramFiles", ".venv", "Scripts", "python.exe")
#     elif sys.platform == "darwin":  # macOS
#         return os.path.expanduser("~/Library/Application Support/AnkiProgramFiles/.venv/bin/python")
#     else:  # Linux
#         return os.path.expanduser("~/.local/share/AnkiProgramFiles/.venv/bin/python")

# # Package versions: {'numpy': '2.3.4', 'scipy': '1.16.3', 'sklearn': '1.7.2', 'fastcluster': '1.3.0'}
# def print_package_versions():
#     versions = {}
#     for package in PACKAGES:
#         try:
#             module = __import__(package)
#             versions[package] = module.__version__
#         except ImportError:
#             versions[package] = "Not installed"
#     print("Package versions:", versions)
#     return versions

# def is_valid_python_runner(exe_path):
#     if not exe_path or not os.path.exists(exe_path):
#         return False
#     try:
#         res = subprocess.run([exe_path, "-c", "import pip"], capture_output=True, timeout=5, text=True)
#         return res.returncode == 0
#     except Exception:
#         return False

# def install_deps():
#     candidates = []
#     if sys.executable:
#         candidates.append(sys.executable)

#     venv_python = get_anki_venv_python()
#     if venv_python and venv_python not in candidates:
#         candidates.append(venv_python)

#     errors = []
#     for exe in candidates:
#         if not is_valid_python_runner(exe):
#             errors.append(f"[{exe}] Invalid or missing pip support.")
#             continue

#         cmd = [exe, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir"] + list(REQUIRED.values())

#         try:
#             subprocess.run(cmd, check=True, capture_output=True, text=True)
#             mw.taskman.run_on_main(lambda: showInfo("Dependencies installed successfully. Please restart Anki."))
#             return
#         except subprocess.CalledProcessError as e:
#             errors.append(f"[{exe}] Failed:\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")
#         except Exception as e:
#             errors.append(f"[{exe}] Error: {str(e)}")
            
#     err_msg = "\n\n".join(errors)
#     mw.taskman.run_on_main(lambda: showWarning(f"Failed to install dependencies:\n{err_msg}"))

# def check_and_install_deps():
#     try:
#         for package in PACKAGES:
#             __import__(package)
#         return True
#     except ImportError:
#         add_site_packages_to_sys_path()  # Ensure site-packages is in sys.path
#         try:
#             for package in PACKAGES:
#                 __import__(package)
#             return True
#         except ImportError:
#             msg = (
#                 f"The '{MENU_NAME}' add-on requires:\n\n{', '.join(PACKAGES)}\n\n"
#                 "Install now? (Anki may freeze briefly)"
#             )
#             if not askUser(msg):
#                 showWarning("Installation canceled.")
#                 return False
#             mw.progress.start(label="Installing dependencies...", immediate=True)
#             mw.taskman.run_in_background(install_deps, lambda _: mw.progress.finish())
#             return False


import sys
import os
import json
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
import importlib
import platform
import sysconfig
import re
from pathlib import Path

from aqt import mw
from aqt.utils import showInfo, showWarning, askUser
from .constants import MENU_NAME

from .vendor.packaging.tags import sys_tags
from .vendor.packaging.utils import parse_wheel_filename


# Pin an entire compatible dependency set.
# These are initial pins, not a fully platform-tested lockfile.
REQUIRED = {
    "numpy": "2.3.4",
    "scipy": "1.16.3",
    "scikit-learn": "1.7.2",
    "fastcluster": "1.3.0",
    "joblib": "1.5.2",
    "threadpoolctl": "3.6.0",
}

IMPORT_NAMES = {
    "numpy": "numpy",
    "scipy": "scipy",
    "scikit-learn": "sklearn",
    "fastcluster": "fastcluster",
    "joblib": "joblib",
    "threadpoolctl": "threadpoolctl",
}

PACKAGES = ["numpy", "scipy", "sklearn", "fastcluster"]

ADDON_DIR = Path(__file__).resolve().parent


def get_runtime_key():
    """Separate native packages by Anki's Python ABI and platform."""
    values = (
        sys.implementation.cache_tag,
        sysconfig.get_config_var("SOABI") or "unknown",
        sysconfig.get_platform(),
        platform.machine(),
    )
    return re.sub(
        r"[^A-Za-z0-9_.-]", "_",
        "-".join(values),
    )


PACKAGE_DIR = (
    ADDON_DIR / "user_files" / "dependencies" / get_runtime_key()
)

MARKER_FILE = PACKAGE_DIR / ".installed.json"


def add_site_packages_to_sys_path():
    """Allow Anki to import packages installed by this add-on."""
    if PACKAGE_DIR.is_dir():
        path = str(PACKAGE_DIR)
        if path not in sys.path:
            sys.path.insert(0, path)
        importlib.invalidate_caches()


def installation_is_current():
    """Require exactly the dependency set expected by this version."""
    if not MARKER_FILE.is_file():
        return False

    try:
        saved = json.loads(MARKER_FILE.read_text("utf-8"))
        return saved == REQUIRED
    except (OSError, ValueError):
        return False


def print_package_versions():
    add_site_packages_to_sys_path()
    versions = {}

    for name in PACKAGES:
        try:
            module = importlib.import_module(name)
            versions[name] = getattr(
                module, "__version__", "Unknown"
            )
        except (ImportError, OSError):
            versions[name] = "Not available"

    print("Package versions:", versions)
    return versions


def select_wheel(package, version, compatible_tags):
    """
    Find a wheel matching the actual Anki Python ABI and platform.
    No source distributions are considered.
    """
    url = (
        f"https://pypi.org/pypi/{package}/{version}/json"
    )

    with urllib.request.urlopen(url, timeout=30) as response:
        metadata = json.load(response)

    candidates = []

    for file in metadata["urls"]:
        filename = file["filename"]

        if file.get("packagetype") != "bdist_wheel":
            continue

        try:
            _, _, _, wheel_tags = parse_wheel_filename(filename)
        except ValueError:
            continue

        # Earlier entries in sys_tags() have higher priority.
        rank = min(
            (
                compatible_tags[tag]
                for tag in wheel_tags
                if tag in compatible_tags
            ),
            default=None,
        )

        if rank is not None:
            candidates.append((rank, file))

    if not candidates:
        raise RuntimeError(
            f"No compatible binary wheel found for "
            f"{package}=={version}.\n"
            f"Python: {sys.version.split()[0]}\n"
            f"Platform: {sysconfig.get_platform()}\n"
            f"ABI: {sysconfig.get_config_var('SOABI')}"
        )

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def download_wheel(file_info, destination):
    """Download and SHA-256 verify a PyPI wheel."""
    url = file_info["url"]
    expected_hash = file_info["digests"]["sha256"]

    digest = hashlib.sha256()

    with urllib.request.urlopen(url, timeout=120) as response:
        with open(destination, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)

                if not chunk:
                    break

                digest.update(chunk)
                output.write(chunk)

    if digest.hexdigest().lower() != expected_hash.lower():
        raise RuntimeError(
            f"SHA-256 verification failed for {file_info['filename']}"
        )


def extract_wheel(wheel_path, target):
    """
    Extract wheel contents into an isolated target directory.

    Handles root, purelib and platlib content. Other wheel
    installation schemes are intentionally rejected.
    """
    target = target.resolve()

    with zipfile.ZipFile(wheel_path) as archive:
        entries = archive.infolist()

        # Validate the entire archive before extracting anything.
        planned = []

        for entry in entries:
            if entry.is_dir():
                continue

            name = entry.filename.replace("\\", "/")
            parts = name.split("/")

            if (
                not parts
                or any(part in ("", ".", "..") for part in parts)
                or name.startswith("/")
                or ":" in parts[0]
            ):
                raise RuntimeError(f"Unsafe wheel path: {name}")

            # Reject symbolic links.
            mode = (entry.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise RuntimeError(f"Wheel contains symlink: {name}")

            if ".data" in parts[0] and parts[0].endswith(".data"):
                if len(parts) < 3:
                    raise RuntimeError(f"Invalid wheel data path: {name}")

                scheme = parts[1]

                if scheme not in ("purelib", "platlib"):
                    raise RuntimeError(
                        f"Unsupported wheel installation scheme: {scheme}"
                    )

                relative = Path(*parts[2:])
            else:
                relative = Path(*parts)

            destination = (target / relative).resolve()

            if not destination.is_relative_to(target):
                raise RuntimeError(f"Unsafe extraction target: {name}")

            planned.append((entry, destination))

        for entry, destination in planned:
            destination.parent.mkdir(parents=True, exist_ok=True)

            with archive.open(entry) as source:
                with open(destination, "wb") as output:
                    shutil.copyfileobj(source, output)


def install_deps():
    """
    Background worker.

    Downloads binary wheels from PyPI without executing pip,
    Anki.exe, or any other Python interpreter.
    """
    parent = PACKAGE_DIR.parent
    parent.mkdir(parents=True, exist_ok=True)

    staging = Path(
        tempfile.mkdtemp(prefix="anki-deps-", dir=parent)
    )

    try:
        # Use packaging's ordering of valid Python/platform tags.
        compatible_tags = {
            tag: index
            for index, tag in enumerate(sys_tags())
        }

        with tempfile.TemporaryDirectory() as download_dir:
            for package, version in REQUIRED.items():
                wheel_info = select_wheel(
                    package, version, compatible_tags
                )

                wheel_path = (
                    Path(download_dir) / wheel_info["filename"]
                )

                download_wheel(wheel_info, wheel_path)
                extract_wheel(wheel_path, staging)

        # All downloads and extractions succeeded.
        (staging / ".installed.json").write_text(
            json.dumps(REQUIRED, indent=2),
            encoding="utf-8",
        )

        backup = parent / (PACKAGE_DIR.name + ".backup")

        if backup.exists():
            shutil.rmtree(backup)

        if PACKAGE_DIR.exists():
            PACKAGE_DIR.rename(backup)

        try:
            staging.rename(PACKAGE_DIR)
        except Exception:
            if backup.exists():
                backup.rename(PACKAGE_DIR)
            raise

        if backup.exists():
            shutil.rmtree(backup)

        return True, (
            "Dependencies installed successfully.\n\n"
            "Please restart Anki."
        )

    except Exception as exc:
        return False, (
            f"Dependency installation failed:\n\n{exc}"
        )

    finally:
        if staging.exists():
            shutil.rmtree(staging)


def check_and_install_deps():
    add_site_packages_to_sys_path()

    missing = []

    for package, import_name in IMPORT_NAMES.items():
        try:
            importlib.import_module(import_name)
        except (ImportError, OSError):
            missing.append(package)

    if not missing and installation_is_current():
        return True

    message = (
        f"The '{MENU_NAME}' add-on requires scientific "
        "Python dependencies.\n\n"
        f"Missing/unavailable: {', '.join(missing) or 'None'}\n\n"
        "Install the required precompiled packages now?\n\n"
        "Anki may be temporarily unresponsive."
    )

    if not askUser(message):
        return False

    mw.progress.start(
        label="Installing dependencies...",
        immediate=True,
    )

    def finished(future):
        mw.progress.finish()

        try:
            success, message = future.result()
        except Exception as exc:
            success, message = False, str(exc)

        if success:
            showInfo(message)
        else:
            showWarning(message)

    mw.taskman.run_in_background(install_deps, finished)

    return False
