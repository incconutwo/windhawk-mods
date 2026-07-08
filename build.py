import os
import subprocess
import site
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow not found. Installing Pillow...")
    subprocess.run(["pip", "install", "Pillow"], check=True)
    from PIL import Image

def build_app():
    print("1. Preparing Icon...")
    png_path = "icon.png"
    ico_path = "icon.ico"
    
    if os.path.exists(png_path):
        img = Image.open(png_path)
        img.save(ico_path, format="ICO", sizes=[(256, 256)])
        print(f"✅ Converted {png_path} to {ico_path}")
    else:
        print(f"⚠️ {png_path} not found. Skipping icon conversion.")
        ico_path = None

    print("\n2. Finding CustomTkinter Assets...")
    # Find the python site-packages to include customtkinter data
    site_packages = site.getsitepackages()[0]
    ctk_path = os.path.join(site_packages, "customtkinter")
    
    if not os.path.exists(ctk_path):
        # Fallback to local user site-packages just in case
        ctk_path = os.path.join(site.getusersitepackages(), "customtkinter")

    print("\n3. Building with PyInstaller...")
    pyinstaller_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir", 
        "--windowed", # Don't open console
        "--name", "ForgeSync",
        "main_app.py"
    ]
    
    if ico_path:
        pyinstaller_cmd.extend(["--icon", ico_path])
        
    if os.path.exists(ctk_path):
        # Add CustomTkinter library explicitly to bundle its assets
        pyinstaller_cmd.extend(["--add-data", f"{ctk_path};customtkinter/"])

    print(f"Running command: {' '.join(pyinstaller_cmd)}")
    subprocess.run(pyinstaller_cmd, check=True)

    print("\n🎉 Build Complete! Check the 'dist/ForgeSync' folder.")

if __name__ == "__main__":
    build_app()
