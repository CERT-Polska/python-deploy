"""
Types for docker/deploy.json files
"""

from typing import Dict, Literal, TypedDict, Union


class DockerSpec(TypedDict, total=False):
    image: str
    dockerfile: str
    dir: str


KubernetesSpec = TypedDict(
    "KubernetesSpec",
    {
        "namespace": str,
        "deployment": str,
        "cronjob": str,
        "container": str,
        "init-container": str,
        "configuration": str,
    },
    total=False,
)


DeployServiceSpec = TypedDict(
    "DeployServiceSpec",
    {
        "docker": DockerSpec,
        "k8s": KubernetesSpec,
        "k8s-staging": KubernetesSpec,
    },
    total=False,
)

DeploySpec = Dict[str, DeployServiceSpec]
KubernetesEnv = Union[Literal["k8s"], Literal["k8s-staging"]]
