from typing import List

from .utils import check_call, flatten


def tag_docker_image(existing_image: str, new_tag: str, push: bool = False) -> None:
    check_call(["docker", "tag", existing_image, new_tag])
    if push:
        push_image(new_tag)


def build_image(
    dockerfile: str, context_dir: str, tags: List[str], no_cache: bool
) -> None:
    check_call(
        [
            "docker",
            "image",
            "build",
            context_dir,
            flatten([["-t", tag] for tag in tags]),
            "-f",
            dockerfile,
            ["--no-cache"] if no_cache else [],
        ]
    )


def push_image(tag: str) -> None:
    check_call(["docker", "image", "push", tag])


def pull_image(tag: str) -> None:
    check_call(["docker", "image", "pull", tag])


def run_image_command(tag: str, params: List[str]) -> None:
    check_call(["docker", "run", tag, params])
