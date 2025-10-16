import os
import subprocess
import sys
from pathlib import Path

def convert_obj_to_bam(obj_folder, bam_folder=None):
    """
    Convert all OBJ files in a folder to BAM format using Panda3D's obj2bam tool
    
    Args:
        obj_folder: Path to folder containing OBJ files
        bam_folder: Path to output folder for BAM files (defaults to ./bam relative to obj_folder)
    """
    
    obj_path = Path(obj_folder)
    if not obj_path.exists():
        print(f"Error: OBJ folder '{obj_folder}' does not exist!")
        return
    
    # Set default bam folder if not specified
    if bam_folder is None:
        bam_folder = obj_path.parent / "bam"
    else:
        bam_folder = Path(bam_folder)
    
    # Create bam folder if it doesn't exist
    bam_folder.mkdir(exist_ok=True)
    
    print(f"Converting OBJ files from: {obj_path}")
    print(f"Saving BAM files to: {bam_folder}")
    
    # Find all OBJ files
    obj_files = list(obj_path.glob("*.blend"))
    
    if not obj_files:
        print("No OBJ files found in the specified folder!")
        return
    
    print(f"Found {len(obj_files)} OBJ files to convert")
    
    successful_conversions = 0
    failed_conversions = 0
    
    for obj_file in obj_files:
        try:
            # Create output BAM filename
            bam_file = bam_folder / f"{obj_file.stem}.bam"
            
            print(f"Converting: {obj_file.name} -> {bam_file.name}")
            
            # Run obj2bam command
            result = subprocess.run([
                "blend2bam",
                str(obj_file),
                str(bam_file)
            ], capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                print(f"✓ Successfully converted {obj_file.name}")
                successful_conversions += 1
            else:
                print(f"✗ Failed to convert {obj_file.name}: {result.stderr}")
                failed_conversions += 1
                
        except subprocess.CalledProcessError as e:
            print(f"✗ Error converting {obj_file.name}: {e.stderr}")
            failed_conversions += 1
        except FileNotFoundError:
            print("✗ Error: obj2bam command not found. Make sure Panda3D is installed and in your PATH.")
            break
        except Exception as e:
            print(f"✗ Unexpected error converting {obj_file.name}: {e}")
            failed_conversions += 1
    
    print(f"\nConversion complete!")
    print(f"Successful: {successful_conversions}")
    print(f"Failed: {failed_conversions}")
    print(f"BAM files saved to: {bam_folder}")

def convert_with_options(obj_folder, bam_folder=None, options=None):
    """
    Convert OBJ to BAM with additional obj2bam options
    
    Args:
        obj_folder: Path to folder containing OBJ files
        bam_folder: Output folder for BAM files
        options: List of additional options for obj2bam
    """
    if options is None:
        options = []
    
    obj_path = Path(obj_folder)
    if not obj_path.exists():
        print(f"Error: OBJ folder '{obj_folder}' does not exist!")
        return
    
    if bam_folder is None:
        bam_folder = obj_path.parent / "bam"
    else:
        bam_folder = Path(bam_folder)
    
    bam_folder.mkdir(exist_ok=True)
    
    obj_files = list(obj_path.glob("*.obj"))
    
    if not obj_files:
        print("No OBJ files found!")
        return
    
    successful = 0
    failed = 0
    
    for obj_file in obj_files:
        try:
            bam_file = bam_folder / f"{obj_file.stem}.bam"
            
            cmd = ["blend2bam"] + options + ["-o", str(bam_file), str(obj_file)]
            
            print(f"Converting: {obj_file.name}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                print(f"✓ Success: {obj_file.name}")
                successful += 1
            else:
                print(f"✗ Failed: {obj_file.name} - {result.stderr}")
                failed += 1
                
        except Exception as e:
            print(f"✗ Error: {obj_file.name} - {e}")
            failed += 1
    
    print(f"\nCompleted: {successful} successful, {failed} failed")

# Alternative version using Panda3D's Python API (if you want to run it within a Panda3D application)
def convert_obj_to_bam_python_api(obj_folder, bam_folder=None):
    """
    Convert OBJ to BAM using Panda3D's Python API
    This can be run from within a Panda3D application
    """
    try:
        from panda3d.core import Filename, Loader, ModelRoot
        from panda3d.core import NodePath
        
        obj_path = Path(obj_folder)
        if bam_folder is None:
            bam_folder = obj_path.parent / "bam"
        else:
            bam_folder = Path(bam_folder)
        
        bam_folder.mkdir(exist_ok=True)
        
        obj_files = list(obj_path.glob("*.obj"))
        
        if not obj_files:
            print("No OBJ files found!")
            return
        
        loader = Loader.get_global_ptr()
        successful = 0
        failed = 0
        
        for obj_file in obj_files:
            try:
                bam_file = bam_folder / f"{obj_file.stem}.bam"
                
                print(f"Converting: {obj_file.name}")
                
                # Load OBJ file
                model = loader.load_model(Filename.from_os_specific(str(obj_file)))
                if model:
                    # Save as BAM
                    model.write_bam_file(Filename.from_os_specific(str(bam_file)))
                    print(f"✓ Success: {obj_file.name}")
                    successful += 1
                else:
                    print(f"✗ Failed to load: {obj_file.name}")
                    failed += 1
                    
            except Exception as e:
                print(f"✗ Error: {obj_file.name} - {e}")
                failed += 1
        
        print(f"\nPython API conversion: {successful} successful, {failed} failed")
        
    except ImportError:
        print("Panda3D Python API not available. Using command-line method instead.")
        convert_obj_to_bam(obj_folder, bam_folder)

# Batch conversion with common options
def batch_convert_with_preset(obj_folder, preset="default"):
    """
    Convert with preset options for different use cases
    """
    presets = {
        "default": [],
        "no_normals": ["--no-normals"],
        "no_uvs": ["--no-uvs"],
        "flip_uvs": ["--flip-uvs"],
        "srgb": ["--srgb"],
        "verbose": ["-v"]
    }
    
    options = presets.get(preset, [])
    print(f"Using preset: {preset} with options: {options}")
    convert_with_options(obj_folder, options=options)

if __name__ == "__main__":
    # Example usage - modify these paths as needed
    
    # Method 1: Simple conversion
    obj_folder = "./mesh"  # Relative to VT/ folder
    bam_folder = "./bam"   # Relative to VT/ folder
    
    print("Starting OBJ to BAM conversion...")
    convert_obj_to_bam(obj_folder, bam_folder)
    
    # Method 2: Conversion with options (uncomment to use)
    # convert_with_options(obj_folder, bam_folder, options=["--flip-uvs", "-v"])
    
    # Method 3: Using preset (uncomment to use)
    # batch_convert_with_preset(obj_folder, "verbose")
    
    # Method 4: Python API (uncomment to use within Panda3D app)
    # convert_obj_to_bam_python_api(obj_folder, bam_folder)