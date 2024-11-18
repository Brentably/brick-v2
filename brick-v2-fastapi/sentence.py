import modal
import subprocess
import os
from llama_cpp.llama import Llama, LlamaGrammar

app = modal.App("sentence-generator")

cuda_version = "12.4.0"  # should be no greater than host CUDA version
flavor = "devel"  #  includes full CUDA toolkit
operating_sys = "ubuntu22.04"
tag = f"{cuda_version}-{flavor}-{operating_sys}"

image = (
    modal.Image.from_registry(f"nvidia/cuda:{tag}", add_python="3.11")
    .apt_install('git', 'curl', 'build-essential', 'clang', "sudo")  # Added clang and build-essential
    .run_commands("curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list")
    .run_commands("sudo apt-get update")
    .run_commands("sudo apt-get install -y nvidia-container-toolkit")
    .run_commands(
        "pip install -U pip",
        "pip install llama-cpp-python \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124"    
    )
    .pip_install("torch")
    .copy_local_file('./experimental/top_2000_german.gbnf', '/experimental/top_2000_german.gbnf')
    .copy_local_file('./experimental/top_600_german.gbnf', '/experimental/top_600_german.gbnf')
    .copy_local_file('./experimental/chess.gbnf', '/experimental/chess.gbnf')
    .copy_local_file("./5009_word_and_scraped_cd.json", "/experimental/5009_word_and_scraped_cd.json")
    # .run_commands("curl -L -o /volume/model https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")

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
            
model_path = "/volume/model"


@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], timeout=3600, volumes={"/volume": volume})
def download_model():
    volume.reload()
    if not os.path.exists(model_path):
        print("Downloading model...")
        subprocess.run([
            "curl",
            "-L",
            "-o", model_path,
            # "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-f16.gguf"
            "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
        ], check=True)
        print("Download complete")
    else:
        print("Model already exists")
    
    volume.commit()

GPU_CONFIG = modal.gpu.H100(count=1)

@app.function(image=image, secrets=[modal.Secret.from_name("huggingface-secret")], volumes={"/volume": volume}, gpu=GPU_CONFIG)
def generate(prompt):
    volume.reload()
    
    import json

    with open("/experimental/5009_word_and_scraped_cd.json", "r") as file:
        data = json.load(file)
    
    words = [entry["word"] for entry in data][:2000]
    print(words)
    
    if not os.path.exists(model_path):
        print('Model not found')
        return
    
    import torch
    has_cuda = torch.cuda.is_available()
    print(f"It is {has_cuda} that torch can access CUDA")

    if torch.cuda.is_available():
        print("GPU is available")
        print(f"Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("GPU is not available, using CPU")
        
    llm = Llama(
        model_path=model_path,
        n_gpu_layers=-1, # Uncomment to use GPU acceleration
        # seed=1337, # Uncomment to set a specific seed
        n_ctx=10000, # Uncomment to increase the context window
    )
    grammar = LlamaGrammar.from_file("/experimental/chess.gbnf")
    german_grammar = LlamaGrammar.from_file("/experimental/top_2000_german.gbnf")

    prompt = "Create a vibrant german sentence using only the following words: " + ", ".join(words) + "." + "Vibrant german sentence: "
    
    output = llm(
        prompt=prompt, # Prompt
        max_tokens=100, # Generate up to 32 tokens, set to None to generate up to the end of the context window
        echo=True, # Echo the prompt back in the output
        # grammar=german_grammar,
        

        
    ) # Generate a completion, can also call create_completion
    for item in output:
        print(item['choices'][0]['text'], end='')
        
    print(output)

    
    return output

@app.local_entrypoint()
def main():
    download_model.remote()
    print(generate.remote("A basic sentence in german: "))