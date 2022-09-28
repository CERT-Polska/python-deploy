import subprocess

from .utils import check_call


def has_git_repo() -> bool:
    proc = subprocess.Popen(
        ["git", "status"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc.communicate()
    return proc.returncode == 0


def is_clean_repo() -> bool:
    status = check_call(["git", "status", "--short"])
    return status.strip() == b""


def get_current_git_hash() -> str:
    return check_call(["git", "rev-parse", "HEAD"]).strip().decode("utf-8")
