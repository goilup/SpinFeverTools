#!/usr/bin/env python3
"""Batch or Single-file decode YMZ280B 4-bit ADPCM audio to PCM WAV.
"""

import argparse
import math
import struct
import wave
import os
import glob

# YMZ280B constants
INDEX_SCALE = [0x0E6, 0x0E6, 0x0E6, 0x0E6, 0x133, 0x199, 0x200, 0x266]
DIFF_LOOKUP = [1, 3, 5, 7, 9, 11, 13, 15, -1, -3, -5, -7, -9, -11, -13, -15]
STEP_MIN = 0x7F
STEP_MAX = 0x6000

def decode_ymz280b(data):
    samples = []
    signal = 0
    step = STEP_MIN
    for byte in data:
        for nib in ((byte >> 4) & 0xF, byte & 0xF):
            signal += int(step * DIFF_LOOKUP[nib] / 8)
            if signal > 32767: signal = 32767
            elif signal < -32768: signal = -32768
            step = (step * INDEX_SCALE[nib & 7]) >> 8
            if step < STEP_MIN: step = STEP_MIN
            elif step > STEP_MAX: step = STEP_MAX
            samples.append(signal)
    return samples

def dc_block(samples, rate, cutoff_hz=20.0):
    alpha = 1.0 - (2.0 * math.pi * cutoff_hz / rate)
    out = [0.0] * len(samples)
    prev_x = 0.0
    prev_y = 0.0
    for i, x in enumerate(samples):
        y = x - prev_x + alpha * prev_y
        prev_x = x
        prev_y = y
        out[i] = max(-32768, min(32767, int(y)))
    return out

def process_file(input_path, rate, apply_filter):
    """Handles the decoding and saving for a single file."""
    output_path = os.path.splitext(input_path)[0] + ".wav"
    try:
        with open(input_path, "rb") as f:
            data = f.read()
        samples = decode_ymz280b(data)
        if apply_filter:
            samples = dc_block(samples, rate)
        with wave.open(output_path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        print(f"  Converted: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    except Exception as e:
        print(f"  Error processing {input_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Decode YMZ280B BIN file(s) to WAV")
    parser.add_argument("path", nargs="?", default=".", 
                        help="Path to a .bin file OR a directory (default: current directory)")
    parser.add_argument("--rate", type=int, default=16000, help="Sample rate (default: 16000)")
    parser.add_argument("--no-dc-filter", action="store_true", help="Skip DC filter")
    args = parser.parse_args()

    target_path = args.path
    files_to_process = []

    if os.path.isfile(target_path):
        # User pointed to a specific file
        files_to_process.append(target_path)
    elif os.path.isdir(target_path):
        # User pointed to a directory, scan for .bin files
        raw_list = glob.glob(os.path.join(target_path, "*.bin")) + \
                   glob.glob(os.path.join(target_path, "*.BIN"))
        # De-duplicate for Windows case-insensitivity
        files_to_process = sorted(list(set(os.path.normpath(f) for f in raw_list)))
    else:
        print(f"Error: Path '{target_path}' not found.")
        return

    if not files_to_process:
        print(f"No .bin files found at: {target_path}")
        return

    print(f"Processing {len(files_to_process)} file(s)...")
    for file_path in files_to_process:
        process_file(file_path, args.rate, not args.no_dc_filter)
    print("Done.")

if __name__ == "__main__":
    main()