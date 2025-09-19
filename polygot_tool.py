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
        print("3. Existing ZIP/RAR file (direct embed - faster)")
        
        choice = input("Choose option [1-3]: ").strip()
        
        files_to_hide = {}
        use_direct_embed = False
        direct_file = None
        
        if choice == "1":
            # Single file
            file_path = self.ask_file_path("Enter path to file to hide: ")
            # Check if it's already an archive
            if file_path.lower().endswith(('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2')):
                bypass = self.ask_yes_no("This is an archive file. Skip ZIP wrapping for faster processing?", "yes")
                if bypass:
                    use_direct_embed = True
                    direct_file = file_path
                else:
                    arcname = input("Enter name for hidden file (or press Enter for original name): ").strip()
                    if not arcname:
                        arcname = os.path.basename(file_path)
                    files_to_hide[file_path] = arcname
            else:
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
            # Direct archive embedding
            archive_path = self.ask_file_path("Enter path to ZIP/RAR/7Z file: ")
            if not archive_path.lower().endswith(('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2')):
                print("Warning: File doesn't appear to be an archive, but proceeding with direct embed.")
            use_direct_embed = True
            direct_file = archive_path
            
        else:
            print("Invalid choice. Using single file option.")
            file_path = self.ask_file_path("Enter path to file to hide: ")
            files_to_hide[file_path] = os.path.basename(file_path)
        
        # Calculate total size
        if use_direct_embed:
            total_size = os.path.getsize(direct_file)
            total_size_gb = total_size / (1024 ** 3)
            print(f"\n📊 Archive size: {total_size_gb:.2f} GB (direct embed - no ZIP overhead)")
        else:
            total_size = sum(os.path.getsize(f) for f in files_to_hide.keys())
            total_size_gb = total_size / (1024 ** 3)
            print(f"\n📊 Total size to hide: {total_size_gb:.2f} GB (will be zipped)")
        
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
        if use_direct_embed:
            if split_size:
                self.create_split_polyglot_direct(video_path, direct_file, output_base, split_size)
            else:
                self.create_single_polyglot_direct(video_path, direct_file, output_base)
        else:
            if split_size:
                self.create_split_polyglot(video_path, files_to_hide, output_base, split_size)
            else:
                self.create_single_polyglot(video_path, files_to_hide, output_base)
    
    def create_single_polyglot(self, video_path, files_to_hide, output_base):
        """Create a single polyglot video (streaming, fast, with progress bar)"""
        from io import BytesIO
        import time
        print(f"\nCreating single polyglot video (streaming)...")

        output_path = f"{output_base}.mp4"

        video_size = os.path.getsize(video_path)
        chunk_size = 16 * 1024 * 1024  # 16MB
        copied = 0

        # Stream video to output with progress
        with open(video_path, 'rb') as v_in, open(output_path, 'wb') as out:
            print("Copying video data:")
            start_time = time.time()
            while True:
                chunk = v_in.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                copied += len(chunk)
                percent = copied / video_size * 100
                speed = copied / (time.time() - start_time + 1e-6) / (1024*1024)
                print(f"\r  {percent:.1f}% ({copied // (1024*1024)} MB / {video_size // (1024*1024)} MB) at {speed:.1f} MB/s", end="")
            print()

            # Create ZIP in memory (still needed for now, but can be optimized further)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zipf:
                for file_path, arcname in files_to_hide.items():
                    zipf.write(file_path, arcname)
                    print(f"Added: {arcname}")
            zip_buffer.seek(0)
            zip_size = len(zip_buffer.getvalue())
            copied_zip = 0
            print("Copying ZIP data:")
            start_time = time.time()
            while True:
                chunk = zip_buffer.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                copied_zip += len(chunk)
                percent = copied_zip / zip_size * 100
                speed = copied_zip / (time.time() - start_time + 1e-6) / (1024*1024)
                print(f"\r  {percent:.1f}% ({copied_zip // (1024*1024)} MB / {zip_size // (1024*1024)} MB) at {speed:.1f} MB/s", end="")
            print()

        # Calculate checksum
        checksum = self.calculate_md5(output_path)

        print(f"\n✅ Polyglot video created: {output_path}")
        print(f"📊 Size: {self.get_file_size_gb(output_path):.2f} GB")
        print(f"🔒 Checksum: {checksum}")
        print(f"📦 Contains: {len(files_to_hide)} hidden files")

        # Create recovery info
        self.create_recovery_info(output_path, checksum, list(files_to_hide.values()))
    
    def create_single_polyglot_direct(self, video_path, archive_path, output_base):
        """Create single polyglot by directly appending archive (no ZIP wrapper)"""
        import time
        print(f"\nCreating single polyglot video (direct embed - faster!)...")

        output_path = f"{output_base}.mp4"
        
        # Stream video + archive directly
        chunk_size = 16 * 1024 * 1024  # 16MB
        
        with open(output_path, 'wb') as out:
            # Copy video
            video_size = os.path.getsize(video_path)
            copied = 0
            start_time = time.time()
            print("Copying video data:")
            with open(video_path, 'rb') as v_in:
                while True:
                    chunk = v_in.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    copied += len(chunk)
                    percent = copied / video_size * 100
                    speed = copied / (time.time() - start_time + 1e-6) / (1024*1024)
                    print(f"\r  {percent:.1f}% ({copied // (1024*1024)} MB / {video_size // (1024*1024)} MB) at {speed:.1f} MB/s", end="")
            print()
            
            # Copy archive directly
            archive_size = os.path.getsize(archive_path)
            copied = 0
            start_time = time.time()
            print("Copying archive data:")
            with open(archive_path, 'rb') as a_in:
                while True:
                    chunk = a_in.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
                    copied += len(chunk)
                    percent = copied / archive_size * 100
                    speed = copied / (time.time() - start_time + 1e-6) / (1024*1024)
                    print(f"\r  {percent:.1f}% ({copied // (1024*1024)} MB / {archive_size // (1024*1024)} MB) at {speed:.1f} MB/s", end="")
            print()

        # Calculate checksum
        checksum = self.calculate_md5(output_path)
        archive_name = os.path.basename(archive_path)

        print(f"\n✅ Polyglot video created: {output_path}")
        print(f"📊 Size: {self.get_file_size_gb(output_path):.2f} GB")
        print(f"🔒 Checksum: {checksum}")
        print(f"📦 Contains: {archive_name} (direct embed)")
        print(f"⚡ No ZIP overhead - maximum speed!")

        # Create recovery info for direct embed
        self.create_recovery_info_direct(output_path, checksum, archive_name)
    
    def create_split_polyglot(self, video_path, files_to_hide, output_base, split_size_gb):
        """Create split polyglot videos (disk-based for massive files)"""
        import math
        import time
        print(f"\nCreating split polyglot videos ({split_size_gb}GB each)... (disk streaming)")

        # Write ZIP to disk (not memory)
        temp_zip_path = f"{output_base}_temp.zip"
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_STORED) as zipf:
            for file_path, arcname in files_to_hide.items():
                zipf.write(file_path, arcname)

        zip_size = os.path.getsize(temp_zip_path)
        split_size = int(split_size_gb * 1024 ** 3)
        num_parts = math.ceil(zip_size / split_size)

        print(f"Splitting {zip_size / (1024**3):.2f} GB into {num_parts} parts...")

        polyglot_videos = []
        part_checksums = []

        for i in range(num_parts):
            part_num = i + 1
            start = i * split_size
            end = min((i + 1) * split_size, zip_size)
            part_len = end - start
            output_path = f"{output_base}_part{part_num}.mp4"
            print(f"Writing {output_path} ({part_len / (1024**3):.2f} GB)...")
            
            with open(video_path, 'rb') as v_in, open(output_path, 'wb') as out:
                # Copy video
                shutil.copyfileobj(v_in, out, length=16*1024*1024)
                # Copy ZIP part
                with open(temp_zip_path, 'rb') as zip_in:
                    zip_in.seek(start)
                    copied = 0
                    chunk_size = 16*1024*1024
                    start_time = time.time()
                    while copied < part_len:
                        to_read = min(chunk_size, part_len - copied)
                        chunk = zip_in.read(to_read)
                        if not chunk:
                            break
                        out.write(chunk)
                        copied += len(chunk)
                        percent = copied / part_len * 100
                        speed = copied / (time.time() - start_time + 1e-6) / (1024*1024)
                        print(f"\r  {percent:.1f}% ({copied // (1024*1024)} MB / {part_len // (1024*1024)} MB) at {speed:.1f} MB/s", end="")
                    print()
            
            # Calculate checksum for this part
            with open(output_path, 'rb') as f:
                f.seek(os.path.getsize(video_path))
                part_data = f.read()
                part_checksums.append(hashlib.md5(part_data).hexdigest())
            
            polyglot_videos.append(output_path)
            print(f"✅ Created {output_path} ({part_len / (1024**3):.2f} GB)")

        # Original checksum (of the full ZIP)
        original_checksum = self.calculate_md5(temp_zip_path)

        # Create recovery package
        self.create_split_recovery_package(output_base, polyglot_videos, original_checksum, part_checksums)

        print(f"\n🎉 Created {num_parts} polyglot videos!")
        print(f"🔒 Original checksum: {original_checksum}")
        print("💾 Recovery package created with extraction tools")

        # Clean up temp zip
        try:
            os.remove(temp_zip_path)
        except Exception:
            pass
    
    def create_split_polyglot_direct(self, video_path, archive_path, output_base, split_size_gb):
        """Create split polyglot by directly splitting archive (no ZIP wrapper)"""
        import math
        import time
        print(f"\nCreating split polyglot videos (direct embed - {split_size_gb}GB each)...")

        archive_size = os.path.getsize(archive_path)
        split_size = int(split_size_gb * 1024 ** 3)
        num_parts = math.ceil(archive_size / split_size)

        print(f"Splitting {archive_size / (1024**3):.2f} GB into {num_parts} parts...")

        polyglot_videos = []
        part_checksums = []

        for i in range(num_parts):
            part_num = i + 1
            start = i * split_size
            end = min((i + 1) * split_size, archive_size)
            part_len = end - start
            output_path = f"{output_base}_part{part_num}.mp4"
            print(f"Writing {output_path} ({part_len / (1024**3):.2f} GB)...")
            
            with open(video_path, 'rb') as v_in, open(output_path, 'wb') as out:
                # Copy video
                shutil.copyfileobj(v_in, out, length=16*1024*1024)
                
                # Copy archive part directly
                with open(archive_path, 'rb') as a_in:
                    a_in.seek(start)
                    copied = 0
                    chunk_size = 16*1024*1024
                    start_time = time.time()
                    while copied < part_len:
                        to_read = min(chunk_size, part_len - copied)
                        chunk = a_in.read(to_read)
                        if not chunk:
                            break
                        out.write(chunk)
                        copied += len(chunk)
                        percent = copied / part_len * 100
                        speed = copied / (time.time() - start_time + 1e-6) / (1024*1024)
                        print(f"\r  {percent:.1f}% ({copied // (1024*1024)} MB / {part_len // (1024*1024)} MB) at {speed:.1f} MB/s", end="")
                    print()
            
            # Calculate checksum for this part's data only
            with open(output_path, 'rb') as f:
                f.seek(os.path.getsize(video_path))
                part_data = f.read()
                part_checksums.append(hashlib.md5(part_data).hexdigest())
            
            polyglot_videos.append(output_path)
            print(f"✅ Created {output_path}")

        # Original checksum
        original_checksum = self.calculate_md5(archive_path)

        # Create recovery package
        self.create_split_recovery_package_direct(output_base, polyglot_videos, original_checksum, part_checksums, os.path.basename(archive_path))

        print(f"\n🎉 Created {num_parts} polyglot videos!")
        print(f"🔒 Original checksum: {original_checksum}")
        print(f"⚡ Direct embed - maximum speed!")
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
    
    def create_recovery_info_direct(self, polyglot_path, checksum, archive_name):
        """Create recovery information for direct embedded archive"""
        recovery_file = f"{os.path.splitext(polyglot_path)[0]}_recovery.txt"
        
        content = f"""POLYGLOT RECOVERY INFORMATION (DIRECT EMBED)
===============================================

Polyglot File: {polyglot_path}
Checksum: {checksum}
Creation Date: {os.path.getctime(polyglot_path)}
Size: {self.get_file_size_gb(polyglot_path):.2f} GB

EMBEDDED ARCHIVE: {archive_name}
TYPE: Direct embed (no ZIP wrapper)

EXTRACTION INSTRUCTIONS:

Method 1: Using 7-Zip (Recommended)
-----------------------------------
7z x {polyglot_path}

Method 2: Using Python
----------------------
# Find archive start (look for archive signature)
import os
with open('{polyglot_path}', 'rb') as f:
    data = f.read()

# Common archive signatures
signatures = {{
    b'PK': 'zip',
    b'Rar!': 'rar', 
    b'7z': '7z',
    b'\\x1f\\x8b': 'gz'
}}

for sig, ext in signatures.items():
    pos = data.find(sig)
    if pos != -1:
        with open(f'extracted.{{ext}}', 'wb') as out:
            out.write(data[pos:])
        print(f"Extracted to extracted.{{ext}}")
        break

Method 3: Manual (Hex Editor)
-----------------------------
1. Open {polyglot_path} in hex editor
2. Find archive signature (PK for ZIP, Rar! for RAR, etc.)
3. Copy everything from signature to end
4. Save as new file with proper extension

Method 4: Command Line (Linux/Mac)
----------------------------------
# Find video size first, then extract remainder
video_size=$(ffprobe -v quiet -show_entries format=size -of csv=p=0 original_video.mp4)
dd if={polyglot_path} of=extracted_archive bs=1 skip=$video_size
"""
        
        with open(recovery_file, 'w') as f:
            f.write(content)
        
        print(f"📋 Recovery info: {recovery_file}")
    
    def create_split_recovery_package_direct(self, output_base, polyglot_videos, original_checksum, part_checksums, archive_name):
        """Create recovery package for direct embedded split archives"""
        recovery_zip = f"{output_base}_recovery.zip"
        
        # Create instructions
        instructions = f"""SPLIT POLYGLOT RECOVERY (DIRECT EMBED)
=====================================

Archive Name: {archive_name}
Original Checksum: {original_checksum}
Number of Parts: {len(polyglot_videos)}
Type: Direct embed (no ZIP wrapper)

PARTS AND CHECKSUMS:
"""
        for i, (video, checksum) in enumerate(zip(polyglot_videos, part_checksums)):
            instructions += f"Part {i+1}: {video} (MD5: {checksum})\n"
        
        instructions += f"""
RECOVERY METHODS:

1. AUTOMATIC:
   - Extract this ZIP
   - Run: python recover_direct_split.py

2. MANUAL COMBINATION:
   - Extract archive data from each part:
     python extract_direct_part.py {polyglot_videos[0]}
     python extract_direct_part.py {polyglot_videos[1]}
     (repeat for all parts)
   
   - Combine parts:
     cat part1.bin part2.bin part3.bin > complete_archive
     # Or on Windows: copy /b part1.bin + part2.bin + part3.bin complete_archive
   
   - Rename with proper extension based on archive type

3. QUICK (if 7z available):
   - Sometimes 7z can handle split polyglots directly
   - Try: 7z x {polyglot_videos[0]}
"""
        
        with open('recovery_instructions.txt', 'w') as f:
            f.write(instructions)
        self.temp_files.append('recovery_instructions.txt')
        
        # Create recovery script for direct embed
        recovery_script = f"""#!/usr/bin/env python3
import sys
import glob
import os

def recover_direct_split():
    # Find all part files
    parts = sorted(glob.glob("{output_base}_part*.mp4"))
    if not parts:
        print("No part files found!")
        return False
    
    print(f"Found {{len(parts)}} parts")
    
    # Get video size from first part (assume all videos same size)
    video_size = 0
    with open(parts[0], 'rb') as f:
        # Try to find end of video data (heuristic: look for common video patterns)
        data = f.read(1024*1024)  # Read first MB
        # This is a simple heuristic - in practice you'd want more sophisticated detection
        
    # For now, assume we need to skip a certain amount from each video
    # User should adjust this based on their video template size
    print("Note: You may need to adjust video_size_to_skip in this script")
    video_size_to_skip = input("Enter video template size in bytes (or 0 to auto-detect): ")
    try:
        video_size_to_skip = int(video_size_to_skip)
    except:
        video_size_to_skip = 0
    
    # Extract and combine
    with open('recovered_archive', 'wb') as outfile:
        for i, part in enumerate(parts):
            print(f"Processing {{part}}...")
            with open(part, 'rb') as f:
                if video_size_to_skip > 0:
                    f.seek(video_size_to_skip)
                else:
                    # Auto-detect: skip to a reasonable position
                    file_size = os.path.getsize(part)
                    f.seek(file_size // 10)  # Skip first 10% as rough estimate
                
                data = f.read()
                outfile.write(data)
    
    print("Recovery complete! File: recovered_archive")
    print("Rename to proper extension (.zip, .rar, .7z, etc.)")
    return True

if __name__ == "__main__":
    recover_direct_split()
"""
        
        with open('recover_direct_split.py', 'w') as f:
            f.write(recovery_script)
        self.temp_files.append('recover_direct_split.py')
        
        # Create extraction script for individual parts
        extract_script = """#!/usr/bin/env python3
import sys
import os

def extract_direct_part(video_path):
    if len(sys.argv) < 2:
        print("Usage: python extract_direct_part.py <video_file>")
        return
        
    video_path = sys.argv[1]
    
    # Simple approach: assume video is first portion, archive is remainder
    file_size = os.path.getsize(video_path)
    
    # Ask user for video size to skip
    video_size = input(f"Enter video size to skip (file is {file_size} bytes): ")
    try:
        video_size = int(video_size)
    except:
        video_size = file_size // 10  # Rough estimate
    
    output_path = video_path.replace('.mp4', '.bin')
    with open(video_path, 'rb') as f:
        f.seek(video_size)
        data = f.read()
        
    with open(output_path, 'wb') as f:
        f.write(data)
    
    print(f"Extracted to {output_path}")

if __name__ == "__main__":
    extract_direct_part(sys.argv[1] if len(sys.argv) > 1 else None)
"""
        
        with open('extract_direct_part.py', 'w') as f:
            f.write(extract_script)
        self.temp_files.append('extract_direct_part.py')
        
        # Create recovery ZIP
        with zipfile.ZipFile(recovery_zip, 'w') as zipf:
            for file in ['recovery_instructions.txt', 'recover_direct_split.py', 'extract_direct_part.py']:
                zipf.write(file)
        
        print(f"📦 Recovery package: {recovery_zip}")
    
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
