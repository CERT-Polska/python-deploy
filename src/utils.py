import logging
import subprocess
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

logger = logging.getLogger("python-deploy")

CallErrorFilter = Callable[[subprocess.CalledProcessError], bool]


class DeployError(RuntimeError):
    pass


def flatten(items: Sequence[Union[str, List[str]]]) -> List[str]:
    return [
        item
        for sublist in items
        for item in (sublist if isinstance(sublist, list) else [sublist])
    ]


def check_call(
    params: List[Union[str, List[str]]],
    input: Optional[bytes] = None,
    error_filter: Optional[CallErrorFilter] = None,
) -> bytes:
    try:
        args = flatten(params)
        logger.debug(f"> {' '.join(args)}")
        result = subprocess.check_output(args, input=input, stderr=subprocess.STDOUT)
        logger.debug(f"$ {result.decode()}")
        return result
    except subprocess.CalledProcessError as exc:
        if error_filter and error_filter(exc):
            return exc.output
        logger.error("Called process error:")
        logger.error(exc.output.decode())
        raise DeployError(f"Command {params[0]} failed.")


def get_dict_key(obj: Dict, key_path: str) -> Any:
    tokens = key_path.split(".")
    current = obj
    for level, key in enumerate(tokens):
        if key not in current:
            return None
        current = current[key]
    return current
