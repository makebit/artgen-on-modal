import json
import subprocess
from pathlib import Path


import modal

PORT = 8000

with open(Path(__file__).parent / 'config.json', 'r') as file:
    config = json.load(file)

models = config["models"]
tokens = config["tokens"]

cache_vol = modal.Volume.from_name("cache", create_if_missing=True)
data_vol = modal.Volume.from_name("data", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install(
        "wget",
        "git",
        "libgl1",
        "libglib2.0-0",
        "google-perftools",  # For tcmalloc
    )
    .env({"LD_PRELOAD": "/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4"})
    .run_commands(
        "git clone --depth 1 --branch v1.10.1 https://github.com/AUTOMATIC1111/stable-diffusion-webui /webui",
        "git clone https://github.com/deforum-art/sd-webui-deforum /webui/extensions/deforum",
        "git clone https://github.com/Mikubill/sd-webui-controlnet.git /webui/extensions/sd-webui-controlnet",
        "python -m venv /webui/venv",
        "cd /webui && . venv/bin/activate && "
        + "python -c 'from modules import launch_utils; launch_utils.prepare_environment()' --xformers",
        gpu="L40S",
    )
    .run_commands(
        "cd /webui && . venv/bin/activate && "
        + "python -c 'from modules import shared_init, initialize; shared_init.initialize(); initialize.initialize()'",
        gpu="L40S",
    )
    # create folders for models
    .run_commands(
        "cd /webui/models && mkdir -p Stable-diffusion"
    )
    .run_commands(
        "echo \"default_output_dir = '/cache'\" >> /webui/modules/paths_internal.py"
    )
)

image = image.add_local_file(
    Path(__file__).parent / 'config.json', "/root/config.json",
    copy=True
)

def hf_download():
    from huggingface_hub import hf_hub_download

    for model in models['hf']:
        model_path = hf_hub_download(
            repo_type=model['repo_type'],
            repo_id=model['repo_id'],
            filename=model['filename'],
            cache_dir="/data",
        )

        subprocess.run(
            f"ln -s {model_path} /webui/models/Stable-diffusion/{model['filename'].split('/')[-1]}",
            shell=True,
            check=True,
        )

def civitai_download():
    for model in models['civitai']:
        subprocess.run(
            f"ln -s /data/{model['filename']} /webui/models/Stable-diffusion/{model['filename']}",
            shell=True,
            check=True,
        )

image = (
    image
    .pip_install("huggingface_hub[hf_transfer]==0.29.3")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        hf_download,
        volumes={"/data": data_vol},
    )
    .run_function(
        civitai_download,
        volumes={"/data": data_vol},
    )
)

app = modal.App("a1111-webui", image=image)


@app.function(
    gpu="L40S",
    cpu=2,
    memory=1024,
    timeout=120,
    # Allows 100 concurrent requests per container.
    allow_concurrent_inputs=100,
    # Keep at least one instance of the server running.
    min_containers=1,
    volumes={"/data": data_vol, "/cache": cache_vol},
)
@modal.web_server(port=PORT, startup_timeout=180)
def run():
    START_COMMAND = f"""
cd /webui && \
. venv/bin/activate && \
accelerate launch \
    --num_processes=1 \
    --num_machines=1 \
    --mixed_precision=fp16 \
    --dynamo_backend=inductor \
    --num_cpu_threads_per_process=6 \
    /webui/launch.py \
        --skip-prepare-environment \
        --no-gradio-queue \
        --listen \
        --port {PORT}
"""
    subprocess.Popen(START_COMMAND, shell=True)
