import bpy
import os
import sys
import site
import tempfile
import subprocess
import importlib
import traceback

def get_site_packages_path():
    """Get the appropriate site-packages path based on the platform"""
    if sys.platform == "win32":
        site_packages_path = os.path.expanduser('~') + "/AppData/Roaming/Python/Python311/site-packages"
    elif sys.platform == "darwin":
        site_packages_path = os.path.expanduser('~') + "/Library/Python/3.11/lib/python/site-packages"
    else:  # Linux and other Unix-like
        site_packages_path = os.path.expanduser('~') + "/.local/lib/python3.11/site-packages"
    
    return site_packages_path

def fix_python_path():
    # Blender's site-packages path (example for Blender 4.4 on macOS)
    blender_site_packages = "/Applications/Blender.app/Contents/Resources/4.4/python/lib/python3.11/site-packages"

    # Add Blender's site-packages path first
    if blender_site_packages not in sys.path:
        sys.path.append(blender_site_packages)
        print(f"[eLCA] Added Blender site-packages: {blender_site_packages}")

    # Optionally keep user site-packages too
    site_packages_path = get_site_packages_path()
    if site_packages_path not in sys.path:
        sys.path.append(site_packages_path)
        print(f"[eLCA] Added user site-packages: {site_packages_path}")

def install_and_import(package_name, import_name=None):
    """
    Install a package if not already installed and import it
    
    Args:
        package_name: Name of the package to install (as used by pip)
        import_name: Name of the module to import (if different from package_name)
    
    Returns:
        The imported module or None if import failed
    """
    if import_name is None:
        import_name = package_name
    
    print(f"[eLCA] Checking for {import_name}...")
    
    try:
        # Try to import the module
        module = importlib.import_module(import_name)
        print(f"[eLCA] {import_name} is already installed")
        return module
    except ImportError:
        print(f"[eLCA] {import_name} not found, attempting to install {package_name}...")
        
        try:
            # Get Python executable
            python_executable = sys.executable
            
            # Ensure pip is available
            subprocess.check_call([python_executable, "-m", "ensurepip", "--upgrade"], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Install the package - don't use --user flag on macOS
            install_cmd = [python_executable, "-m", "pip", "install", package_name]
            if sys.platform != "darwin":  # Not macOS
                install_cmd.append("--user")
            
            subprocess.check_call(install_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print(f"[eLCA] Successfully installed {package_name}")
            
            # Try to import again
            module = importlib.import_module(import_name)
            print(f"[eLCA] Successfully imported {import_name}")
            return module
            
        except Exception as e:
            print(f"[eLCA] Error installing package {package_name} using {import_name} as import name: {str(e)}")
            print(traceback.format_exc())
            return None

def ensure_dependencies():
    """Ensure all required dependencies are installed"""
    print("[eLCA] Checking and installing dependencies...")
    
    # Fix Python path
    fix_python_path()
    
    # List of required packages (package_name, import_name)
    required_packages = [
        ("beautifulsoup4", "bs4"),
        ("pandas", "pandas"),
        ("ifcopenshell", "ifcopenshell"),
    ]
    
    # Install and import each package
    missing_packages = []
    for package_name, import_name in required_packages:
        module = install_and_import(package_name, import_name)
        if module is None:
            missing_packages.append(package_name)
    
    # Report results
    if missing_packages:
        print(f"[eLCA] Warning: Could not install the following packages: {', '.join(missing_packages)}")
        return False
    else:
        print("[eLCA] All dependencies are installed")
        return True

# Run this when the module is imported
if __name__ == "__main__":
    ensure_dependencies()