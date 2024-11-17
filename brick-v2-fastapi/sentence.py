import modal
import subprocess
import os
import torch

app = modal.App("sentence-generator")

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(["torch==2.2.1", "huggingface_hub", "hf-transfer", "transformers", "vllm", "hf-transfer==0.1.4", "accelerate>=0.26.0"])
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
volume = modal.Volume.from_name("llamas", create_if_missing=True)

def print_file_structure(directory):
    for root, dirs, files in os.walk(directory):
        level = root.replace(directory, '').count(os.sep)
        if level > 2:
            continue
        indent = ' ' * 4 * (level)
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 4 * (level + 1)
        for f in files + dirs:
            print(f'{subindent}{f}')
            
model_dir = "/volume/model"


@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], timeout=3600, volumes={"/volume": volume})
def download_model():
    volume.reload()

    subprocess.run(["huggingface-cli", "login", "--token", os.environ["HF_TOKEN"]])
    
    
    # Ensure the module is available before importing
    import huggingface_hub
    from huggingface_hub import snapshot_download
    
    if not os.path.exists(model_dir):
        print('downloading')
        snapshot_download(repo_id="meta-llama/Llama-3.2-3B-Instruct",
                          token=os.environ["HF_TOKEN"],
                          ignore_patterns=["*.pt", "*.gguf"],  # Using safetensors
                          local_dir=model_dir
                          )
    else:
        print('not need download')
    
    
    volume.commit()
    
    
GPU_CONFIG = modal.gpu.H100(count=1)

@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], volumes={"/volume": volume}, gpu=GPU_CONFIG)
def generate(prompt):
    volume.reload()
    
    if not os.path.exists(model_dir):
        print('error')

    # Use a pipeline as a high-level helper
    from transformers import pipeline

    messages = [
        {"role": "user", "content": prompt},
    ]
    
    print_file_structure('/volume')
    
    if not os.path.exists('/volume/model'):
        pipe = pipeline("text-generation", model="meta-llama/Llama-3.2-3B-Instruct", model_kwargs={"torch_dtype": torch.bfloat16}, device_map="auto", token=os.environ["HF_TOKEN"], max_new_tokens=200)
        pipe.save_pretrained('/volume')
    else:
        pipe = pipeline("text-generation", model="/volume/model", tokenizer="/volume", model_kwargs={"torch_dtype": torch.bfloat16}, device_map="auto", token=os.environ["HF_TOKEN"], max_new_tokens=200)


    volume.commit()
    
    response = pipe(messages)
    
    return response


@app.local_entrypoint()
def main():
    download_model.remote()
    print(generate.remote("hey"))