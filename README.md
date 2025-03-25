# ComfyUI & AUTOMATIC1111 on Modal  

This repository sets up a working environment for [ComfyUI](https://github.com/comfyanonymous/ComfyUI), [AUTOMATIC1111 Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui), and [Deforum](https://github.com/deforum-art/deforum-stable-diffusion) on [modal.com](https://modal.com/).  

It includes pre-built images that handle downloading and saving various models — including checkpoints, LoRAs, VAEs, and ControlNets — from [Huggingface](https://huggingface.co/) and [CivitAI](https://civitai.com/).  


## 🚀 Setup  

1. **Create an account** on [modal.com](https://modal.com/).  
2. **Install dependencies:**  
   ```bash
   pip install -r requirements.txt
   ```  
3. **Set up Modal CLI:**  
   ```bash
   modal setup
   ```  
4. **Download models and assets:**  
   ```bash
   python download_data.py
   ```  
5. **Launch the WebUI:**  
   ```bash
   python comfyui.py   # For ComfyUI  
   python a1111.py     # For AUTOMATIC1111  
   ```

## ⚙️ Configuration  

The `config.json` file defines which models to download.  

To download models from CivitAI, include your CivitAI token in this file — it's required for access to CivitAI models.

If you want to add other models just add them to the config file and launch `python download_data.py`.

## 💾 Modal Volumes  

The scripts use two persistent volumes:  

- **`data`**: Stores models and user inputs.  
- **`cache`**: Stores outputs and temporary files.  

## 🛠️ Scripts  

- **`download_data.py`**: Downloads models from HuggingFace and CivitAI based on `config.json`. Data is stored on a Modal volume to avoid re-downloading.  
- **`a1111.py`**: Sets up the AUTOMATIC1111 WebUI and installs the Deforum extension.  
- **`comfyui.py`**: Sets up ComfyUI with custom nodes and Deforum Comfy Nodes.  

## 🔧 Useful Commands  

Here’s a quick reference for managing data on Modal volumes:  

### 📥 **Download from Modal Volume:**  
```bash
modal volume get [OPTIONS] VOLUME_NAME REMOTE_PATH [LOCAL_DESTINATION]
```
**Example:**  
To download outputs to a local `output/` folder:  
```bash
modal volume get --force cache / output/
```

### 📤 **Upload to Modal Volume:**  
```bash
modal volume put [OPTIONS] VOLUME_NAME LOCAL_PATH [REMOTE_PATH]
```
**Example:**  
To upload local `input/` data to `/data/input`:  
```bash
modal volume put --force data input/ /input
```
