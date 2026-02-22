import os
import struct
import sys
import re

class Image:
    def __init__(self, width=0, height=0, planes=None):
        self.width = width
        self.height = height
        self.planes = planes

def expand_lzss(data):
    unpacked_len = struct.unpack('<I', data[:4])[0]
    out = bytearray()
    ring = bytearray([0] * 0x1000)
    ring_pos = 0x0FEE
    in_ptr = 4
    control_word = 1
    while len(out) < unpacked_len:
        if control_word == 1:
            control_word = 0x100 | data[in_ptr]
            in_ptr += 1
        if control_word & 1:
            byte = data[in_ptr]
            in_ptr += 1
            out.append(byte)
            ring[ring_pos] = byte
            ring_pos = (ring_pos + 1) % 0x1000
        else:
            cmd1, cmd2 = data[in_ptr], data[in_ptr + 1]
            in_ptr += 2
            chunk_len = (cmd2 & 0x0F) + 3
            chunk_offset = ((cmd2 & 0xF0) << 4) | cmd1
            for _ in range(chunk_len):
                if len(out) >= unpacked_len: break
                byte = ring[chunk_offset]
                out.append(byte)
                ring[ring_pos] = byte
                chunk_offset = (chunk_offset + 1) % 0x1000
                ring_pos = (ring_pos + 1) % 0x1000
        control_word >>= 1
    return out

def unpack_gc(data):
    magic = struct.unpack('<H', data[0:2])[0]
    if magic != 0x4347: return None
    w = min(struct.unpack('>H', data[12:14])[0], 1024)
    h = min(struct.unpack('>H', data[14:16])[0], 1024)
    pixel_data = data[24:]
    npixels = w * h
    out_planes = bytearray()
    if len(data) > npixels * 4:
        out_planes = pixel_data[:npixels * 4]
    else:
        pixels = struct.unpack(f'<{npixels}H', pixel_data[:npixels*2])
        for p in pixels:
            b, g, r = (p & 0x1F) << 3, ((p >> 5) & 0x1F) << 3, ((p >> 10) & 0x1F) << 3
            a = 0xFF if (p & 0x8000) else 0x00
            out_planes.extend([b, g, r, a])
    return Image(w, h, out_planes)

def write_tga(path, width, height, data):
    with open(path, 'wb') as f:
        header = bytearray([0]*18)
        header[2], header[12], header[13], header[14], header[15], header[16], header[17] = 2, width & 0xFF, width >> 8, height & 0xFF, height >> 8, 32, 32
        f.write(header)
        f.write(data)

def process_set(bin_file, gcz_list, out_dir):
    prefix = os.path.splitext(os.path.basename(bin_file))[0]
    print(f"Processing Set: {prefix} with {len(gcz_list)} files")
    images = []
    for gcz in gcz_list:
        with open(gcz, 'rb') as f:
            images.append(unpack_gc(expand_lzss(f.read())))

    with open(bin_file, 'rb') as f:
        data = f.read()

    toc_offset = 0x01BC
    name_ptr = 8 + struct.unpack('<I', data[0:4])[0]
    
    while toc_offset + 8 <= len(data):
        x, y, w, h = struct.unpack('<hhhh', data[toc_offset:toc_offset+8])
        if w <= 0 or h <= 0: break
        
        end_name = data.find(b'\x00', name_ptr)
        sprite_name = data[name_ptr:end_name].decode('ascii', errors='ignore')
        
        img_idx, curr_y = 0, y
        while img_idx < len(images) and curr_y >= images[img_idx].height:
            curr_y -= images[img_idx].height
            img_idx += 1
        
        if img_idx < len(images):
            out_path = os.path.join(out_dir, f"{prefix}_{sprite_name}.tga")
            img, slice_data = images[img_idx], bytearray()
            temp_y = curr_y
            for _ in range(h):
                if temp_y >= img.height:
                    img_idx += 1
                    if img_idx >= len(images): break
                    img, temp_y = images[img_idx], 0
                start = (temp_y * img.width + x) * 4
                slice_data.extend(img.planes[start : start + (w * 4)])
                temp_y += 1
            write_tga(out_path, w, h, slice_data)
        
        toc_offset += 8
        name_ptr = end_name + 4

def main(in_dir, out_dir):
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    files = os.listdir(in_dir)
    bins = [f for f in files if f.lower().endswith('.bin')]
    for b in bins:
        base_name = os.path.splitext(b)[0]
        # Strict Regex anchoring to prevent similar name overlap
        pattern = re.compile(r'^' + re.escape(base_name) + r'(\d+)\.gcz$', re.IGNORECASE)
        matched_gczs = sorted([(int(pattern.match(f).group(1)), os.path.join(in_dir, f)) 
                              for f in files if pattern.match(f)])
        if matched_gczs:
            process_set(os.path.join(in_dir, b), [g[1] for g in matched_gczs], out_dir)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} [indir] [outdir]")
    else:
        main(sys.argv[1], sys.argv[2])