import subprocess
from typing import Dict, List

import yaml

from .utils import check_call


def diff_k8s_configuration(k8s_config: List[Dict], namespace: str) -> str:
    def error_filter(exc: subprocess.CalledProcessError):
        return exc.returncode in [0, 1]

    return check_call(
        ["kubectl", "diff", "--namespace", namespace, "-f", "-"],
        input=yaml.dump_all(k8s_config, encoding="utf-8"),
        error_filter=error_filter,
    ).decode()


def apply_k8s_configuration(k8s_config: List[Dict], namespace: str) -> bytes:
    return check_call(
        ["kubectl", "apply", "--namespace", namespace, "-f", "-"],
        input=yaml.dump_all(k8s_config, encoding="utf-8"),
    )


def set_current_image(namespace: str, object: str, container: str, image: str) -> None:
    check_call(
        [
            "kubectl",
            "set",
            "image",
            "--namespace",
            namespace,
            object,
            f"{container}={image}",
        ]
    )


def get_current_image(namespace: str, container: str) -> str:
    jsonpath = f'{{..containers[?(@.name=="{container}")].image}}'

    return check_call(
        [
            "kubectl",
            "get",
            "deployment",
            "--namespace",
            namespace,
            f"-o=jsonpath={jsonpath}",
        ]
    ).decode()


def get_k8s_namespaces() -> List[str]:
    ns_bytes = check_call(["kubectl", "get", "namespaces"])
    ns_text = ns_bytes.decode("utf-8")
    namespaces = []
    for line in ns_text.split("\n")[1:]:
        if not line.strip():
            continue
        namespaces.append(line.split()[0])
    return namespaces
