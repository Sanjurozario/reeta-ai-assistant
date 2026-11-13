import os
import sys
import struct
import subprocess

def align4(b):
    pad = (4 - (len(b) % 4)) % 4
    return b + (b'\x00' * pad)

def pack_str_u16(s):
    return s.encode('utf-16le') + b'\x00\x00'

def make_res_entry(type_id, name_id, data, lang_id=0x0409):
    type_bytes = struct.pack('<HH', 0xFFFF, type_id)
    name_bytes = struct.pack('<HH', 0xFFFF, name_id)
    header_size = 4 + 4 + len(type_bytes) + len(name_bytes)
    pad = (4 - (header_size % 4)) % 4
    header_size += pad + 16
    hdr = struct.pack('<II', len(data), header_size)
    hdr += type_bytes + name_bytes + (b'\x00' * pad)
    hdr += struct.pack('<IHHI', 0, 0x1030, lang_id, 0)
    hdr += struct.pack('<I', 0)
    return hdr + align4(data)

def build_version_info(company='REETA Systems', desc='REETA', ver='1.0.0.0', prod='REETA', copy='Copyright © 2026 REETA'):
    fixed = struct.pack('<IIIIIIIIIIIII',
        0xFEEF04BD, 0x00010000, 0x00010000, 0x00000000,
        0x00010000, 0x00000000, 0x0000003F, 0x00000000,
        0x00040004, 0x00000001, 0x00000000, 0x00000000, 0x00000000
    )

    def build_string(key, val):
        val_u16 = pack_str_u16(val)
        key_u16 = pack_str_u16(key)
        val_len_wchars = len(val) + 1
        str_hdr = struct.pack('<HHH', 0, val_len_wchars, 1) + key_u16
        str_hdr = align4(str_hdr)
        res = str_hdr + val_u16
        res = align4(res)
        return struct.pack('<H', len(res)) + res[2:]

    strings = [
        build_string('CompanyName', company),
        build_string('FileDescription', desc),
        build_string('FileVersion', ver),
        build_string('LegalCopyright', copy),
        build_string('ProductName', prod),
        build_string('ProductVersion', ver),
    ]
    str_table_data = b''.join(strings)
    str_table_hdr = struct.pack('<HHH', 0, 0, 1) + pack_str_u16('000004b0')
    str_table_hdr = align4(str_table_hdr)
    str_table = align4(struct.pack('<H', len(str_table_hdr) + len(str_table_data)) + str_table_hdr[2:] + str_table_data)

    sfi_hdr = struct.pack('<HHH', 0, 0, 1) + pack_str_u16('StringFileInfo')
    sfi_hdr = align4(sfi_hdr)
    sfi = align4(struct.pack('<H', len(sfi_hdr) + len(str_table)) + sfi_hdr[2:] + str_table)

    var_data = struct.pack('<HH', 0x0000, 0x04b0)
    var_hdr = struct.pack('<HHH', 0, len(var_data), 0) + pack_str_u16('Translation')
    var_hdr = align4(var_hdr)
    var = align4(struct.pack('<H', len(var_hdr) + len(var_data)) + var_hdr[2:] + var_data)

    vfi_hdr = struct.pack('<HHH', 0, 0, 1) + pack_str_u16('VarFileInfo')
    vfi_hdr = align4(vfi_hdr)
    vfi = align4(struct.pack('<H', len(vfi_hdr) + len(var)) + vfi_hdr[2:] + var)

    root_key = pack_str_u16('VS_VERSION_INFO')
    root_hdr = struct.pack('<HHH', 0, len(fixed), 0) + root_key
    root_hdr = align4(root_hdr)
    full_body = root_hdr[2:] + fixed + align4(sfi) + align4(vfi)
    return struct.pack('<H', len(full_body) + 2) + full_body

def compile_rc(rc_path, out_res_path, ico_path=None):
    # 1. Null header (32 bytes)
    res_data = b'\x00\x00\x00\x00\x20\x00\x00\x00\xff\xff\x00\x00\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

    # 2. Manifest (RT_MANIFEST = 24, Name = 1)
    manifest_xml = (
        b'<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">'
        b'<dependency><dependentAssembly>'
        b'<assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>'
        b'</dependentAssembly></dependency></assembly>'
    )
    res_data += make_res_entry(24, 1, manifest_xml)

    # 3. Version Info (RT_VERSION = 16, Name = 1)
    vi_data = build_version_info()
    res_data += make_res_entry(16, 1, vi_data)

    # 4. Icon (RT_GROUP_ICON = 14, RT_ICON = 3)
    if not ico_path or not os.path.exists(ico_path):
        candidates = [
            os.path.join(os.path.dirname(__file__), '../desktop/src-tauri/icons/icon.ico'),
            'desktop/src-tauri/icons/icon.ico',
            'icons/icon.ico',
        ]
        for c in candidates:
            if os.path.exists(c):
                ico_path = c
                break

    if ico_path and os.path.exists(ico_path):
        with open(ico_path, 'rb') as f:
            ico_bytes = f.read()
        reserved, ico_type, count = struct.unpack('<HHH', ico_bytes[:6])
        grp_dir = struct.pack('<HHH', reserved, ico_type, count)
        for i in range(count):
            entry_offset = 6 + i * 16
            w, h, colors, resv, planes, bpp, bytes_in_res, img_offset = struct.unpack('<BBBBHHII', ico_bytes[entry_offset:entry_offset+16])
            grp_dir += struct.pack('<BBBBHHIH', w, h, colors, resv, planes, bpp, bytes_in_res, i + 1)
            img_data = ico_bytes[img_offset:img_offset+bytes_in_res]
            res_data += make_res_entry(3, i + 1, img_data)
        res_data += make_res_entry(14, 32512, grp_dir)

    os.makedirs(os.path.dirname(os.path.abspath(out_res_path)), exist_ok=True)
    with open(out_res_path, 'wb') as f:
        f.write(res_data)

if __name__ == '__main__':
    out_file = None
    rc_file = None
    for i, arg in enumerate(sys.argv):
        if arg.lower() == '/fo' and i + 1 < len(sys.argv):
            out_file = sys.argv[i+1]
        elif arg.lower().startswith('/fo'):
            out_file = arg[3:]
        elif arg.endswith('.rc'):
            rc_file = arg

    if out_file:
        compile_rc(rc_file, out_file)
        sys.exit(0)
    else:
        print("Usage: rc_compiler.py /fo <output.res> <input.rc>")
        sys.exit(1)

