import os
import sys
import zipfile
import hashlib
import shutil
from pathlib import Path

class PolyglotTool:
    def __init__(self):
        self.temp_files = []
    
    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        self.temp_files = []
    
    def calculate_md5(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_file_size_gb(self, file_path):
        """Get file size in GB"""
        return os.path.getsize(file_path) / (1024 ** 3)
    
    def ask_yes_no(self, question, default="yes"):
        """Ask a yes/no question"""
        valid = {"yes": True, "y": True, "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("Invalid default answer: '%s'" % default)
        
        while True:
            choice = input(question + prompt).lower().strip()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                print("Please respond with 'yes' or 'no' (or 'y' or 'n').")
    
    def ask_file_path(self, prompt, file_type=None):
        """Ask for a file path with validation"""
        while True:
            path = input(prompt).strip()
            if not path:
                print("Please enter a file path.")
                continue
            
            if not os.path.exists(path):
                print("File does not exist. Please try again.")
                continue
            
            if file_type == "video" and not path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                print("Please select a video file (MP4, MOV, AVI, MKV).")
                continue
            
            return path
    
    def ask_directory(self, prompt):
        """Ask for a directory path"""
        while True:
            path = input(prompt).strip()
            if not path:
                print("Please enter a directory path.")
                continue
            
            if not os.path.exists(path):
                create = self.ask_yes_no("Directory doesn't exist. Create it?", "yes")
                if create:
                    os.makedirs(path, exist_ok=True)
                    return path
                else:
                    continue
            
            if os.path.isdir(path):
                return path
            else:
                print("This is not a directory. Please try again.")
    
    def ask_number(self, prompt, min_val=None, max_val=None, default=None):
        """Ask for a number with validation"""
        while True:
            try:
                value = input(prompt).strip()
                if default and value == "":
                    return default
                
                num = float(value)
                if min_val is not None and num < min_val:
                    print(f"Value must be at least {min_val}.")
                    continue
                if max_val is not None and num > max_val:
                    print(f"Value must be at most {max_val}.")
                    continue
                return num
            except ValueError:
                print("Please enter a valid number.")
    
    def create_polyglot_video(self):
        """Create a polyglot video from files"""
        print("\n" + "="*60)
        print("🎬 CREATE POLYGLOT VIDEO")
        print("="*60)
        
        # Ask for video template
        video_path = self.ask_file_path(
            "Enter path to video template (MP4/MOV/AVI/MKV): ",
            file_type="video"
        )
        
        # Ask what to hide
        print("\nWhat do you want to hide in the video?")
        print("1. Single file")
        print("2. Multiple files/folder")
        print("3. Existing ZIP file")
        
        choice = input("Choose option [1-3]: ").strip()
        
        files_to_hide = {}
        
        if choice == "1":
            # Single file
            file_path = self.ask_file_path("Enter path to file to hide: ")
            arcname = input("Enter name for hidden file (or press Enter for original name): ").strip()
            if not arcname:
                arcname = os.path.basename(file_path)
            files_to_hide[file_path] = arcname
            
        elif choice == "2":
            # Multiple files or folder
            source = self.ask_file_path("Enter path to file or folder to hide: ")
            
            if os.path.isdir(source):
                # Folder
                for root, _, files in os.walk(source):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, source)
                        files_to_hide[full_path] = rel_path
                print(f"Found {len(files_to_hide)} files in folder")
            else:
                # Single file but asked for multiple option
                arcname = input("Enter name for hidden file (or press Enter for original name): ").strip()
                if not arcname:
                    arcname = os.path.basename(source)
                files_to_hide[source] = arcname
                
        elif choice == "3":
            # Existing ZIP
            zip_path = self.ask_file_path("Enter path to ZIP file to hide: ")
            files_to_hide[zip_path] = "hidden_archive.zip"
            
        else:
            print("Invalid choice. Using single file option.")
            file_path = self.ask_file_path("Enter path to file to hide: ")
            files_to_hide[file_path] = os.path.basename(file_path)
        
        # Calculate total size
        total_size = sum(os.path.getsize(f) for f in files_to_hide.keys())
        total_size_gb = total_size / (1024 ** 3)
        
        print(f"\n📊 Total size to hide: {total_size_gb:.2f} GB")
        
        # Ask about splitting
        split_size = None
        if total_size_gb > 10:
            split = self.ask_yes_no("File is larger than 10GB. Split into multiple polyglot videos?", "yes")
            if split:
                split_size = self.ask_number(
                    "Enter split size in GB (recommended: 4-8): ",
                    min_val=1, max_val=20, default=8
                )
        
        # Output name
        output_base = input("Enter output base name (or press Enter for 'hidden_data'): ").strip()
        if not output_base:
            output_base = "hidden_data"
        
        # Create polyglot
        if split_size:
            self.create_split_polyglot(video_path, files_to_hide, output_base, split_size)
        else:
            self.create_single_polyglot(video_path, files_to_hide, output_base)
    
    def create_single_polyglot(self, video_path, files_to_hide, output_base):
        """Create a single polyglot video"""
        print(f"\nCreating single polyglot video...")
        
        # Read video
        with open(video_path, 'rb') as f:
            video_data = f.read()
        
        # Create ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, arcname in files_to_hide.items():
                zipf.write(file_path, arcname)
                print(f"Added: {arcname}")
        
        zip_data = zip_buffer.getvalue()
        
        # Create polyglot
        output_path = f"{output_base}.mp4"
        with open(output_path, 'wb') as f:
            f.write(video_data)
            f.write(zip_data)
        
        # Calculate checksum
        checksum = self.calculate_md5(output_path)
        
        print(f"\n✅ Polyglot video created: {output_path}")
        print(f"📊 Size: {self.get_file_size_gb(output_path):.2f} GB")
        print(f"🔒 Checksum: {checksum}")
        print(f"📦 Contains: {len(files_to_hide)} hidden files")
        
        # Create recovery info
        self.create_recovery_info(output_path, checksum, list(files_to_hide.values()))
    
    def create_split_polyglot(self, video_path, files_to_hide, output_base, split_size_gb):
        """Create split polyglot videos"""
        import math
        print(f"\nCreating split polyglot videos ({split_size_gb}GB each)...")

        # Read video
        with open(video_path, 'rb') as f:
            video_data = f.read()

        # Create ZIP first
        temp_zip = f"{output_base}_temp.zip"
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, arcname in files_to_hide.items():
                zipf.write(file_path, arcname)
        self.temp_files.append(temp_zip)

        # Read ZIP data
        with open(temp_zip, 'rb') as f:
            zip_data = f.read()

        # Split parameters
        split_size = int(split_size_gb * 1024 ** 3)
        num_parts = math.ceil(len(zip_data) / split_size)

        print(f"Splitting {len(zip_data) / (1024**3):.2f} GB into {num_parts} parts...")

        # Create parts
        polyglot_videos = []
        part_checksums = []

        for i in range(num_parts):
            part_num = i + 1
            start = i * split_size
            end = min((i + 1) * split_size, len(zip_data))
            part_data = zip_data[start:end]

            # Create polyglot video
            output_path = f"{output_base}_part{part_num}.mp4"
            with open(output_path, 'wb') as f:
                f.write(video_data)
                f.write(part_data)

            polyglot_videos.append(output_path)
            part_checksums.append(hashlib.md5(part_data).hexdigest())

            print(f"✅ Created {output_path} ({len(part_data) / (1024**3):.2f} GB)")

        # Original checksum
        original_checksum = self.calculate_md5(temp_zip)

        # Create recovery package
        self.create_split_recovery_package(output_base, polyglot_videos, original_checksum, part_checksums)

        print(f"\n🎉 Created {num_parts} polyglot videos!")
        print(f"🔒 Original checksum: {original_checksum}")
        print("💾 Recovery package created with extraction tools")
    
    def create_recovery_info(self, polyglot_path, checksum, hidden_files):
        """Create recovery information for single polyglot"""
        recovery_file = f"{os.path.splitext(polyglot_path)[0]}_recovery.txt"
        
        content = f"""POLYGLOT RECOVERY INFORMATION
===============================

Polyglot File: {polyglot_path}
Checksum: {checksum}
Creation Date: {os.path.getctime(polyglot_path)}
Size: {self.get_file_size_gb(polyglot_path):.2f} GB

HIDDEN FILES:
"""
        for file in hidden_files:
            content += f"- {file}\n"
        
        content += f"""
EXTRACTION INSTRUCTIONS:

Method 1: Using Python
----------------------
import zipfile
with open('{polyglot_path}', 'rb') as f:
    data = f.read()
zip_start = data.find(b'PK')
with open('extracted.zip', 'wb') as f:
    f.write(data[zip_start:])

Method 2: Manual Extraction
---------------------------
1. Find where ZIP data starts (look for 'PK' header)
2. Use tools like dd or hex editors to extract
3. Rename extracted data to .zip and extract

Method 3: Command Line
----------------------
# Extract using unzip (may work directly)
unzip {polyglot_path}

# Or use strings to find ZIP start
strings -t d {polyglot_path} | grep PK
"""
        
        with open(recovery_file, 'w') as f:
            f.write(content)
        
        print(f"📋 Recovery info: {recovery_file}")
    
    def create_split_recovery_package(self, output_base, polyglot_videos, original_checksum, part_checksums):
        """Create recovery package for split polyglots"""
        recovery_zip = f"{output_base}_recovery.zip"
        
        # Create instructions
        instructions = f"""SPLIT POLYGLOT RECOVERY
=======================

Original Checksum: {original_checksum}
Number of Parts: {len(polyglot_videos)}

PARTS AND CHECKSUMS:
"""
        for i, (video, checksum) in enumerate(zip(polyglot_videos, part_checksums)):
            instructions += f"Part {i+1}: {video} (MD5: {checksum})\n"
        
        instructions += f"""
RECOVERY METHODS:

1. AUTOMATIC:
   - Extract this ZIP
   - Run: python recover_split.py

2. MANUAL:
   - Extract each part:
     python extract_part.py {polyglot_videos[0]}
     python extract_part.py {polyglot_videos[1]}
   
   - Combine parts:
     copy /b part1.bin + part2.bin + ... complete.zip
   
   - Verify checksum:
     python verify_checksum.py complete.zip {original_checksum}

3. QUICK:
   python recover_split.py --auto
"""
        
        with open('recovery_instructions.txt', 'w') as f:
            f.write(instructions)
        self.temp_files.append('recovery_instructions.txt')
        
        # Create recovery script
        recovery_script = f"""#!/usr/bin/env python3
import sys
import glob
import os

def recover_split():
    # Find all part files
    parts = sorted(glob.glob("{output_base}_part*.mp4"))
    if not parts:
        print("No part files found!")
        return False
    
    # Extract and combine
    with open('recovered.zip', 'wb') as outfile:
        for part in parts:
            print(f"Processing {{part}}...")
            with open(part, 'rb') as f:
                data = f.read()
            # Find ZIP data (simple heuristic)
            zip_start = max(data.find(b'PK'), len(data) // 2)
            outfile.write(data[zip_start:])
    
    print("Recovery complete! File: recovered.zip")
    return True

if __name__ == "__main__":
    recover_split()
"""
        
        with open('recover_split.py', 'w') as f:
            f.write(recovery_script)
        self.temp_files.append('recover_split.py')
        
        # Create extraction script
        extract_script = """#!/usr/bin/env python3
import sys

def extract_part(video_path):
    with open(video_path, 'rb') as f:
        data = f.read()
    # Find where data starts (after video)
    data_start = data.find(b'PK')
    if data_start == -1:
        data_start = len(data) // 2
    output_path = video_path.replace('.mp4', '.bin')
    with open(output_path, 'wb') as f:
        f.write(data[data_start:])
    print(f"Extracted to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_part.py <video_file>")
        sys.exit(1)
    extract_part(sys.argv[1])
"""
        
        with open('extract_part.py', 'w') as f:
            f.write(extract_script)
        self.temp_files.append('extract_part.py')
        
        # Create recovery ZIP
        with zipfile.ZipFile(recovery_zip, 'w') as zipf:
            for file in ['recovery_instructions.txt', 'recover_split.py', 'extract_part.py']:
                zipf.write(file)
        
        print(f"📦 Recovery package: {recovery_zip}")
    
    def extract_from_polyglot(self):
        """Extract hidden content from polyglot video"""
        print("\n" + "="*60)
        print("🔓 EXTRACT FROM POLYGLOT VIDEO")
        print("="*60)
        
        polyglot_path = self.ask_file_path("Enter path to polyglot video: ")
        
        if not os.path.exists(polyglot_path):
            print("File not found!")
            return
        
        # Check if it's part of a split polyglot
        is_split = "_part" in polyglot_path and polyglot_path.endswith('.mp4')
        
        if is_split:
            self.extract_split_polyglot(polyglot_path)
        else:
            self.extract_single_polyglot(polyglot_path)
    
    def extract_single_polyglot(self, polyglot_path):
        """Extract from single polyglot video"""
        print(f"Extracting from {polyglot_path}...")
        
        with open(polyglot_path, 'rb') as f:
            data = f.read()
        
        # Find ZIP data
        zip_start = data.find(b'PK')
        if zip_start == -1:
            print("No ZIP data found in the file!")
            return
        
        # Extract ZIP data
        zip_data = data[zip_start:]
        output_zip = f"extracted_from_{os.path.basename(polyglot_path)}.zip"
        
        with open(output_zip, 'wb') as f:
            f.write(zip_data)
        
        # Try to list contents
        try:
            with zipfile.ZipFile(output_zip, 'r') as zipf:
                files = zipf.namelist()
                print(f"✅ Successfully extracted {len(files)} files:")
                for file in files:
                    print(f"  - {file}")
                
                # Ask to extract
                extract = self.ask_yes_no("\nExtract the files?", "yes")
                if extract:
                    extract_dir = f"extracted_{os.path.splitext(polyglot_path)[0]}"
                    os.makedirs(extract_dir, exist_ok=True)
                    zipf.extractall(extract_dir)
                    print(f"📁 Files extracted to: {extract_dir}")
        
        except zipfile.BadZipFile:
            print("⚠ Extracted data is not a valid ZIP file")
            print("The file may be corrupted or not contain ZIP data")
    
    def extract_split_polyglot(self, polyglot_path):
        """Handle split polyglot extraction"""
        print("This appears to be part of a split polyglot.")
        
        # Find all parts
        base_name = polyglot_path.split('_part')[0]
        possible_parts = []
        
        for ext in ['.mp4', '.mov', '.avi']:
            pattern = f"{base_name}_part*{ext}"
            possible_parts.extend(glob.glob(pattern))
        
        if len(possible_parts) > 1:
            print(f"Found {len(possible_parts)} potential parts:")
            for part in sorted(possible_parts):
                print(f"  - {part}")
            
            extract_all = self.ask_yes_no("Extract and combine all parts?", "yes")
            if extract_all:
                self.combine_split_polyglots(possible_parts)
        else:
            print("Only one part found. Extracting single part...")
            self.extract_single_polyglot(polyglot_path)
    
    def combine_split_polyglots(self, part_files):
        """Combine and extract from split polyglots"""
        print("Combining split polyglots...")
        
        combined_data = bytearray()
        
        for part_file in sorted(part_files):
            print(f"Processing {part_file}...")
            with open(part_file, 'rb') as f:
                data = f.read()
            
            # Find where data starts in each part
            data_start = data.find(b'PK')
            if data_start == -1:
                data_start = len(data) // 2  # heuristic fallback
            
            combined_data.extend(data[data_start:])
        
        # Save combined data
        output_zip = "combined_extracted.zip"
        with open(output_zip, 'wb') as f:
            f.write(combined_data)
        
        # Try to extract
        try:
            with zipfile.ZipFile(output_zip, 'r') as zipf:
                files = zipf.namelist()
                print(f"✅ Combined {len(part_files)} parts into {len(files)} files")
                
                extract = self.ask_yes_no("Extract the files?", "yes")
                if extract:
                    extract_dir = "combined_extraction"
                    os.makedirs(extract_dir, exist_ok=True)
                    zipf.extractall(extract_dir)
                    print(f"📁 Files extracted to: {extract_dir}")
        
        except zipfile.BadZipFile:
            print("⚠ Combined data is not a valid ZIP")
            print("The parts may be corrupted or in wrong order")
    
    def show_menu(self):
        """Show main menu"""
        print("\n" + "="*60)
        print("🎬 POLYGLOT VIDEO TOOL")
        print("="*60)
        print("1. Create polyglot video (hide files in video)")
        print("2. Extract from polyglot video (get hidden files)")
        print("3. Verify polyglot integrity")
        print("4. Clean up temporary files")
        print("5. Exit")
        
        choice = input("\nChoose option [1-5]: ").strip()
        
        if choice == "1":
            self.create_polyglot_video()
        elif choice == "2":
            self.extract_from_polyglot()
        elif choice == "3":
            self.verify_polyglot()
        elif choice == "4":
            self.cleanup()
            print("Temporary files cleaned up!")
        elif choice == "5":
            print("Goodbye! 👋")
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")
        self.show_menu()
    
    def verify_polyglot(self):
        """Verify polyglot integrity"""
        print("\n" + "="*60)
        print("🔍 VERIFY POLYGLOT INTEGRITY")
        print("="*60)
        
        polyglot_path = self.ask_file_path("Enter path to polyglot video: ")
        
        if not os.path.exists(polyglot_path):
            print("File not found!")
            return
        
        # Check if it contains ZIP data
        with open(polyglot_path, 'rb') as f:
            data = f.read()
        
        has_zip = b'PK' in data
        file_size = self.get_file_size_gb(polyglot_path)
        checksum = self.calculate_md5(polyglot_path)
        
        print(f"\n📊 File: {polyglot_path}")
        print(f"📏 Size: {file_size:.2f} GB")
        print(f"🔒 Checksum: {checksum}")
        print(f"📦 Contains ZIP data: {'✅ Yes' if has_zip else '❌ No'}")
        
        if has_zip:
            # Try to read the ZIP
            zip_start = data.find(b'PK')
            zip_data = data[zip_start:]
            
            temp_zip = "temp_verify.zip"
            with open(temp_zip, 'wb') as f:
                f.write(zip_data)
            self.temp_files.append(temp_zip)
            
            try:
                with zipfile.ZipFile(temp_zip, 'r') as zipf:
                    files = zipf.namelist()
                    print(f"✅ ZIP integrity: Good")
                    print(f"📁 Contains {len(files)} files:")
                    for file in files[:5]:  # Show first 5 files
                        print(f"  - {file}")
                    if len(files) > 5:
                        print(f"  - ... and {len(files) - 5} more")
            
            except zipfile.BadZipFile:
                print("⚠ ZIP data appears corrupted")
        
        print("\n💡 Tips:")
        print("- Use extraction tool to recover files")
        print("- Keep backup of original files")
        print("- Verify checksums after recovery")

def main():
    """Main function"""
    tool = PolyglotTool()
    
    try:
        print("Welcome to the Polyglot Video Tool! 🎥✨")
        print("This tool helps you hide files inside videos and extract them later.")
        tool.show_menu()
    except KeyboardInterrupt:
        print("\nExiting... 👋")
        tool.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    from io import BytesIO
    import glob
    main()
