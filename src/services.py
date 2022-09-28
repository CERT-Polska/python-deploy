import copy
import pathlib
from typing import Dict, List, Optional

import yaml

from .docker import build_image, pull_image, push_image, tag_image
from .k8s import apply_k8s_configuration, diff_k8s_configuration
from .schema import DeployServiceSpec, DeploySpec, KubernetesEnv, KubernetesSpec
from .utils import DeployError, get_dict_key


class DeployK8S:
    def __init__(
        self, spec: KubernetesSpec, environment: KubernetesEnv, service_name: str
    ) -> None:
        self.spec = spec
        self.environment = environment
        self.service_name = service_name
        self.config_path = self.get_config_path()
        self.config = self.load_config(self.config_path)

    def get_config_path(self) -> pathlib.Path:
        if "configuration" in self.spec:
            return pathlib.Path(self.spec["configuration"])
        if self.environment == "k8s-staging":
            environment_dir = "k8s-st"
        else:
            environment_dir = "k8s"
        return pathlib.Path(f"deploy/{environment_dir}/{self.service_name}.yml")

    def load_config(self, config_path: pathlib.Path) -> List[Dict]:
        if not config_path.exists():
            raise DeployError(
                f"Configuration file {config_path.as_posix()} not found. "
                f"Check whether deploy/deploy.json is configured properly."
            )
        with config_path.open("r") as f:
            return list(yaml.safe_load_all(f))

    def get_service_config(self, k8s_config: List[Dict]) -> Dict:
        """
        Returns config that matches deployment/cronjob
        """
        if "deployment" in self.spec:
            kind = "deployment"
            name = self.spec["deployment"]
        elif "cronjob" in self.spec:
            kind = "cronjob"
            name = self.spec["cronjob"]
        else:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"'deployment' or 'cronjob' must be specified."
            )

        for svc_config in k8s_config:
            svc_kind = svc_config.get("kind")
            if not svc_kind or svc_kind.lower() != kind:
                continue
            metadata = svc_config.get("metadata", {})
            if metadata.get("name") == name:
                break
        else:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"{kind}/{name} not found in {self.config_path.as_posix()}."
            )

        namespace = self.spec.get("namespace")
        if not namespace:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"'namespace' must be specified."
            )

        if metadata.get("namespace") != namespace:
            raise DeployError(
                f"Kubernetes configuration file doesn't apply to the namespace "
                f"provided in deploy/deploy.json (expected: {namespace}, "
                f"found: {metadata.get('namespace')})"
            )
        return svc_config

    def get_from_template_spec(self, service_config: Dict, key: str) -> Dict:
        if service_config["kind"].lower() == "deployment":
            path = "spec.template.spec." + key
        elif service_config["kind"].lower() == "cronjob":
            path = "spec.jobTemplate.spec.template.spec." + key
        else:
            raise NotImplementedError
        spec = get_dict_key(service_config, path)
        if not spec:
            raise DeployError(
                f"Missing key {path} in " f"Kubernetes configuration file."
            )
        return spec

    def get_container_spec(self, service_config: Dict) -> Dict:
        if "container" not in self.spec:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"'container' must be specified."
            )
        container_name = self.spec["container"]
        containers = self.get_from_template_spec(service_config, "containers")
        for container in containers:
            if container.get("name") == container_name:
                return container
        else:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"container {container_name} not found in "
                f"{self.config_path.as_posix()}."
            )

    def get_init_container_spec(self, service_config: Dict) -> Optional[Dict]:
        if "init-container" not in self.spec:
            return None
        init_container_name = self.spec["init-container"]
        containers = self.get_from_template_spec(service_config, "initContainers")
        for container in containers:
            if container.get("name") == init_container_name:
                return container
        else:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"init container {init_container_name} not found "
                f"in {self.config_path.as_posix()}."
            )

    def _set_image_tag(self, container_config: Dict, image: str) -> None:
        if "image" not in container_config:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"container doesn't have 'image' specified "
                f"in {self.config_path.as_posix()}."
            )
        container_image_name, container_tag = container_config["image"].split(":")
        image_name, tag = image.split(":")
        if container_image_name != image_name:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"container image doesn't match with '{image_name}' "
                f"(found '{container_image_name}' specified "
                f"in {self.config_path.as_posix()})."
            )
        container_config["image"] = image

    def set_image_tag(self, image: str) -> List[Dict]:
        k8s_config = copy.deepcopy(self.config)
        service_config = self.get_service_config(k8s_config)
        container = self.get_container_spec(service_config)
        self._set_image_tag(container, image)
        init_container = self.get_init_container_spec(service_config)
        if init_container:
            self._set_image_tag(init_container, image)
        return k8s_config


