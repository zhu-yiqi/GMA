# GMA: General Mobile Assistant

GMA is an Android benchmark environment for mobile-agent evaluation. It provides Dockerized Android emulator environments, seeded mobile apps, task definitions, and an evaluation harness.

## What You Need

- Linux host with Docker installed
- Python 3.12
- Enough disk space for the Docker image and runtime containers
- The GMA source code from this repository
- The prepared Docker image archive from ModelScope: `StephenZhu0218/GMA`, file `gma-image.tar.gz`

## Install The Python Package

```bash
git clone git@github.com:zhu-yiqi/GMA.git
cd GMA

python3.12 -m venv .venv
source .venv/bin/activate
pip install uv
uv sync
```

## Download And Load The Docker Image

Download `gma-image.tar.gz` from the ModelScope repo `StephenZhu0218/GMA`. With the ModelScope CLI, one typical command is:

```bash
pip install modelscope
modelscope download --model StephenZhu0218/GMA gma-image.tar.gz --local_dir .
```

Then load the image into Docker:

```bash
docker load -i gma-image.tar.gz
docker images | grep gma
```

The expected image tag is:

```text
gma:ready
```

If Docker loads the image under a different tag, retag it:

```bash
docker tag <loaded-image-id-or-tag> gma:ready
```

## Start GMA Environments

Before starting containers, load the host kernel NAT/iptables modules. This is required because GMA containers use Docker-in-Docker and rely on host NAT routing support. Run this on the host after boot and before `gma env up`:

```bash
sudo modprobe ip_tables
sudo modprobe iptable_nat
sudo modprobe iptable_filter
```

If you are already root, omit `sudo`.

Start one environment:

```bash
./.venv/bin/gma env up --count 1 --image gma:ready
```

Start multiple environments:

```bash
./.venv/bin/gma env up --count 10 --image gma:ready
```

List running environments:

```bash
./.venv/bin/gma env list
```

By default, environment `N` uses:

- backend port: `8100 + N`, for example env 1 uses `http://localhost:8101`
- browser emulator view port: `5920 + N`, for example env 1 uses `http://localhost:5921/vnc.html`

Stop all GMA environments:

```bash
./.venv/bin/gma env down
```

## Run A Manual Task

List available tasks:

```bash
./.venv/bin/gma task list
```

Initialize a task in one environment and manually operate the emulator:

```bash
./.venv/bin/gma manual ElementXSendLongTimeNoSeeJordanTask --url http://localhost:8101
```

Inside the manual shell, use:

```text
eval      # evaluate current state
ask ...   # ask the simulated user if the task supports user interaction
quit      # run final evaluation and exit
```

## Run Evaluation

Start at least as many environments as the desired parallelism, then run evaluation with an OpenAI-compatible model endpoint:

```bash
./.venv/bin/gma eval \
  --agent-type basic_e2e \
  --model <model-name> \
  --base-url <openai-compatible-base-url> \
  --api-key <api-key> \
  --task ElementXSendLongTimeNoSeeJordanTask TravelReviewEmiratesSep30FlightTask \
  --max-steps 50 \
  --max-concurrency 2 \
  --log-dir logs/example_run \
  --no-evaluate-each-step
```

For a larger task set, pass more task names after `--task`, or omit `--task` to run all registered tasks. Logs and trajectories are written under `--log-dir`.

Useful options:

- `--max-steps`: maximum agent steps per task
- `--max-concurrency`: number of parallel tasks, bounded by running containers
- `--no-evaluate-each-step`: evaluate only after final answer or termination
- `--no-skip-finished`: rerun tasks that already have completed logs

## Annotation Server

The browser annotation interface can be started with:

```bash
./.venv/bin/gma annotate --help
```

Use the help output to choose the host, port, task source, and environment URLs for your annotation run.

## Notes

- Use the prepared image `gma:ready` for normal evaluation. It already contains the emulator state and backend baselines needed by the tasks.
- Containers must be started with `--privileged`; the `gma env up` command handles this.
- If an environment becomes unhealthy, restart it with `gma env down` / `gma env up`, or start a fresh container and point evaluation/manual commands to the new backend URL.
