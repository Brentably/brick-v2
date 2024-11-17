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


@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], timeout=3600, volumes={"/volume": volume})
def download_model():
    volume.reload()

    subprocess.run(["huggingface-cli", "login", "--token", os.environ["HF_TOKEN"]])
    
    
    # Ensure the module is available before importing
    import huggingface_hub
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id="meta-llama/Llama-3.2-3B-Instruct",
                            #   local_dir=volume + "/" + "llama3.2",
                              token=os.environ["HF_TOKEN"],
                                ignore_patterns=["*.pt", "*.gguf"],  # Using safetensors
                              )
    volume.commit()
    
    
GPU_CONFIG = modal.gpu.H100(count=1)

@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], volumes={"/volume": volume}, gpu=GPU_CONFIG)
def generate(prompt):
    volume.reload()
    # Use a pipeline as a high-level helper
    from transformers import pipeline

    messages = [
        {"role": "user", "content": prompt},
    ]
    
    pipe = pipeline("text-generation", model="meta-llama/Llama-3.2-3B-Instruct", model_kwargs={"torch_dtype": torch.bfloat16}, device_map="auto", token=os.environ["HF_TOKEN"], max_new_tokens=200)
    response = pipe(messages)
    return response


@app.local_entrypoint()
def main():
    download_model.remote()
    print(generate.remote("hey"))