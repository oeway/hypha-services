import subprocess
import sys


def pip_install(package):
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            package,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()

    if process.returncode != 0:
        raise Exception(
            f"Failed to install package {package}. {stderr.decode().strip()}"
        )

    print(stdout.decode().strip())
    print(f"Successfully installed package {package}")
