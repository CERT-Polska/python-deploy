#!/usr/bin/python3

import argparse
import json
import logging
import os
import pathlib
import subprocess
from datetime import datetime
from typing import List, Optional

from .docker import run_image_command
from .git import get_current_git_hash, has_git_repo, is_clean_repo
from .schema import KubernetesEnv
from .services import DeployService, DeployServiceSet
from .utils import DeployError, logger


def load_deploy_json(load_only: Optional[List[str]] = None) -> DeployServiceSet:
    deploy_path = pathlib.Path("deploy/deploy.json")
    if not deploy_path.is_file():
        raise DeployError(
            "Configuration file deploy/deploy.json not found. " "Check your CWD."
        )
    deploy_json = deploy_path.read_text()
    return DeployServiceSet(json.loads(deploy_json), load_only=load_only)


def get_version_tag(source: str, check_dirty: bool = True) -> str:
    if check_dirty:
        if not has_git_repo():
            raise DeployError(
                "There is no Git repository available. "
                "Use --force if you don't care about it"
            )
        if not is_clean_repo():
            raise DeployError(
                "Git repository is dirty. Commit your changes "
                "or use --force if you don't care about it"
            )
    else:
        logger.warning("Used --force. Git won't be checked.")
    if source == "commit":
        try:
            return get_current_git_hash()
        except subprocess.CalledProcessError:
            ci_commit_sha = os.getenv("CI_COMMIT_SHA")
            if ci_commit_sha:
                logger.warning(
                    "Can't determine commit hash: "
                    "getting version from $CI_COMMIT_SHA."
                )
                return ci_commit_sha
            else:
                raise DeployError(
                    "Can't determine commit hash. Use alternative " "--version variant."
                )
    elif source == "date":
        return datetime.utcnow().strftime("v%Y%m%d%H%M%S")
    else:
        return source


class Deploy(object):
    def __init__(self, args):
        self.args = args
        self.config = load_deploy_json(load_only=self.args.service)
        if self.args.service:
            for srv in self.args.service:
                if srv not in self.config.services.keys():
                    raise DeployError(f"Unknown service: {srv}")
        self.version_tag: str = get_version_tag(
            self.args.version, check_dirty=not self.args.force
        )

    def build(self) -> None:
        extra_tags = self.args.tag or []
        for service in self.config.get_services():
            logger.info(f"Building image for {service.service_name}")
            service.build_docker([self.version_tag] + extra_tags, self.args.no_cache)

    def push(self) -> None:
        self.build()
        extra_tags = self.args.tag or []
        for service in self.config.get_services():
            logger.info(f"Pushing image for {service.service_name}")
            service.push_docker([self.version_tag] + extra_tags)

    def pull(self) -> None:
        for service in self.config.get_services():
            logger.info(f"Pulling image for {service.service_name}")
            service.pull_docker([self.version_tag])

    def _validate(self, service: DeployService, environment: KubernetesEnv) -> None:
        diff = service.diff_k8s_config(self.version_tag, environment)
        if diff:
            logger.info(f"Found difference for {service.service_name}")
            print(diff)
        else:
            logger.info(f"No changes found for {service.service_name}")

    def _deploy(self, service: DeployService, environment: KubernetesEnv) -> None:
        if environment == "k8s":
            service.tag_docker(self.version_tag, ["master", "latest"])
        else:
            service.tag_docker(self.version_tag, ["latest"])
        service.apply_k8s_config(self.version_tag, environment)

    def production(self) -> None:
        for service in self.config.get_services():
            if self.args.validate:
                self._validate(service, "k8s")
                continue
            if not self.args.deploy_only:
                self.push()
            logger.info(f"Deploying {service.service_name} to k8s")
            self._deploy(service, "k8s")

    def staging(self) -> None:
        for service in self.config.get_services():
            if self.args.validate:
                self._validate(service, "k8s-staging")
                continue
            if not self.args.deploy_only:
                self.push()
            logger.info(f"Deploying {service.service_name} to k8s-staging")
            self._deploy(service, "k8s-staging")

    def image(self) -> None:
        for service in self.config.get_services():
            version_tag = service.get_docker_tags([self.version_tag])[0]
            print(version_tag)

    def run(self) -> None:
        for service in self.config.get_services():
            version_tag = service.get_docker_tags([self.version_tag])[0]
            run_image_command(version_tag, self.args.cmd)

    def list(self) -> None:
        for service in self.config.get_services():
            print(f"{service.service_name} ({','.join(service.spec.keys())})")

    def perform(self) -> None:
        getattr(self, self.args.command)()


def main():
    parser = argparse.ArgumentParser(description="Deploy the application.")

    service_subparser = argparse.ArgumentParser(add_help=False)
    service_subparser.add_argument(
        "--service",
        "-s",
        action="append",
        help="Specify services to perform action (default: all)",
    )
    service_subparser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Don't perform check-ups, force deploy (not recommended)",
    )
    service_subparser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print spawned subcommands and their outputs",
    )
    service_subparser.add_argument(
        "--version",
        help="Alternative version tag ('commit', 'date' or custom)",
        default="commit",
        type=str,
    )

    build_subparser = argparse.ArgumentParser(add_help=False)
    build_subparser.add_argument(
        "--tag", "-t", action="append", help="Alternative tags for image"
    )
    build_subparser.add_argument(
        "--no-cache",
        action="store_true",
        help="Pass --no-cache to docker build",
    )

    deploy_subparser = argparse.ArgumentParser(add_help=False)
    deploy_subparser.add_argument(
        "--deploy-only",
        action="store_true",
        help="Don't build and push, just apply k8s configuration",
    )
    deploy_subparser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate k8s configuration and show 'kubectl diff' output",
    )

    commands = parser.add_subparsers(help="Deploy commands", dest="command")
    commands.required = True
    commands.add_parser(
        "build",
        parents=[build_subparser, service_subparser],
        help="Only build images",
    )
    commands.add_parser(
        "push",
        parents=[build_subparser, service_subparser],
        help="Build and push images",
    )
    commands.add_parser(
        "pull", parents=[service_subparser], help="Pull images from registry"
    )
    commands.add_parser(
        "staging",
        parents=[build_subparser, service_subparser, deploy_subparser],
        help="Build, push and deploy images to the staging environment",
    )
    commands.add_parser(
        "production",
        parents=[build_subparser, service_subparser, deploy_subparser],
        help="Build, push and deploy images to the PRODUCTION environment",
    )
    commands.add_parser("image", parents=[service_subparser], help="Show image names")
    run_command = commands.add_parser(
        "run",
        parents=[service_subparser],
        help="Run interactive command for service images",
    )
    run_command.add_argument("cmd", nargs="*")
    commands.add_parser(
        "list", parents=[service_subparser], help="List available services"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )
    try:
        Deploy(args).perform()
    except DeployError as e:
        raise SystemExit(f"[!] {e.args[0]}")


if __name__ == "__main__":
    main()
