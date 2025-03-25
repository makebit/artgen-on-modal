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

cache_vol = modal.Volume.from_name("cache", create_if_missing=True)
data_vol = modal.Volume.from_name("data", create_if_missing=True)

image = (
    modal.Image.debian_slim(
        python_version="3.10.16"
    )
    .apt_install(["git", "ffmpeg", "libsm6", "libxext6"])
    .run_commands("ldconfig")
    .pip_install("comfy-cli==1.3.8")
    .pip_install("huggingface_hub[hf_transfer]==0.29.3")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_commands(
        "comfy --skip-prompt install --nvidia --version 0.3.26"
    )
)

image = (
    image
    .run_commands(
        "comfy node install comfyui-animatediff-evolved@1.5.3"
    )
    .run_commands(
        "comfy node install comfyui-videohelpersuite@1.5.11"
    )
    .run_commands(
        "comfy node install comfyui_fizznodes@1.0.2"
    )
    .run_commands(
        "comfy node install ComfyUI-Crystools@1.22.1"
    )
    .run_commands(
        "comfy node install comfyui-art-venture@1.0.6"
    )
    .run_commands(
        "comfy node install comfyui_controlnet_aux@1.0.7"
    )
    .run_commands(
        "comfy node install ComfyUI-Custom-Scripts@1.2.3"
    )
    .run_commands(
        "comfy node install ComfyUI-WD14-Tagger@1.0.0"
    )
    .run_commands(
        "comfy node install ComfyUI_essentials@1.1.0"
    )
    .run_commands(
        "comfy node install comfyui-advanced-controlnet@1.5.4 "
    )
    .run_commands(
        "comfy node install ComfyUI-Apt_Preset@1.0.0 && pip install --upgrade colorama diffusers[torch] keyframed toolz"
    )
    .run_commands(
        "comfy node install comfyui-post-processing-nodes@1.0.1"
    )
    .run_commands(
        "comfy node install comfyui-glifnodes@1.0.0"
    )
    .run_commands(
        "comfy node install comfyui-hakuimg@1.0.5"
    )
    .run_commands(
        "comfy node install deforum-comfy-nodes"
    )
    .run_commands(
        "pip install --upgrade colorama==0.4.6 diffusers[torch]==0.32.2 keyframed==0.3.15 toolz==1.0.0 huggingface-hub==0.29.3"
    )

    # create folders for models
    .run_commands(
        "cd /root/comfy/ComfyUI/models && mkdir -p animatediff_models animatediff_motion_lora checkpoints clip clip_vision configs controlnet diffusers diffusion_models embeddings gligen hypernetworks loras photomaker style_models text_encoders unet upscale_models vae vae_approx"
    )
    
    # Add .run_commands(...) calls for any other custom nodes you want to download
)

image = image.add_local_file(
    Path(__file__).parent / 'config.json', "/root/config.json",
    copy=True
)

def hf_download():
    from huggingface_hub import hf_hub_download

    for model in models['hf']:
        model_path = hf_hub_download(
            repo_id=model['repo_id'],
            filename=model['filename'],
            cache_dir="/data",
        )
        subprocess.run(
            f"ln -s {model_path} /root/comfy/ComfyUI/models/{model['type']}/{model['filename'].split('/')[-1]}",
            shell=True,
            check=True,
        )

def civitai_download():
    for model in models['civitai']:
        subprocess.run(
            f"comfy --skip-prompt model download --url {model['url']} --set-civitai-api-token={tokens['civitai']} --relative-path /data &&"
            f"ln -s /data/{model['filename']} /root/comfy/ComfyUI/models/{model['type']}/{model['filename']}",
            shell=True,
            check=True,
        )

image = (
    image
    .run_function(
        hf_download,
        volumes={"/data": data_vol},
    )
    .run_function(
        civitai_download,
        volumes={"/data": data_vol},
    )
)


app = modal.App(name="comfyui", image=image)

@app.function(
    allow_concurrent_inputs=10,
    max_containers=1,
    gpu="T4",
    volumes={"/data": data_vol, "/cache": cache_vol},
)
@modal.web_server(8000, startup_timeout=60)
def ui():
    subprocess.Popen(f"comfy launch -- --listen 0.0.0.0 --port 8000 --output-directory /cache --verbose DEBUG", shell=True)
