"""
BlueStacks OSRS Anti-Detection Deployer
========================================
One-command deployment to any BlueStacks instance on any Windows machine.

Usage:
    python deploy.py                     # Deploy instance 0
    python deploy.py --instance 3        # Deploy instance 3 (unique identity)
    python deploy.py --test              # Test only (don't redeploy)
    python deploy.py --register          # Extract GSF ID for Play Protect registration
    python deploy.py --instance 3 --test # Test instance 3

Requirements:
    - BlueStacks 5.x running with ADB enabled
    - Python 3.7+
    - No other dependencies
"""

import subprocess
import sys
import os
import re
import time
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ADB discovery ---

def find_adb():
    """Find HD-Adb.exe or adb.exe on this machine."""
    paths = [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "BlueStacks_nxt", "HD-Adb.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "BlueStacks_nxt", "HD-Adb.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
    ]
    for p in paths:
        if os.path.isfile(p):
            return p
    # Try PATH
    for name in ["adb.exe", "adb"]:
        try:
            r = subprocess.run([name, "version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return None


def adb(exe, *args, serial=None, timeout=30):
    """Run an ADB command, return (stdout+stderr, returncode).
    If serial is provided, uses -s <serial> to target a specific device."""
    cmd = [exe]
    if serial:
        cmd += ["-s", serial]
    cmd += list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr, r.returncode
    except FileNotFoundError:
        return f"ADB executable not found: {exe}", 1
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1


def adb_push(exe, local, remote, serial=None):
    """Push a file. Returns True on success."""
    out, rc = adb(exe, "push", local, remote, serial=serial)
    if rc != 0:
        print(f"  [ERR] push {os.path.basename(local)}: {out.strip()}")
        return False
    print(f"  [OK]  {os.path.basename(local)} -> {remote}")
    return True


def adb_root_shell(exe, script_path, serial=None):
    """Execute a script on-device as root via the renamed su binary.
    Falls back to 'su' if .s binary itself is not invocable."""
    out, rc = adb(exe, "shell",
                  f"echo '/system/bin/sh {script_path}' | /system/xbin/.s",
                  serial=serial, timeout=60)
    if rc != 0:
        # Only fallback when .s binary can't be invoked (not when script returns error).
        # Check if output is ONLY a shell error about the binary (no script output present).
        out_lower = out.lower()
        shell_errors = ("inaccessible", "not found", "no such file",
                        "permission denied", "cannot execute", "not permitted")
        is_binary_error = any(e in out_lower for e in shell_errors)
        has_script_output = "[SPOOF]" in out or "[PASS]" in out or "[CRIT]" in out or "===" in out
        if is_binary_error and not has_script_output:
            out, rc = adb(exe, "shell",
                          f"echo '/system/bin/sh {script_path}' | su",
                          serial=serial, timeout=60)
    return out, rc


def to_lf(src):
    """Convert a file to LF line endings. Returns path to unique temp file.
    Uses PID suffix to avoid collisions when multiple deploy.py instances run."""
    with open(src, "rb") as f:
        data = f.read()
    data = data.replace(b"\r\n", b"\n")
    dst = f"{src}.{os.getpid()}.lf"
    with open(dst, "wb") as f:
        f.write(data)
    return dst


def parse_test_results(out, rc):
    """Parse test.sh output and return appropriate exit code.
    test.sh exits non-zero when detection failures exist — that's functional
    signal, not a script crash. We parse output to distinguish:
      0 = ALL CLEAR
      1 = detection failures found
      2 = critical failures found
      3 = test script failed to execute (no parseable output)
    """
    # Check if output contains the summary line (proves test.sh actually ran)
    crit_match = re.search(r'CRIT:\s*(\d+)', out)
    has_summary = bool(crit_match) or "ALL CLEAR" in out or "FAILURES DETECTED" in out

    if not has_summary:
        # No parseable test output — script didn't run or crashed
        if rc != 0:
            print("[ERR] Test script failed to execute (no test output).")
        else:
            print("[!] Test produced no parseable results.")
        return 3

    # Script ran — check results
    if crit_match:
        crit_count = int(crit_match.group(1))
        if crit_count > 0:
            print(f"\n[!!!] {crit_count} CRITICAL detection failure(s) — review output above")
            return 2

    if "ALL CLEAR" in out:
        return 0

    # Has summary but not ALL CLEAR — detection failures
    print("[!] Detection failures found — review output above")
    return 1


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Deploy OSRS anti-detection to BlueStacks")
    parser.add_argument("-i", "--instance", type=int, default=0, choices=range(256),
                        metavar="N",
                        help="Instance ID 0-255 for unique device identity (default: 0)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-t", "--test", action="store_true",
                      help="Only run detection test, skip deployment")
    mode.add_argument("-r", "--register", action="store_true",
                      help="Extract GSF ID for Play Protect registration")
    mode.add_argument("--cleanup", action="store_true",
                      help="Post-registration cleanup (clear GMS/Play Store data)")
    parser.add_argument("--adb", type=str, default=None,
                        help="Path to ADB executable (auto-detected if omitted)")
    parser.add_argument("-d", "--device", type=str, default=None,
                        help="ADB device serial (e.g. emulator-5554). Required when multiple devices connected.")
    args = parser.parse_args()

    print("=" * 50)
    print("  BlueStacks OSRS Anti-Detection Deployer")
    print("=" * 50)
    print()

    # 1. Find ADB
    exe = args.adb or find_adb()
    if not exe:
        print("[ERR] Cannot find ADB. Install Android SDK or specify --adb path.")
        print("      BlueStacks ADB is usually at:")
        print(r"      C:\Program Files\BlueStacks_nxt\HD-Adb.exe")
        sys.exit(1)
    print(f"[ADB] {exe}")

    # 2. Check device — select target serial
    out, rc = adb(exe, "devices")
    lines = [l for l in out.strip().split("\n") if "\tdevice" in l]
    if not lines:
        print("[ERR] No device connected. Is BlueStacks running with ADB enabled?")
        sys.exit(1)

    if args.device:
        # User specified a device serial — verify it's connected
        serials = [l.split("\t")[0] for l in lines]
        if args.device not in serials:
            print(f"[ERR] Device '{args.device}' not found. Connected: {', '.join(serials)}")
            sys.exit(1)
        serial = args.device
    elif len(lines) > 1:
        serials = [l.split("\t")[0] for l in lines]
        print(f"[ERR] Multiple devices connected: {', '.join(serials)}")
        print("      Use --device <serial> to select one.")
        sys.exit(1)
    else:
        serial = lines[0].split("\t")[0]

    print(f"[DEV] {serial}")
    print()

    # 3. Register mode — extract GSF ID for Play Protect registration
    if args.register:
        print("--- Play Protect Registration (extract GSF ID) ---")
        print()
        lf = to_lf(os.path.join(SCRIPT_DIR, "get_gsfid.sh"))
        if not adb_push(exe, lf, "/data/local/tmp/get_gsfid.sh", serial=serial):
            os.remove(lf)
            print("[ERR] Failed to push get_gsfid.sh. Aborting.")
            sys.exit(1)
        os.remove(lf)
        print()
        out, rc = adb_root_shell(exe, "/data/local/tmp/get_gsfid.sh", serial=serial)
        print(out)
        if rc != 0:
            print("[ERR] GSF ID extraction failed.")
            sys.exit(1)
        print()
        print("After registering at google.com/android/uncertified,")
        followup = "python deploy.py --cleanup"
        if args.device:
            followup += f" --device {args.device}"
        if args.adb:
            followup += f" --adb \"{args.adb}\""
        print(f"run: {followup}")
        return

    # 3b. Post-registration cleanup
    if args.cleanup:
        print("--- Post-Registration Cleanup ---")
        print()
        lf = to_lf(os.path.join(SCRIPT_DIR, "register.sh"))
        if not adb_push(exe, lf, "/data/local/tmp/register.sh", serial=serial):
            os.remove(lf)
            print("[ERR] Failed to push register.sh. Aborting.")
            sys.exit(1)
        os.remove(lf)
        print()
        out, rc = adb_root_shell(exe, "/data/local/tmp/register.sh", serial=serial)
        print(out)
        if rc != 0:
            print("[ERR] Cleanup script failed.")
            sys.exit(1)
        return

    # 3c. Test-only mode
    if args.test:
        print("--- Test Only Mode ---")
        lf = to_lf(os.path.join(SCRIPT_DIR, "test.sh"))
        if not adb_push(exe, lf, "/data/local/tmp/test.sh", serial=serial):
            os.remove(lf)
            print("[ERR] Failed to push test.sh. Aborting.")
            sys.exit(1)
        os.remove(lf)
        print()
        out, rc = adb_root_shell(exe, "/data/local/tmp/test.sh", serial=serial)
        print(out)
        # Parse test results from output (test.sh exits non-zero on failures)
        exit_code = parse_test_results(out, rc)
        sys.exit(exit_code)

    # 4. Full deployment
    print(f"--- Deploying (instance {args.instance}) ---")
    print()

    # Convert scripts to LF
    spoof_lf = to_lf(os.path.join(SCRIPT_DIR, "spoof.sh"))
    test_lf = to_lf(os.path.join(SCRIPT_DIR, "test.sh"))
    cleanup = [spoof_lf, test_lf]

    # Push everything
    print("[PUSH] Uploading files...")
    files = [
        (spoof_lf, "/data/local/tmp/spoof.sh"),
        (test_lf, "/data/local/tmp/test.sh"),
    ]
    s64 = os.path.join(SCRIPT_DIR, "sensors64_patched.so")
    s32 = os.path.join(SCRIPT_DIR, "sensors32_patched.so")
    if os.path.isfile(s64):
        files.append((s64, "/data/local/tmp/sensors64_patched.so"))
    if os.path.isfile(s32):
        files.append((s32, "/data/local/tmp/sensors32_patched.so"))

    # GL hook libraries (64-bit and 32-bit) and config
    gl_hook64 = os.path.join(SCRIPT_DIR, "gl-hook", "gl_spoof.so")
    gl_hook32 = os.path.join(SCRIPT_DIR, "gl-hook", "gl_spoof32.so")
    gl_conf = os.path.join(SCRIPT_DIR, "gl-hook", "gl_spoof.conf")
    if os.path.isfile(gl_hook64):
        files.append((gl_hook64, "/data/local/tmp/gl_spoof.so"))
        print("  [GL]  GL string hook (64-bit) found, will deploy")
    else:
        print("  [GL]  No gl_spoof.so found, skipping GL hook (build with gl-hook/build.sh)")
    if os.path.isfile(gl_hook32):
        files.append((gl_hook32, "/data/local/tmp/gl_spoof32.so"))
        print("  [GL]  GL string hook (32-bit) found, will deploy")
    if os.path.isfile(gl_conf):
        files.append((gl_conf, "/data/local/tmp/gl_spoof.conf"))

    try:
        for local, remote in files:
            if not adb_push(exe, local, remote, serial=serial):
                print("[ERR] Failed to push files. Aborting.")
                sys.exit(1)
    finally:
        # Always cleanup temp LF files, even on push failure
        for f in cleanup:
            try:
                os.remove(f)
            except OSError:
                pass

    # Run spoofer
    print()
    print("[RUN] Applying spoofer...")
    out, rc = adb_root_shell(exe, f"/data/local/tmp/spoof.sh {args.instance}", serial=serial)
    print(out)
    if rc != 0:
        # Spoofer exits non-zero when property spoofs fail.
        # Check if it completed (has summary line) vs crashed/transport error.
        if "SPOOF v7 COMPLETE" in out:
            print("[WARN] Spoofer completed with property failures (see above).")
        else:
            print("[ERR] Spoofer execution failed (root shell error).")
            sys.exit(1)

    # Brief pause for mounts to settle
    time.sleep(1)

    # Run test
    print("[TEST] Validating...")
    out, rc = adb_root_shell(exe, "/data/local/tmp/test.sh", serial=serial)
    print(out)
    exit_code = parse_test_results(out, rc)
    if exit_code == 0:
        print("[OK] Deployment successful - device is clean")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
