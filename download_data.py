import json
import subprocess
import uuid
from pathlib import Path
from typing import Dict

import modal


with open(Path(__file__).parent / 'config.json', 'r') as file:
    config = json.load(file)

models = config["models"]
tokens = config["tokens"]

data_vol = modal.Volume.from_name("data", create_if_missing=True)

image = (
    modal.Image.debian_slim(
        python_version="3.12"
    )
    .apt_install(["git"])
    .pip_install("comfy-cli==1.3.8")
    .pip_install("huggingface_hub[hf_transfer]==0.29.3")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_commands(
        "comfy --skip-prompt install --nvidia --version 0.3.26"
    )
)

image = image.add_local_file(
    Path(__file__).parent / 'config.json', "/root/config.json",
    copy=True,
)

def hf_download():
    from huggingface_hub import hf_hub_download

    for model in models['hf']:
        model_path = hf_hub_download(
            repo_type=model['repo_type'],
            repo_id=model['repo_id'],
            filename=model['filename'],
            cache_dir="/cache",
        )

def civitai_download():
    for model in models['civitai']:
        subprocess.run(
            f"comfy --skip-prompt model download --url {model['url']} --set-civitai-api-token={tokens['civitai']} --relative-path /data",
            shell=True,
            check=True,
        )

image = (
    image
    .run_function(
        hf_download,
        volumes={"/data": data_vol},
        force_build=True,
    )
    .run_function(
        civitai_download,
        volumes={"/data": data_vol},
        force_build=True,
    )
)


app = modal.App(name="model-download", image=image)

@app.function(
    allow_concurrent_inputs=10,
    max_containers=1,
    volumes={"/data": data_vol},
)
@modal.web_server(8000, startup_timeout=60)
def ui():
    subprocess.Popen(f"exit 1", shell=True)
