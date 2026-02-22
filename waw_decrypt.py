import os
import sys
import struct
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

# Function to parse the XOR table from the .rs file
def load_xor_table(rs_file_path):
    with open(rs_file_path, 'r') as f:
        content = f.read()
    # Find all hex values (0xA6, etc.)
    hex_values = re.findall(r'0x[0-9A-Fa-f]{1,2}', content)
    return [int(v, 16) for v in hex_values]

# This is the worker function that runs on each process
def decrypt_single_wav(args):
    src_path, dst_path, xor_table = args
    
    try:
        with open(src_path, 'rb') as f:
            dat = bytearray(f.read())
        
        # Header validation
        if dat[:4] != b"RIFF" or dat[8:12] != b"WAVE":
            return f"Skipped (Invalid header): {src_path.name}"

        chunk_offset = 12
        found_datx = False

        while (chunk_offset + 8) < len(dat):
            chunk_name = dat[chunk_offset:chunk_offset + 4]
            chunk_len = struct.unpack('<I', dat[chunk_offset + 4:chunk_offset + 8])[0]

            if chunk_name != b"datx":
                chunk_offset += chunk_len + 8
                continue

            found_datx = True
            # Fixup: rename 'datx' to 'data'
            dat[chunk_offset + 3] = ord('a') 
            
            ddat_off = chunk_offset + 8
            # XOR decryption loop
            for i in range(ddat_off, ddat_off + chunk_len):
                # The decryption formula from main.rs
                idx = (((i & 0xFF) + (i >> 12)) & 7) + (i & 0xFF8)
                dat[i] ^= xor_table[idx % 4096]

            chunk_offset += chunk_len + 8

        if found_datx:
            os.makedirs(dst_path.parent, exist_ok=True)
            with open(dst_path, 'wb') as f:
                f.write(dat)
            return f"Decrypted: {src_path.name}"
        else:
            return f"No 'datx' found: {src_path.name}"
            
    except Exception as e:
        return f"Error processing {src_path.name}: {e}"

def main():
    if len(sys.argv) != 2:
        print("Usage: python decrypt_parallel.py <data_folder>")
        return

    src_root = Path(sys.argv[1])
    # Assume xor_table.txt is in the same directory as the script
    xor_table_path = Path(__file__).parent / "xor_table.txt"
    
    if not xor_table_path.exists():
        print(f"Error: {xor_table_path} not found in script directory.")
        return
        
    print("Loading XOR table...")
    xor_table = load_xor_table(xor_table_path)
    
    dst_root = src_root.parent / "data_wav"
    tasks = []

    print("Scanning for files...")
    for root, _, files in os.walk(src_root):
        for file in files:
            if file.lower().endswith(".waw"):
                src_path = Path(root) / file
                relative = src_path.relative_to(src_root)
                
                # Logic for filename extension conversion
                if str(relative).lower().endswith(".bak"):
                    target_filename = relative.with_suffix("").with_suffix(".wav.bak")
                else:
                    target_filename = relative.with_suffix(".wav")
                
                dst_path = dst_root / target_filename
                tasks.append((src_path, dst_path, xor_table))

    print(f"Starting parallel decryption of {len(tasks)} files...")
    
    # Using ProcessPoolExecutor to use multiple CPU cores
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(decrypt_single_wav, tasks))

    # Optional: Print results summary
    for res in results:
        print(res)

if __name__ == "__main__":
    # Required for multiprocessing on Windows
    main()