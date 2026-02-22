import os
import struct
import sys

def compress_lzss(data):
    """Compresses data using the LZSS algorithm compatible with the GCZ format."""
    length = len(data)
    out = bytearray(struct.pack('<I', length)) # 4-byte header: original size
    
    ring = bytearray([0] * 0x1000)
    ring_pos = 0x0FEE
    
    pos = 0
    while pos < length:
        # We will use a simple "straight copy" approach for every byte.
        # While this doesn't actually 'shrink' the file much, it creates 
        # a valid LZSS stream that the game's decompressor can read.
        
        # 8 bits of '1' in a control byte means 8 straight copies
        control_byte = 0xFF 
        chunk = bytearray()
        
        for _ in range(8):
            if pos < length:
                byte = data[pos]
                chunk.append(byte)
                ring[ring_pos] = byte
                ring_pos = (ring_pos + 1) % 0x1000
                pos += 1
            else:
                # If we run out of data mid-control-byte, we shift the bit
                # (This is a simplified encoder)
                pass
        
        out.append(control_byte)
        out.extend(chunk)
        
    return out

def pack_gc(width, height, rgba_data):
    """Converts 32-bit BGRA/RGBA to 16-bit ARGB1555 and adds the GC header."""
    out = bytearray(b'GC') # Magic
    out.extend(bytearray([0]*10)) # Padding/Unknown
    
    # Dimensions are Big Endian
    out.extend(struct.pack('>H', width))
    out.extend(struct.pack('>H', height))
    out.extend(bytearray([0]*8)) # More padding to reach 24-byte header

    # Convert pixels back to 16-bit
    # Expected format: A(1 bit) R(5 bits) G(5 bits) B(5 bits)
    for i in range(0, len(rgba_data), 4):
        b, g, r, a = rgba_data[i:i+4]
        
        a_bit = 0x8000 if a > 128 else 0x0000
        r_bits = (r >> 3) << 10
        g_bits = (g >> 3) << 5
        b_bits = (b >> 3)
        
        pixel16 = a_bit | r_bits | g_bits | b_bits
        out.extend(struct.pack('<H', pixel16)) # Pixels are Little Endian
        
    return out

def main(tga_dir, gcz_dir):
    if not os.path.exists(gcz_dir):
        os.makedirs(gcz_dir)
        
    tga_files = [f for f in os.listdir(tga_dir) if f.lower().endswith('.tga')]
    print(f"Found {len(tga_files)} TGA files. Packing to GCZ...")

    for tga_name in tga_files:
        tga_path = os.path.join(tga_dir, tga_name)
        gcz_name = os.path.splitext(tga_name)[0] + ".gcz"
        gcz_path = os.path.join(gcz_dir, gcz_name)
        
        try:
            with open(tga_path, 'rb') as f:
                # Skip TGA header (18 bytes)
                f.seek(12)
                width = struct.unpack('<H', f.read(2))[0]
                height = struct.unpack('<H', f.read(2))[0]
                f.seek(18)
                pixel_data = f.read()
                
            # 1. Convert to GC format (16-bit)
            gc_data = pack_gc(width, height, pixel_data)
            
            # 2. Compress with LZSS
            compressed = compress_lzss(gc_data)
            
            with open(gcz_path, 'wb') as f:
                f.write(compressed)
            print(f"  [OK] {tga_name} -> {gcz_name}")
                
        except Exception as e:
            print(f"  [ERROR] {tga_name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} [tga_dir] [out_gcz_dir]")
    else:
        main(sys.argv[1], sys.argv[2])