import modal
import subprocess
import os


app = modal.App("sentence-generator")

image = (
    modal.Image.from_registry("ghcr.io/ggerganov/llama.cpp:light-cuda", add_python="3.11")
    .entrypoint([])
    # .run_commands("ln -sf /usr/bin/python3 /usr/bin/python", "python -V")
    # .run_commands("echo \"alias python='python3'\" >> /root/.bashrc", "python -V")
    .copy_local_file('./experimental/top_2000_german.gbnf', '/experimental/top_2000_german.gbnf')
    .copy_local_file('./experimental/top_600_german.gbnf', '/experimental/top_600_german.gbnf')
    .copy_local_file('./experimental/chess.gbnf', '/experimental/chess.gbnf')

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
            
model_path = "/volume/Llama-3.2-3B-Instruct-f16.gguf"


@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], timeout=3600, volumes={"/volume": volume})
def download_model():
    volume.reload()
    if not os.path.exists(model_path):
        print("Downloading model...")
        subprocess.run([
            "curl",
            "-L",
            "-o", model_path,
            "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-f16.gguf"
        ], check=True)
        print("Download complete")
    else:
        print("Model already exists")
    
    volume.commit()

GPU_CONFIG = modal.gpu.H100(count=1)

@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], volumes={"/volume": volume}, gpu=GPU_CONFIG)
def generate(prompt):
    volume.reload()
    
    if not os.path.exists(model_path):
        print('Model not found')
        return
    
    # First generate with llama.cpp
    llama_response = subprocess.run(
        ["/llama-cli",
        "-m", model_path, 
        "-p", prompt, 
        "-n", "100", 
        "--ctx-size", "100000",  
        "--grammar-file", "/experimental/top_600_german.gbnf",
        "--gpus", "all",
        "--n-gpu-layers", "1", '-v'], capture_output=True, text=True)

    print('response')
    print(llama_response.stdout)
    print('stdrr')
    print(llama_response.stderr)

    
    return llama_response

@app.local_entrypoint()
def main():
    download_model.remote()
    print(generate.remote("A basic sentence in german: "))