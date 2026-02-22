import os
import struct
import sys

def load_tga_pixels(path):
    with open(path, 'rb') as f:
        f.seek(12)
        w, h = struct.unpack('<HH', f.read(4))
        f.seek(18)
        return w, h, f.read()

def write_tga_sheet(path, width, height, data):
    with open(path, 'wb') as f:
        header = bytearray([0]*18)
        header[2], header[12], header[13], header[14], header[15], header[16], header[17] = 2, width & 0xFF, width >> 8, height & 0xFF, height >> 8, 32, 32
        f.write(header)
        f.write(data)

def assemble_sheet(bin_path, sprite_dir, out_dir):
    prefix = os.path.splitext(os.path.basename(bin_path))[0]
    with open(bin_path, 'rb') as f:
        bin_data = f.read()

    toc_offset = 0x01BC
    name_ptr = 8 + struct.unpack('<I', bin_data[0:4])[0]
    sheets = []
    
    while toc_offset + 8 <= len(bin_data):
        x, y, w, h = struct.unpack('<hhhh', bin_data[toc_offset:toc_offset+8])
        if w <= 0 or h <= 0: break
        
        end_name = bin_data.find(b'\x00', name_ptr)
        sprite_name = bin_data[name_ptr:end_name].decode('ascii', errors='ignore')
        tga_path = os.path.join(sprite_dir, f"{prefix}_{sprite_name}.tga")

        if os.path.exists(tga_path):
            sw, sh, pixels = load_tga_pixels(tga_path)
            sheet_idx, curr_y = 0, y
            while curr_y >= 1024:
                curr_y -= 1024
                sheet_idx += 1
            
            while len(sheets) <= sheet_idx:
                sheets.append(bytearray([0] * (1024 * 1024 * 4)))

            for row in range(h):
                for col in range(w):
                    src_idx = (row * w + col) * 4
                    target_idx = ((curr_y + row) * 1024 + (x + col)) * 4
                    sheets[sheet_idx][target_idx : target_idx + 4] = pixels[src_idx : src_idx + 4]
        
        toc_offset += 8
        name_ptr = end_name + 4

    for idx, sheet_data in enumerate(sheets):
        out_name = f"{prefix}{idx}.tga"
        write_tga_sheet(os.path.join(out_dir, out_name), 1024, 1024, sheet_data)
        print(f"  [OK] Assembled {out_name}")

def main(bin_dir, sprite_dir, out_dir):
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    bins = [f for f in os.listdir(bin_dir) if f.lower().endswith('.bin')]
    for b in bins:
        assemble_sheet(os.path.join(bin_dir, b), sprite_dir, out_dir)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} [bin_dir] [sprite_dir] [output_dir]")
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])