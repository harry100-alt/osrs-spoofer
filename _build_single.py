"""Assemble osrs_spoof.py from source files. Run: python _build_single.py"""
import base64, os

def read_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def read_b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')

EXT = 'magisk-setup/extracted'

# Collect all assets
assets = {
    # Shell scripts (repr-encoded for safe embedding)
    'SPOOF_SH': repr(read_text('spoof.sh')),
    'TEST_SH': repr(read_text('test.sh')),
    'REGISTER_SH': repr(read_text('register.sh')),
    'GET_GSFID_SH': repr(read_text('get_gsfid.sh')),
    'GL_SPOOF_CONF': repr(read_text('gl-hook/gl_spoof.conf')),
    'INSTALL_MAGISK_SH': repr(read_text('magisk-setup/install_magisk.sh')),
    # Sensor/GL binaries (base64)
    'SENSORS64_B64': f'"{read_b64("sensors64_patched.so")}"',
    'SENSORS32_B64': f'"{read_b64("sensors32_patched.so")}"',
    'GL_SPOOF64_B64': f'"{read_b64("gl-hook/gl_spoof.so")}"',
    'GL_SPOOF32_B64': f'"{read_b64("gl-hook/gl_spoof32.so")}"',
    # Magisk binaries (base64)
    'MAGISK64_B64': f'"{read_b64(f"{EXT}/lib/x86_64/libmagisk64.so")}"',
    'MAGISK32_B64': f'"{read_b64(f"{EXT}/lib/x86/libmagisk32.so")}"',
    'BUSYBOX_B64': f'"{read_b64(f"{EXT}/lib/x86_64/libbusybox.so")}"',
    'MAGISKINIT_B64': f'"{read_b64(f"{EXT}/lib/x86/libmagiskinit.so")}"',  # x86_64 is 0 bytes
    'MAGISKPOLICY_B64': f'"{read_b64(f"{EXT}/lib/x86/libmagiskpolicy.so")}"',
    'STUB_APK_B64': f'"{read_b64(f"{EXT}/assets/stub.apk")}"',
    'MAIN_JAR_B64': f'"{read_b64(f"{EXT}/assets/main.jar")}"',
    'UTIL_FUNCTIONS_B64': f'"{read_b64(f"{EXT}/assets/util_functions.sh")}"',
}

# Read the code template
tail = read_text('_tail.py')

# Build header
header = '#!/usr/bin/env python3\n'
header += '"""BlueStacks OSRS Anti-Detection Spoofer - Single File Edition.\n'
header += 'Auto-detects environment, installs Magisk if missing, spoofs device, validates.\n'
header += 'Usage: python osrs_spoof.py [--test] [--instance N] [--register] [--cleanup]\n'
header += 'Requirements: Python 3.7+, BlueStacks 5 with ADB + root enabled.\n'
header += '"""\n\n'
header += 'import subprocess, sys, os, re, time, argparse, base64, tempfile, shutil, threading\n\n'

for name, value in assets.items():
    header += f'{name} = {value}\n\n'

# Write final file
with open('osrs_spoof.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(header)
    f.write(tail)

size = os.path.getsize('osrs_spoof.py')
print(f"Created osrs_spoof.py: {size:,} bytes ({size/1024:.1f} KB / {size/1024/1024:.1f} MB)")