class DeployService:
    def __init__(self, spec: DeployServiceSpec, service_name: str) -> None:
        self.service_name = service_name
        self.spec = spec
        self.docker_spec = spec.get("docker")
        self.k8s_spec = spec.get("k8s")
        self.k8s_staging_spec = spec.get("k8s-staging")

    def get_docker_tags(self, tags: List[str]) -> List[str]:
        if not self.docker_spec:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"Missing docker image specification."
            )
        if "image" not in self.docker_spec:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"'docker.image' must be specified."
            )
        return [
            tag if ":" in tag else f'{self.docker_spec["image"]}:{tag}' for tag in tags
        ]

    def build_docker(self, tags: List[str], no_cache: bool = False) -> None:
        if not self.docker_spec:
            raise DeployError(
                f"Invalid specification of {self.service_name}. "
                f"Missing docker image specification."
            )
        dockerfile = self.docker_spec.get("dockerfile", "./Dockerfile")
        context_dir = self.docker_spec.get("dir", ".")
        build_image(dockerfile, context_dir, self.get_docker_tags(tags), no_cache)

    def push_docker(self, tags: List[str]) -> None:
        for tag in self.get_docker_tags(tags):
            push_image(tag)

    def tag_docker(self, existing_tag: str, tags: List[str]) -> None:
        existing_docker_tag = self.get_docker_tags([existing_tag])[0]
        for tag in self.get_docker_tags(tags):
            tag_image(existing_docker_tag, tag, push=True)

    def pull_docker(self, tags: List[str]) -> None:
        for tag in self.get_docker_tags(tags):
            pull_image(tag)

    def get_k8s(self, environment: KubernetesEnv) -> DeployK8S:
        if environment == "k8s":
            if not self.k8s_spec:
                raise DeployError(
                    f"Invalid specification of {self.service_name}. "
                    f"Missing k8s specification."
                )
            k8s = DeployK8S(self.k8s_spec, "k8s", service_name=self.service_name)
        elif environment == "k8s-staging":
            if not self.k8s_staging_spec:
                raise DeployError(
                    f"Invalid specification of {self.service_name}. "
                    f"Missing k8s-staging specification."
                )
            k8s = DeployK8S(
                self.k8s_staging_spec, "k8s-staging", service_name=self.service_name
            )
        else:
            raise NotImplementedError
        return k8s

    def apply_k8s_config(self, tag: str, environment: KubernetesEnv) -> None:
        image = self.get_docker_tags([tag])[0]
        k8s = self.get_k8s(environment)
        patched_config = k8s.set_image_tag(image)
        apply_k8s_configuration(patched_config, k8s.spec["namespace"])

    def diff_k8s_config(self, tag: str, environment: KubernetesEnv) -> str:
        image = self.get_docker_tags([tag])[0]
        k8s = self.get_k8s(environment)
        patched_config = k8s.set_image_tag(image)
        return diff_k8s_configuration(patched_config, k8s.spec["namespace"])


class DeployServiceSet:
    def __init__(self, spec: DeploySpec, load_only: Optional[List[str]] = None) -> None:
        self.spec = spec
        self.services = {
            service_name: DeployService(service_spec, service_name=service_name)
            for service_name, service_spec in spec.items()
            if not load_only or service_name in load_only
        }

    def get_services(self) -> List[DeployService]:
        return list(self.services.values())
