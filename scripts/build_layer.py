import os
import subprocess
import shutil

def build_lambda_layer():
    print("--- Building Lambda Package (Layer) ---")
    layer_dir = os.path.join("layer", "python")
    
    # 1. Clean the destination folder if it already exists
    if os.path.exists("layer"):
        shutil.rmtree("layer")
        
    os.makedirs(layer_dir, exist_ok=True)
    
    print(f"Fetching dependencies for AWS Serverless environment...")
    
    try:
        # Use explicit instructions to download compiled versions for Amazon Linux (x86_64) and Python 3.12
        # This prevents 'Runtime.ImportModuleError' when deploying on AWS Lambda
        subprocess.run(
            [
                "python", "-m", "pip", "install", 
                "requests", "pydantic", 
                "--target", layer_dir,
                "--platform", "manylinux2014_x86_64",
                "--implementation", "cp",
                "--python-version", "3.12",
                "--only-binary=:all:",
                "--upgrade"
            ],
            check=True
        )
        print("\nSuccess! The layer is ready in ./layer")
        print("Returning to terraform to compress.")
    except Exception as e:
        print(f"Error packing dependencies. Error: {e}")

if __name__ == "__main__":
    build_lambda_layer()
