simpletga.py - Python script that converts all GCZ files in a directory into TGA sprite sheets

simplegcz.py - Python script that converts all TGA sprite sheets in a directory into GCZ files (uncompressed, SpinFever does not care)

extract_sprites.py - Python script that extracts the sprites from the GCZ files into easily editable files (when editing TGA files do not exceed the transparency boundary or it will corrupt)

sprites_to_sheet.py - Python script that takes all your sprites in a directory and places them on a TGA sheet that should match the original. (You must specify the original AEP directory for it to match the location on the sprite sheet)

waw_decrypt.py - Python script that converts .WAW to .WAV (requires xor_table.txt)

waw_encrypt.py - Python script that converts .WAV to .WAW (requires xor_table.txt)

cougarwav.py - Python script that converts COUGAR SD1/SD2/SD3.bin into wav, use --rate 16000 or --rate 22050 depending on the file. You can find these in "update"