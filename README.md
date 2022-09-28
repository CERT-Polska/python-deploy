# deploy

Build, push and deploy k8s services with single deploy.json file to provide common convention for
multiple production services.

```
pip install python-deploy
```

### Make your Docker setup deploy-enabled

First of all, create a file under `deploy/deploy.json` path pointing at your Dockerfile. 

> It's recommended to place your Dockerfile in a `deploy/docker` subdirectory.

```json
{
    "fancy-service": {
        "docker": {
            "image": "certpl/fancy-service",
            "dockerfile": "deploy/docker/Dockerfile",
            "dir": "."
        }
    }
}
```

Then you can use `deploy build` to build your Docker image. Your image will be tagged using Git commit hash.

```
$ deploy build
[INFO] Building image for fancy-service
[INFO] Building certpl/fancy-service:cb85eb9d38c407e462a6681351dfd36331635329
```

If you want to provide alternative version tag, use `--version`. You can provide any tag you want, but few of them are special:
- `date` uses current timestamp (e.g. `v20200302170007`)
- `commit` is default
- other strings are used "as is"

Use `deploy push` if you want to push (and build) image to Docker Registry or Docker Hub with all provided tags:

```
$ deploy push
[INFO] Building image for fancy-service
[INFO] Building certpl/fancy-service:cb85eb9d38c407e462a6681351dfd36331635329
[INFO] Pushing image for fancy-service
[INFO] Pushing certpl/fancy-service:7f6dd7010dba1ffdaeb32875e0f71c30c9810df7
```

### Make your k8s deployment deploy-enabled

Enhance your `deploy/deploy.json` with configuration of k8s deployment. 

Deploy supports two environments: `k8s` (production) and `k8s-staging` (staging).

A complete example of a `deploy.json` file is presented below:

```
{
    "fancy-service": {
        "docker": {
            "image": "certpl/fancy-service",
            "dockerfile": "deploy/docker/Dockerfile",
            "dir": "."
        },
        "k8s": {
            "namespace": "service-prod",
            "deployment": "deployment-fancy-service",
            "container": "container-fancy-service"
        },
        "k8s-staging": {
            "namespace": "service-st",
            "deployment": "deployment-fancy-service",
            "container": "container-fancy-service"
        }
    }
}
```

Starting from v4.0.0 you can provide `cronjob` instead of `deployment`. `init-container` is also supported if it uses
the same image.

> It's recommended to place your Kubernetes configuration files in the `deploy/k8s` and `deploy/k8s-staging` subdirectories.

This enables you to use `deploy staging` and `deploy production` commands.

- `deploy staging` builds and pushes Docker image with version tag and `latest` tag. After all, updates the image name used by staging container 
to new version.

- `deploy production` does the same thing, but images are additionally tagged  as `master`. Then it updates the production container.

```
$ deploy production
[INFO] Building image for fancy-service
[INFO] Building certpl/fancy-service:cb85eb9d38c407e462a6681351dfd36331635329
[INFO] Pushing image for fancy-service
[INFO] Pushing certpl/fancy-service:7f6dd7010dba1ffdaeb32875e0f71c30c9810df7
[INFO] Deploying image to k8s
[INFO] Tagging certpl/fancy-service:e12840da50a9426b36de7c0be6dc553cde9923e8 as certpl/fancy-service::latest
[INFO] Pushing certpl/fancy-service:latest
```

If you don't want to rebuild your Docker images and need just to pull them from the Docker Registry, you can use
`deploy pull` and `deploy production --deploy-only` switch

```
$ docker pull
[INFO] Pulling image for fancy-service
[INFO] Pulling certpl/fancy-service:7f6dd7010dba1ffdaeb32875e0f71c30c9810df7
$ deploy production --deploy-only
[INFO] Deploying image to k8s
[INFO] Tagging certpl/fancy-service:e12840da50a9426b36de7c0be6dc553cde9923e8 as certpl/fancy-service::latest
[INFO] Pushing certpl/fancy-service:latest
```

### Support for multiple services

If your app is built using multiple containers, just specify more services as top-level keys of `deploy.json`.

```json
{
    "fancy-service": {
        ...
    },
    "fancy-service-web": {
        ...
    }
}
```

Deploy will build, push and deploy them all (unless you explicitly select services using `--service/-s` option).

### Make your Gitlab CI deploy-enabled

You can automate all these steps with CI/CD. Example `.gitlab-ci.yml` file is presented below:

```yaml
image: certpl/deploy:v4.0.0

services:
  - docker:dind

stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - git submodule init
    - git submodule update --recursive
    # Build and push images to Docker Registry
    - deploy push

test:
  stage: test
  script:
    # Pull images and run unit tests
    - deploy pull
    - deploy run -- python -m unittest discover

deploy:
  stage: deploy
  only:
  - master
  script:
    # Set default token, pull images and deploy them
    - kubernetes_use_token https://kapi.example.com "$KUBE_TOKEN"
    - deploy pull
    - deploy production --deploy-only
```

If you don't have tests and you just want to build and deploy everything in one step: invoke `deploy production`

### Full usage

Keep in mind that some optional arguments are only relevant for some commands

```
usage: deploy [-h] {build,push,pull,staging,production,image,run} ...

Deploy the application.

positional arguments:
  {build,push,pull,staging,production,image,run}
                        Deploy commands
    build               Only build images
    push                Build and push images
    pull                Pull images from registry
    staging             Build, push and deploy images to the staging
                        environment
    production          Build, push and deploy images to the PRODUCTION
                        environment
    image               Show image names
    run                 Run interactive command for service images

optional arguments:
  -h, --help            show this help message and exit

  --tag TAG, -t TAG     Alternative tags for image
  --no-cache            Pass --no-cache to docker build
  --service SERVICE, -s SERVICE
                        Specify services to perform action (default: all)
  --force, -f           Don't perform check-ups, force deploy (not
                        recommended)
  --verbose, -v         Print spawned subcommands and their outputs
  --version {commit,date,latest}
                        Alternative version tag
```
