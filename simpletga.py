import os
import struct
import sys

class Image:
    def __init__(self, width=0, height=0, planes=None):
        self.width = width
        self.height = height
        self.planes = planes

def expand_lzss(data):
    """Decompress GCZ LZSS data."""
    # Header = 32 bit unpacked file length
    unpacked_len = struct.unpack('<I', data[:4])[0]
    out = bytearray()
    ring = bytearray([0] * 0x1000)
    ring_pos = 0x0FEE
    in_ptr = 4
    control_word = 1

    while len(out) < unpacked_len:
        if control_word == 1:
            # Read a control byte
            control_word = 0x100 | data[in_ptr]
            in_ptr += 1

        # Decode a byte according to the current control byte bit
        if control_word & 1:
            # Straight copy
            byte = data[in_ptr]
            in_ptr += 1
            out.append(byte)
            ring[ring_pos] = byte
            ring_pos = (ring_pos + 1) % 0x1000
        else:
            # Reference to data in ring buffer
            cmd1 = data[in_ptr]
            cmd2 = data[in_ptr + 1]
            in_ptr += 2

            chunk_len = (cmd2 & 0x0F) + 3
            chunk_offset = ((cmd2 & 0xF0) << 4) | cmd1

            for _ in range(chunk_len):
                if len(out) >= unpacked_len: break
                byte = ring[chunk_offset]
                out.append(byte)
                ring[ring_pos] = byte
                
                # Update counters
                chunk_offset = (chunk_offset + 1) % 0x1000
                ring_pos = (ring_pos + 1) % 0x1000
        
        # Get next control bit
        control_word >>= 1
    
    return out

def unpack_gc(data):
    """Converts raw GC texture data to 32-bit BGRA."""
    magic = struct.unpack('<H', data[0:2])[0]
    if magic != 0x4347: # "GC"
        return None

    # Dimensions are Big Endian (swab16)
    raw_width = struct.unpack('>H', data[12:14])[0]
    raw_height = struct.unpack('>H', data[14:16])[0]
    
    # Clamp W/H as per original C logic
    width = min(raw_width, 1024)
    height = min(raw_height, 1024)
    
    pixel_data = data[24:]
    npixels = width * height
    out_planes = bytearray()

    # Check if 32-bit (Deep) or 16-bit (Shallow)
    # Original C logic used out_sz > npixels * 4
    if len(data) > npixels * 4:
        # Deep image (32-bit) - copy directly
        out_planes = pixel_data[:npixels * 4]
    else:
        # Shallow image (16-bit ARGB1555) to 32-bit BGRA
        pixels = struct.unpack(f'<{npixels}H', pixel_data[:npixels*2])
        for p in pixels:
            # ARGB1555: A(1) R(5) G(5) B(5)
            b = (p & 0x1F) << 3
            g = ((p >> 5) & 0x1F) << 3
            r = ((p >> 10) & 0x1F) << 3
            a = 0xFF if (p & 0x8000) else 0x00
            # TGA standard expects BGRA
            out_planes.extend([b, g, r, a])
            
    return Image(width, height, out_planes)

def write_tga(path, width, height, data):
    """Writes a standard 32-bit TGA file."""
    with open(path, 'wb') as f:
        header = bytearray([0]*18)
        header[2] = 2           # Uncompressed true-color
        header[12] = width & 0xFF
        header[13] = (width >> 8) & 0xFF
        header[14] = height & 0xFF
        header[15] = (height >> 8) & 0xFF
        header[16] = 32         # 32 bits per pixel
        header[17] = 32         # Descriptor (origin upper-left)
        f.write(header)
        f.write(data)

def main(in_dir, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith('.gcz')]
    print(f"Found {len(files)} GCZ files. Exporting full sheets...")

    for gcz_name in files:
        full_path = os.path.join(in_dir, gcz_name)
        out_name = os.path.splitext(gcz_name)[0] + ".tga"
        out_path = os.path.join(out_dir, out_name)
        
        try:
            with open(full_path, 'rb') as f:
                compressed_data = f.read()
            
            raw_gc = expand_lzss(compressed_data)
            img = unpack_gc(raw_gc)
            
            if img:
                write_tga(out_path, img.width, img.height, img.planes)
                print(f"  [OK] {gcz_name} -> {out_name}")
            else:
                print(f"  [FAIL] {gcz_name}: Invalid Header")
                
        except Exception as e:
            print(f"  [ERROR] {gcz_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} [indir] [outdir]")
    else:
        main(sys.argv[1], sys.argv[2])