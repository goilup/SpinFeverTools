import os
import sys
import struct
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def load_xor_table(rs_file_path):
    """Parses the 4096-byte XOR table from the provided .rs file."""
    try:
        with open(rs_file_path, 'r') as f:
            content = f.read()
        hex_values = re.findall(r'0x[0-9A-Fa-f]{1,2}', content)
        table = [int(v, 16) for v in hex_values]
        if len(table) != 4096:
            print(f"Warning: Table length is {len(table)}, expected 4096.")
        return table
    except Exception as e:
        print(f"Error loading XOR table: {e}")
        sys.exit(1)

def encrypt_single_wav(args):
    """
    Worker function:
    - Finds 'data' chunks.
    - XORs the data.
    - Renames 'data' to 'datx'.
    - Saves as .waw.
    """
    src_path, dst_path, xor_table = args
    
    try:
        with open(src_path, 'rb') as f:
            dat = bytearray(f.read())
        
        # Header validation (RIFF WAVE)
        if dat[:4] != b"RIFF" or dat[8:12] != b"WAVE":
            return f"Skipped (Not a valid WAV): {src_path.name}"

        chunk_offset = 12
        found_data = False

        while (chunk_offset + 8) < len(dat):
            chunk_name = dat[chunk_offset:chunk_offset + 4]
            chunk_len = struct.unpack('<I', dat[chunk_offset + 4:chunk_offset + 8])[0]

            # We look for 'data' chunks to encrypt into 'datx'
            if chunk_name != b"data":
                chunk_offset += chunk_len + 8
                continue

            found_data = True
            
            # Change 'data' -> 'datx'
            dat[chunk_offset + 3] = ord('x') 
            
            # Apply XOR encryption
            ddat_off = chunk_offset + 8
            for i in range(ddat_off, ddat_off + chunk_len):
                # Use the exact indexing logic from the original source
                idx = (((i & 0xFF) + (i >> 12)) & 7) + (i & 0xFF8)
                dat[i] ^= xor_table[idx % 4096]

            chunk_offset += chunk_len + 8

        if found_data:
            os.makedirs(dst_path.parent, exist_ok=True)
            with open(dst_path, 'wb') as f:
                f.write(dat)
            return f"Encrypted to .waw: {src_path.name}"
        else:
            return f"No 'data' chunk found in: {src_path.name}"
            
    except Exception as e:
        return f"Error processing {src_path.name}: {e}"

def main():
    if len(sys.argv) != 2:
        print("Usage: python wav_to_waw.py <uncrypto_folder>")
        return

    src_root = Path(sys.argv[1])
    # Ensure xor_table.txt is in the same directory as this script
    xor_table_path = Path(__file__).parent / "xor_table.txt"
    
    if not xor_table_path.exists():
        print(f"Error: Could not find 'xor_table.txt' in {xor_table_path.parent}")
        return
        
    xor_table = load_xor_table(xor_table_path)
    
    # Destination folder is 'data_waw' next to the source folder
    dst_root = src_root.parent / "data_waw"
    tasks = []

    print(f"Scanning {src_root} for .wav files...")
    for root, _, files in os.walk(src_root):
        for file in files:
            if file.lower().endswith(".wav"):
                src_path = Path(root) / file
                relative = src_path.relative_to(src_root)
                
                # Convert filename extension back to .waw
                # Handles files like 'sound.wav' -> 'sound.waw'
                # Also handles 'sound.wav.bak' if they exist
                if str(relative).lower().endswith(".wav.bak"):
                    target_filename = relative.with_suffix("").with_suffix(".waw.bak")
                else:
                    target_filename = relative.with_suffix(".waw")
                
                dst_path = dst_root / target_filename
                tasks.append((src_path, dst_path, xor_table))

    if not tasks:
        print("No .wav files found to process.")
        return

    print(f"Processing {len(tasks)} files using all CPU cores...")
    
    with ProcessPoolExecutor() as executor:
        # Results are gathered as they complete
        results = list(executor.map(encrypt_single_wav, tasks))

    # Print summary of actions
    for res in results:
        print(res)
    print(f"\nFinished. Files saved to: {dst_root}")

if __name__ == "__main__":
    main()