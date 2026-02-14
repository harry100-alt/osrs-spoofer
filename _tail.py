
# =============================================================================
#  ASSET EXTRACTION
# =============================================================================

def extract_assets():
    """Extract all embedded assets to a temp directory. Returns (tmpdir, paths_dict)."""
    tmpdir = tempfile.mkdtemp(prefix="osrs_spoof_")
    paths = {}

    for name, content in [
        ("spoof.sh", SPOOF_SH),
        ("test.sh", TEST_SH),
        ("register.sh", REGISTER_SH),
        ("get_gsfid.sh", GET_GSFID_SH),
        ("gl_spoof.conf", GL_SPOOF_CONF),
        ("install_magisk.sh", INSTALL_MAGISK_SH),
    ]:
        p = os.path.join(tmpdir, name)
        with open(p, "wb") as f:
            f.write(content.replace("\r\n", "\n").encode("utf-8"))
        paths[name] = p

    for name, b64data in [
        ("sensors64_patched.so", SENSORS64_B64),
        ("sensors32_patched.so", SENSORS32_B64),
        ("gl_spoof.so", GL_SPOOF64_B64),
        ("gl_spoof32.so", GL_SPOOF32_B64),
        # Magisk binaries
        ("magisk64", MAGISK64_B64),
        ("magisk32", MAGISK32_B64),
        ("busybox", BUSYBOX_B64),
        ("magiskinit", MAGISKINIT_B64),
        ("magiskpolicy", MAGISKPOLICY_B64),
        ("stub.apk", STUB_APK_B64),
        ("main.jar", MAIN_JAR_B64),
        ("util_functions.sh", UTIL_FUNCTIONS_B64),
    ]:
        p = os.path.join(tmpdir, name)
        with open(p, "wb") as f:
            f.write(base64.b64decode(b64data))
        paths[name] = p

    return tmpdir, paths


# =============================================================================
#  ADB HELPERS
# =============================================================================

def find_adb():
    """Find HD-Adb.exe or adb.exe on this machine."""
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "BlueStacks_nxt", "HD-Adb.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "BlueStacks_nxt", "HD-Adb.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Android", "Sdk", "platform-tools", "adb.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""),
                     "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    for name in ["adb.exe", "adb"]:
        try:
            r = subprocess.run([name, "version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return None


def adb(exe, *args, serial=None, timeout=30):
    """Run an ADB command, return (stdout+stderr, returncode)."""
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


def _has_script_output(out):
    """Check if output contains recognizable script output markers."""
    return ("[SPOOF]" in out or "[PASS]" in out or "[CRIT]" in out
            or "===" in out or "INSTALL_" in out or "ALREADY_" in out
            or "REMOUNT_" in out)


def _is_su_error(out):
    """Check if output indicates su/shell binary failure (not script failure)."""
    out_lower = out.lower()
    shell_errors = ("inaccessible", "not found", "no such file",
                    "permission denied", "cannot execute", "not permitted")
    return any(e in out_lower for e in shell_errors) and not _has_script_output(out)


def _has_init_service(exe, serial):
    """Check if the osrs_spoof init service exists on this device.
    On fresh boots, init.svc.osrs_spoof may be empty until first trigger.
    Fall back to checking if the .rc file exists."""
    out, _ = adb(exe, "shell", "getprop init.svc.osrs_spoof", serial=serial, timeout=5)
    if out.strip():
        return True
    # Property not set yet — check if the .rc file exists
    out, _ = adb(exe, "shell",
                 "ls /system/etc/init/osrs_spoof.rc 2>/dev/null && echo RC_EXISTS",
                 serial=serial, timeout=5)
    return "RC_EXISTS" in out


def _init_service_exec(exe, commands, serial=None, timeout=120):
    """Execute commands as root via the osrs_spoof init service.

    The service is defined as 'disabled' (no oneshot) in /system/etc/init/osrs_spoof.rc.
    Flow: stop service -> write script -> clear markers -> start service -> poll for done.

    Since the service is non-oneshot, init will restart it when it exits. We work around
    this by: stopping the service before each use (which kills any restart loop), writing
    the new script, then starting it fresh.

    Returns (output_text, return_code) — same interface as adb_root_shell.
    """
    log_file = "/data/local/tmp/.init_output"
    marker = "/data/local/tmp/.init_done"

    # Step 1: Stop the service if it's running/restarting from a previous invocation
    adb(exe, "shell", "setprop ctl.stop osrs_spoof", serial=serial, timeout=5)
    time.sleep(0.3)

    # Step 2: Build the boot script
    # Note: chmod 666 on output files so shell user can read them
    script_lines = (
        f"#!/system/bin/sh\n"
        f"rm -f {marker}\n"
        f"(\n"
        f"{commands}\n"
        f") > {log_file} 2>&1\n"
        f"_rc=$?\n"
        f"echo $_rc > {marker}\n"
        f"chmod 666 {log_file} {marker}\n"
        f"# Sleep to avoid instant restart loop (killed by ctl.stop)\n"
        f"sleep 86400\n"
    )

    # Step 3: Clean up old marker/output files
    adb(exe, "shell", f"rm -f {marker} {log_file}", serial=serial, timeout=5)

    # Step 4: Write script to device via base64 (avoids shell escaping issues)
    import base64 as b64mod
    encoded = b64mod.b64encode(script_lines.encode()).decode()
    chunk_size = 4000
    chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]

    adb(exe, "shell",
        f"echo '{chunks[0]}' > /data/local/tmp/.init_script_b64",
        serial=serial, timeout=5)
    for chunk in chunks[1:]:
        adb(exe, "shell",
            f"echo '{chunk}' >> /data/local/tmp/.init_script_b64",
            serial=serial, timeout=5)

    adb(exe, "shell",
        "base64 -d /data/local/tmp/.init_script_b64 > /data/local/tmp/spoof_boot.sh; "
        "chmod 755 /data/local/tmp/spoof_boot.sh; "
        "rm /data/local/tmp/.init_script_b64",
        serial=serial, timeout=10)

    # Step 5: Start the service
    adb(exe, "shell", "setprop ctl.start osrs_spoof", serial=serial, timeout=5)

    # Step 6: Poll for completion marker
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        out, _ = adb(exe, "shell", f"cat {marker} 2>/dev/null", serial=serial, timeout=5)
        if out.strip():
            # Marker exists — commands completed
            rc = int(out.strip()) if out.strip().isdigit() else 1

            # Read the output log
            log_out, _ = adb(exe, "shell", f"cat {log_file} 2>/dev/null",
                             serial=serial, timeout=10)

            # Stop the service (it's sleeping in sleep 86400) and cleanup
            adb(exe, "shell", "setprop ctl.stop osrs_spoof", serial=serial, timeout=5)
            adb(exe, "shell", f"rm -f {marker} {log_file}",
                serial=serial, timeout=5)

            return log_out, rc

    # Timeout — try to read whatever output exists
    adb(exe, "shell", "setprop ctl.stop osrs_spoof", serial=serial, timeout=5)
    log_out, _ = adb(exe, "shell", f"cat {log_file} 2>/dev/null",
                     serial=serial, timeout=5)
    adb(exe, "shell", f"rm -f {marker} {log_file}", serial=serial, timeout=5)
    return log_out or "TIMEOUT: init service did not complete", 1


def adb_root_shell(exe, script_path, serial=None):
    """Execute a script on-device as root. Tries multiple methods:
    1. Magisk's renamed su (.s) via pipe
    2. Bare su via pipe
    3. su -c with file-based output (for BlueStacks developer mode)
    4. Init service trigger (for clone instances without working su)"""
    # Method 1: Magisk's renamed su (.s) via pipe
    out, rc = adb(exe, "shell",
                  f"echo '/system/bin/sh {script_path}' | /system/xbin/.s",
                  serial=serial, timeout=120)
    if rc == 0 or _has_script_output(out):
        return out, rc

    if _is_su_error(out):
        # Method 2: bare su via pipe (before Magisk renames it)
        out, rc = adb(exe, "shell",
                      f"echo '/system/bin/sh {script_path}' | su",
                      serial=serial, timeout=120)
        if rc == 0 or _has_script_output(out):
            return out, rc

    if _is_su_error(out) or (rc != 0 and not _has_script_output(out)):
        # Method 3: su -c (BlueStacks developer mode — output via file)
        out_file = "/data/local/tmp/.su_output"
        out2, rc2 = adb(exe, "shell",
                        f"su -c '/system/bin/sh {script_path} > {out_file} 2>&1'; "
                        f"cat {out_file} 2>/dev/null; rm {out_file} 2>/dev/null",
                        serial=serial, timeout=120)
        if _has_script_output(out2):
            return out2, rc2
        # If method 3 also produced nothing, try init service
        if out2.strip() and not _is_su_error(out2):
            return out2, rc2

    # Method 4: Init service (for clone instances)
    if _has_init_service(exe, serial):
        commands = f"/system/bin/sh {script_path}"
        out4, rc4 = _init_service_exec(exe, commands, serial=serial, timeout=120)
        if _has_script_output(out4) or (rc4 == 0 and out4.strip()):
            return out4, rc4
        # Return init service output even on failure — it's our last resort
        if out4.strip():
            return out4, rc4

    return out, rc


def parse_test_results(out, rc):
    """Parse test.sh output. 0=clean, 1=failures, 2=critical, 3=crash."""
    crit_match = re.search(r'CRIT:\s*(\d+)', out)
    has_summary = bool(crit_match) or "ALL CLEAR" in out or "FAILURES DETECTED" in out

    if not has_summary:
        if rc != 0:
            print("[ERR] Test script failed to execute (no test output).")
        else:
            print("[!] Test produced no parseable results.")
        return 3

    if crit_match:
        crit_count = int(crit_match.group(1))
        if crit_count > 0:
            print(f"\n[!!!] {crit_count} CRITICAL detection failure(s) -- review output above")
            return 2

    if "ALL CLEAR" in out:
        return 0

    print("[!] Detection failures found -- review output above")
    return 1


# =============================================================================
#  PRE-FLIGHT CHECKS
# =============================================================================

def check_root(exe, serial):
    """Check if we have root access on the device."""
    # Try .s (renamed su — Magisk's su) via pipe
    out, rc = adb(exe, "shell", "echo 'echo ROOT_OK' | /system/xbin/.s",
                  serial=serial, timeout=10)
    if rc == 0 and "ROOT_OK" in out:
        return True
    # Try bare su via pipe (before Magisk renames it)
    out, rc = adb(exe, "shell", "echo 'echo ROOT_OK' | su",
                  serial=serial, timeout=10)
    if rc == 0 and "ROOT_OK" in out:
        return True
    # BlueStacks su with developer mode: output goes to file instead of pipe
    marker = "/data/local/tmp/.root_check"
    out, rc = adb(exe, "shell",
                  f"su -c 'echo ROOT_OK > {marker}' 2>/dev/null; "
                  f"cat {marker} 2>/dev/null; rm {marker} 2>/dev/null",
                  serial=serial, timeout=10)
    if "ROOT_OK" in out:
        return True
    # Init service method (clone instances — no working su, but init runs as root)
    if _has_init_service(exe, serial):
        out, rc = _init_service_exec(exe, "echo ROOT_OK", serial=serial, timeout=15)
        if "ROOT_OK" in out:
            return True
    return False


def check_magisk(exe, serial):
    """Check if resetprop is installed and working."""
    # resetprop --version exits non-zero (prints help), so just check output
    out, _ = adb(exe, "shell",
                 "echo '/system/xbin/resetprop --version' | /system/xbin/.s",
                 serial=serial, timeout=10)
    if "resetprop" in out.lower():
        return True
    # Try via bare su (before su rename)
    out, _ = adb(exe, "shell",
                 "echo '/system/xbin/resetprop --version' | su",
                 serial=serial, timeout=10)
    if "resetprop" in out.lower():
        return True
    # Try via init service (clone instances)
    if _has_init_service(exe, serial):
        out, _ = _init_service_exec(exe, "/system/xbin/resetprop --version",
                                    serial=serial, timeout=15)
        if "resetprop" in out.lower():
            return True
    return False


def install_magisk(exe, serial, paths, log_fn=print):
    """Push Magisk binaries and run install_magisk.sh.
    Supports both su-based and init-service-based installation."""
    log_fn("")
    log_fn("[SETUP] KitsuneMask/Magisk not found — installing automatically...")
    log_fn("")

    magisk_files = [
        ("magisk64", "/data/local/tmp/magisk64"),
        ("magisk32", "/data/local/tmp/magisk32"),
        ("busybox", "/data/local/tmp/busybox"),
        ("magiskinit", "/data/local/tmp/magiskinit"),
        ("magiskpolicy", "/data/local/tmp/magiskpolicy"),
        ("util_functions.sh", "/data/local/tmp/util_functions.sh"),
        ("main.jar", "/data/local/tmp/main.jar"),
        ("stub.apk", "/data/local/tmp/stub.apk"),
        ("install_magisk.sh", "/data/local/tmp/install_magisk.sh"),
    ]

    for name, remote in magisk_files:
        if not adb_push(exe, paths[name], remote, serial=serial):
            log_fn(f"[ERR] Failed to push {name}. Aborting Magisk install.")
            return False

    log_fn("")
    log_fn("[SETUP] Running Magisk installer...")

    # Try su first (works on primary instance), fall back to init service (clones)
    out, rc = adb(exe, "shell",
                  "echo '/system/bin/sh /data/local/tmp/install_magisk.sh' | su",
                  serial=serial, timeout=60)

    if "MAGISK INSTALL SUCCESS" not in out and "MAGISK INSTALL COMPLETED" not in out:
        # su didn't work — try init service (clone instances)
        if _has_init_service(exe, serial):
            log_fn("  (su failed, trying init service...)")
            out, rc = _init_service_exec(
                exe, "/system/bin/sh /data/local/tmp/install_magisk.sh",
                serial=serial, timeout=60)

    log_fn(out)

    if "MAGISK INSTALL SUCCESS" in out:
        log_fn("[OK] KitsuneMask installed successfully!")
        return True
    elif "MAGISK INSTALL COMPLETED" in out:
        log_fn("[WARN] KitsuneMask installed with warnings (see above).")
        return True
    else:
        log_fn("[ERR] KitsuneMask installation failed.")
        return False


# =============================================================================
#  CLI CORE (used by both CLI and GUI)
# =============================================================================

def _get_bluestacks_instances():
    """Read BlueStacks config to find all instance names and their ADB ports.
    Returns list of dicts: {name, display_name, adb_port}."""
    conf_path = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                             "BlueStacks_nxt", "bluestacks.conf")
    instances = {}
    try:
        with open(conf_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Parse: bst.instance.<NAME>.<KEY>="<VALUE>"
                if not line.startswith("bst.instance."):
                    continue
                rest = line[len("bst.instance."):]
                dot = rest.find(".")
                if dot < 0:
                    continue
                inst_name = rest[:dot]
                kv = rest[dot + 1:]
                eq = kv.find("=")
                if eq < 0:
                    continue
                key = kv[:eq]
                val = kv[eq + 1:].strip('"')
                if inst_name not in instances:
                    instances[inst_name] = {"name": inst_name}
                instances[inst_name][key] = val
    except (FileNotFoundError, PermissionError):
        return []

    result = []
    for name, data in instances.items():
        adb_port = data.get("status.adb_port") or data.get("adb_port")
        display_name = data.get("display_name", name)
        root_on = data.get("enable_root_access") == "1"
        if adb_port:
            result.append({
                "name": name,
                "display_name": display_name,
                "adb_port": adb_port,
                "root_enabled": root_on,
            })
    return result


def _ensure_bluestacks_config(log_fn=print):
    """Auto-enable root access, ADB, and rooting feature on all BlueStacks instances.
    Edits bluestacks.conf directly.
    Changes take effect on next instance restart.
    Returns list of instance names that were modified."""
    conf_path = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                             "BlueStacks_nxt", "bluestacks.conf")
    try:
        with open(conf_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (FileNotFoundError, PermissionError) as e:
        log_fn(f"[WARN] Cannot read BlueStacks config: {e}")
        return []

    modified = []
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # Fix enable_root_access="0" -> "1" (per-instance)
        if 'enable_root_access="0"' in stripped and stripped.startswith("bst.instance."):
            inst_name = stripped.split("bst.instance.")[1].split(".")[0]
            new_lines.append(line.replace('enable_root_access="0"', 'enable_root_access="1"'))
            if inst_name not in modified:
                modified.append(inst_name)
        # Fix global ADB access
        elif stripped == 'bst.enable_adb_access="0"':
            new_lines.append(line.replace('"0"', '"1"'))
            modified.append("__global_adb__")
        # Fix bst.feature.rooting (enables su from adb shell via hypercall)
        elif stripped == 'bst.feature.rooting="0"':
            new_lines.append(line.replace('"0"', '"1"'))
            modified.append("__rooting__")
        else:
            new_lines.append(line)

    if modified:
        try:
            with open(conf_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except PermissionError as e:
            log_fn(f"[WARN] Cannot write BlueStacks config: {e}")
            return []

    return [m for m in modified if m not in ("__global_adb__", "__rooting__")]


def detect_devices(exe):
    """Return list of dicts: {serial, display_name} for connected ADB devices.
    Reads BlueStacks config to auto-connect to all running instances."""
    # Read BlueStacks config for known instance ports
    bs_instances = _get_bluestacks_instances()

    # First, get currently visible devices (before connecting)
    out_before, _ = adb(exe, "devices")
    auto_serials = set()
    for line in out_before.strip().split("\n"):
        if "\tdevice" in line:
            auto_serials.add(line.split("\t")[0])

    # Figure out which ports are already covered by auto-discovered emulators
    auto_ports = set()
    for serial in auto_serials:
        if serial.startswith("emulator-"):
            try:
                auto_ports.add(str(int(serial.split("-")[1]) + 1))
            except (ValueError, IndexError):
                pass

    # Connect to any BlueStacks instance ports that aren't already covered
    tried_ports = set()
    for inst in bs_instances:
        port = inst["adb_port"]
        if port not in auto_ports and port not in tried_ports:
            adb(exe, "connect", f"127.0.0.1:{port}", timeout=5)
            tried_ports.add(port)

    # Now list all connected devices
    out, rc = adb(exe, "devices")
    devices = []
    seen_ports = set()  # track ports to avoid duplicates
    for line in out.strip().split("\n"):
        if "\tdevice" in line:
            serial = line.split("\t")[0]

            # Determine port for dedup
            port = None
            if serial.startswith("emulator-"):
                try:
                    port = str(int(serial.split("-")[1]) + 1)
                except (ValueError, IndexError):
                    pass
            elif ":" in serial:
                port = serial.split(":")[-1]

            # Skip duplicates (prefer emulator-XXXX over 127.0.0.1:XXXX)
            if port and port in seen_ports:
                continue
            if port:
                seen_ports.add(port)

            # Try to match serial to a BlueStacks instance for display name
            display_name = None
            for inst in bs_instances:
                inst_port = inst["adb_port"]
                if port and port == inst_port:
                    display_name = inst["display_name"]
                    break

            devices.append({
                "serial": serial,
                "display_name": display_name,
            })

    # Normalize: "BlueStacks App Player" (no number) -> "BlueStacks App Player 1"
    for d in devices:
        name = d.get("display_name") or ""
        if re.match(r"^BlueStacks App Player\s*$", name):
            d["display_name"] = "BlueStacks App Player 1"

    # Sort numerically ascending (App Player 1, App Player 2, ...)
    def _sort_key(d):
        name = d.get("display_name") or ""
        m = re.search(r"(\d+)\s*$", name)
        return int(m.group(1)) if m else 0
    devices.sort(key=_sort_key)

    return devices


def check_spoof_status(exe, serial):
    """Check if a device is actively spoofed RIGHT NOW (not just configured).
    Returns dict: spoofed (bool), model (str or None), instance (str or None).
    Checks two things:
      1. .spoof_instance file exists (our spoof was configured for this device)
      2. /dev/vboxguest is gone (bind mounts are actually active this session)
    Both must be true — the file persists across reboots but mounts don't."""
    result = {"spoofed": False, "model": None, "instance": None}
    try:
        # Single shell command: check marker file AND verify mounts are active
        out, _ = adb(exe, "shell",
                     "cat /data/local/tmp/.spoof_instance 2>/dev/null; "
                     "echo ---; "
                     "ls /dev/vboxguest 2>/dev/null && echo VBOX_EXISTS || echo VBOX_GONE",
                     serial=serial, timeout=5)
        parts = out.strip().split("---")
        inst = parts[0].strip().split("\n")[-1].strip() if len(parts) > 0 else ""
        vbox = parts[1].strip().split("\n")[-1].strip() if len(parts) > 1 else ""

        if inst.isdigit() and vbox == "VBOX_GONE":
            result["spoofed"] = True
            result["instance"] = inst
            # Get spoofed model from resetprop (no root needed)
            out, _ = adb(exe, "shell",
                         "/system/xbin/resetprop ro.product.model 2>/dev/null",
                         serial=serial, timeout=5)
            model = out.strip().split("\n")[-1].strip()
            if model.startswith("SM-"):
                result["model"] = model
    except Exception:
        pass
    return result


def run_spoof(exe, serial, instance, paths, log_fn=print):
    """Deploy the spoofer. Returns (success: bool, message: str)."""
    log_fn(f"--- Deploying (instance {instance}) ---")
    log_fn("")
    log_fn("[PUSH] Uploading files...")
    files = [
        (paths["spoof.sh"], "/data/local/tmp/spoof.sh"),
        (paths["test.sh"], "/data/local/tmp/test.sh"),
        (paths["sensors64_patched.so"], "/data/local/tmp/sensors64_patched.so"),
        (paths["sensors32_patched.so"], "/data/local/tmp/sensors32_patched.so"),
        (paths["magisk64"], "/data/local/tmp/magisk64"),
    ]
    for key, remote, label in [
        ("gl_spoof.so", "/data/local/tmp/gl_spoof.so", "GL string hook (64-bit)"),
        ("gl_spoof32.so", "/data/local/tmp/gl_spoof32.so", "GL string hook (32-bit)"),
        ("gl_spoof.conf", "/data/local/tmp/gl_spoof.conf", None),
    ]:
        if key in paths:
            files.append((paths[key], remote))
            if label:
                log_fn(f"  [GL]  {label} embedded")

    for local, remote in files:
        out_push, rc = adb(exe, "push", local, remote, serial=serial)
        if rc != 0:
            log_fn(f"  [ERR] push {os.path.basename(local)}: {out_push.strip()}")
            return False, "Failed to push files"
        log_fn(f"  [OK]  {os.path.basename(local)} -> {remote}")

    log_fn("")
    log_fn("[RUN] Applying spoofer...")
    out, rc = adb_root_shell(exe, f"/data/local/tmp/spoof.sh {instance}", serial=serial)
    log_fn(out)
    if rc != 0 and "SPOOF v7 COMPLETE" not in out:
        return False, "Spoofer execution failed"

    time.sleep(1)
    log_fn("[TEST] Validating...")
    out, rc = adb_root_shell(exe, "/data/local/tmp/test.sh", serial=serial)
    log_fn(out)

    if "ALL CLEAR" in out:
        log_fn("")
        log_fn("[OK] Deployment successful - device is clean")
        return True, "ALL CLEAR - 25/25 PASS"
    elif re.search(r'CRIT:\s*[1-9]', out):
        return False, "CRITICAL detection failures found"
    else:
        return False, "Some tests failed - check output"


def run_test(exe, serial, paths, log_fn=print):
    """Run test only. Returns (success: bool, message: str)."""
    log_fn("--- Test Only ---")
    out_push, rc = adb(exe, "push", paths["test.sh"], "/data/local/tmp/test.sh", serial=serial)
    if rc != 0:
        return False, "Failed to push test.sh"
    log_fn(f"  [OK]  test.sh pushed")
    log_fn("")
    out, rc = adb_root_shell(exe, "/data/local/tmp/test.sh", serial=serial)
    log_fn(out)
    if "ALL CLEAR" in out:
        return True, "ALL CLEAR - 25/25 PASS"
    elif re.search(r'CRIT:\s*[1-9]', out):
        return False, "CRITICAL detection failures"
    else:
        return False, "Some tests failed"


def _extract_gsf_hex(output):
    """Parse GSF hex ID from get_gsfid.sh output."""
    for line in output.split("\n"):
        if "GSF ID (hex):" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return None


def _root_exec_simple(exe, serial, command, timeout=10):
    """Execute a simple root command and return output. Tries su methods, then init service.
    For quick one-off root commands (not full script execution)."""
    # Try .s pipe
    out, rc = adb(exe, "shell", f"echo '{command}' | /system/xbin/.s",
                  serial=serial, timeout=timeout)
    if rc == 0 and out.strip() and not _is_su_error(out):
        return out
    # Try bare su
    out, rc = adb(exe, "shell", f"echo '{command}' | su",
                  serial=serial, timeout=timeout)
    if rc == 0 and out.strip() and not _is_su_error(out):
        return out
    # Try init service
    if _has_init_service(exe, serial):
        out, _ = _init_service_exec(exe, command, serial=serial, timeout=timeout)
        return out
    return out


def _try_init_gsf(exe, serial, log_fn=print):
    """Try to initialize the GSF database by triggering Google Services checkin.
    Returns True if the database exists (or was created), False otherwise."""
    # Check if database already exists
    out = _root_exec_simple(exe, serial,
        "ls /data/data/com.google.android.gsf/databases/gservices.db 2>/dev/null && echo DB_EXISTS")
    if "DB_EXISTS" in out:
        return True

    log_fn("  GSF database not found — attempting to initialize...")
    log_fn("")

    # Try triggering the GSF checkin service (creates the database + android_id)
    for attempt_cmd, desc in [
        # Trigger checkin service directly
        ("am startservice com.google.android.gsf/.update.SystemUpdateService",
         "Starting GSF SystemUpdateService"),
        # Broadcast a connectivity change to trigger checkin
        ("am broadcast -a android.net.conn.CONNECTIVITY_CHANGE",
         "Broadcasting connectivity change"),
        # Force-stop and restart GMS to trigger initialization
        ("am force-stop com.google.android.gms && am startservice com.google.android.gms/.chimera.GmsIntentOperationService",
         "Restarting Google Play Services"),
        # Direct checkin broadcast
        ("am broadcast -a com.google.android.gms.checkin.CHECKIN_NOW",
         "Broadcasting checkin request"),
    ]:
        log_fn(f"  {desc}...")
        _root_exec_simple(exe, serial, attempt_cmd, timeout=15)

    # Wait for database to appear
    log_fn("")
    log_fn("  Waiting for GSF to initialize (up to 15s)...")
    for i in range(6):
        time.sleep(2.5)
        out = _root_exec_simple(exe, serial,
            "ls /data/data/com.google.android.gsf/databases/gservices.db 2>/dev/null && echo DB_EXISTS")
        if "DB_EXISTS" in out:
            log_fn("  GSF database created!")
            return True

    return False


def run_register(exe, serial, paths, log_fn=print, clipboard_fn=None,
                 open_browser_fn=None, wait_fn=None):
    """Full registration flow: extract GSF ID, copy to clipboard, open browser,
    wait for user, then auto-cleanup. Returns (success: bool, message: str)."""
    import webbrowser

    log_fn("--- Play Protect Registration ---")
    log_fn("")

    # Step 0: Ensure GSF database exists (try to create it if missing)
    if not _try_init_gsf(exe, serial, log_fn=log_fn):
        log_fn("")
        log_fn("[ERR] You need to sign into a Google account first!")
        log_fn("")
        log_fn("  How to fix:")
        log_fn("    1. Go to BlueStacks")
        log_fn("    2. Open the Play Store app")
        log_fn("    3. Sign in with any Google account")
        log_fn("    4. Wait 30 seconds")
        log_fn("    5. Come back here and click Register again")
        return False, "Sign into Google account in BlueStacks first, then try again"

    # Step 1: Extract GSF ID
    log_fn("[1/3] Getting your device code...")
    out_push, rc = adb(exe, "push", paths["get_gsfid.sh"],
                       "/data/local/tmp/get_gsfid.sh", serial=serial)
    if rc != 0:
        return False, "Failed to push get_gsfid.sh"
    out, rc = adb_root_shell(exe, "/data/local/tmp/get_gsfid.sh", serial=serial)

    gsf_hex = _extract_gsf_hex(out)
    if not gsf_hex:
        log_fn("")
        log_fn("[ERR] Could not get device code.")
        log_fn("  Sign into a Google account in BlueStacks, wait 30 seconds, try again.")
        return False, "Sign into Google account in BlueStacks first, then try again"

    log_fn(f"  Your code: {gsf_hex}")
    log_fn("")

    # Step 2: Copy to clipboard + open browser
    log_fn("[2/3] Code copied to clipboard! Opening browser...")
    if clipboard_fn:
        clipboard_fn(gsf_hex)
    else:
        try:
            import subprocess as sp
            proc = sp.Popen(["clip"], stdin=sp.PIPE)
            proc.communicate(gsf_hex.encode())
        except Exception:
            log_fn(f"  Could not copy automatically. Your code is: {gsf_hex}")
    log_fn("")
    log_fn("  ================================================")
    log_fn("  A webpage will open. Here's what to do:")
    log_fn("")
    log_fn("    1. Sign into your Google account on the page")
    log_fn("    2. Click the text box on the page")
    log_fn("    3. Press Ctrl+V to paste your code")
    log_fn("    4. Click the 'Register' button on the page")
    log_fn("    5. Come back here and click 'Done - Continue'")
    log_fn("  ================================================")
    log_fn("")
    try:
        if open_browser_fn:
            open_browser_fn("https://www.google.com/android/uncertified")
        else:
            webbrowser.open("https://www.google.com/android/uncertified")
    except Exception:
        log_fn("  Could not open browser. Go to:")
        log_fn("  https://www.google.com/android/uncertified")
    log_fn("")

    # Step 3: Wait for user, then cleanup
    if wait_fn:
        wait_fn()
    else:
        log_fn("Press ENTER when you've registered on the webpage...")
        try:
            input()
        except EOFError:
            pass

    log_fn("")
    log_fn("[3/3] Cleaning up...")
    out_push, rc = adb(exe, "push", paths["register.sh"],
                       "/data/local/tmp/register.sh", serial=serial)
    if rc != 0:
        return False, "Failed to push register.sh"
    out, rc = adb_root_shell(exe, "/data/local/tmp/register.sh", serial=serial)
    log_fn(out)

    log_fn("")
    log_fn("All done! Reboot BlueStacks and wait 15-30 minutes.")
    log_fn("Play Protect will show as registered after the reboot.")
    return True, f"Registered! Reboot BlueStacks and wait 15-30 min."


def run_cleanup(exe, serial, paths, log_fn=print):
    """Post-registration cleanup. Returns (success: bool, message: str)."""
    log_fn("--- Post-Registration Cleanup ---")
    out_push, rc = adb(exe, "push", paths["register.sh"],
                       "/data/local/tmp/register.sh", serial=serial)
    if rc != 0:
        return False, "Failed to push register.sh"
    log_fn("")
    out, rc = adb_root_shell(exe, "/data/local/tmp/register.sh", serial=serial)
    log_fn(out)
    if rc != 0:
        return False, "Cleanup failed"
    return True, "Cleanup complete"


def run_preflight(exe, serial, paths, log_fn=print):
    """Run pre-flight checks. Returns True if ready."""
    if not check_root(exe, serial):
        # Try auto-enabling root + rooting feature in BlueStacks config
        fixed = _ensure_bluestacks_config(log_fn=log_fn)
        if fixed:
            log_fn(f"[FIX] Enabled root access for: {', '.join(fixed)}")
        log_fn("[ERR] No root access.")
        log_fn("      Close and restart this BlueStacks instance, then try again.")
        log_fn("      (Config has been auto-fixed — just needs a restart to apply.)")
        return False
    log_fn("[OK] Root access confirmed")

    if not check_magisk(exe, serial):
        # Try to install Magisk — but don't fail if it doesn't work,
        # since spoof.sh can self-install resetprop from pushed magisk64
        if install_magisk(exe, serial, paths, log_fn=log_fn):
            log_fn("[OK] KitsuneMask installed")
        else:
            log_fn("[OK] resetprop will be auto-installed by spoof.sh")
    else:
        log_fn("[OK] KitsuneMask/resetprop available")
    return True


# =============================================================================
#  GUI
# =============================================================================

def _random_instance_id():
    """Generate a random instance ID (0-255) for unique device identity."""
    import random
    return random.randint(0, 255)


def launch_gui():
    """Launch the tkinter GUI."""
    import tkinter as tk
    from tkinter import scrolledtext

    # --- Find ADB upfront ---
    exe = find_adb()

    # --- Auto-enable root + ADB on all BlueStacks instances ---
    _fixed = _ensure_bluestacks_config()

    # --- State ---
    tmpdir = None
    paths = None

    def extract():
        nonlocal tmpdir, paths
        if tmpdir is None:
            tmpdir, paths = extract_assets()
        return paths

    def cleanup_tmp():
        nonlocal tmpdir
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
            tmpdir = None

    # --- Window ---
    root = tk.Tk()
    root.title("OSRS Spoofer v7")
    root.geometry("700x600")
    root.configure(bg="#1a1a2e")
    root.resizable(True, True)

    # Colors
    BG = "#1a1a2e"
    FG = "#e0e0e0"
    ACCENT = "#e94560"
    BTN_BG = "#16213e"
    BTN_ACTIVE = "#0f3460"
    ENTRY_BG = "#0f3460"
    OK_COLOR = "#4ecca3"
    ERR_COLOR = "#e94560"

    # --- Title ---
    title_frame = tk.Frame(root, bg=BG)
    title_frame.pack(fill="x", padx=15, pady=(12, 4))
    tk.Label(title_frame, text="OSRS Anti-Detection Spoofer v7",
             font=("Segoe UI", 16, "bold"), fg=ACCENT, bg=BG).pack(side="left")

    # --- How To Use ---
    MUTED = "#888"
    help_text = (
        "1. Open BlueStacks  (root + ADB are enabled automatically)\n"
        "2. Click  Spoof  to make the emulator look like a real phone\n"
        "     Run after every reboot. If it fails, restart the instance and try again.\n"
        "3. Click  Test  to verify everything is working (25/25 = good)\n"
        "4. Register  = certifies with Google Play Protect (optional, one-time)\n"
        "     Sign into a Google account in BlueStacks first.\n"
        "     It copies a code to your clipboard - just paste it on the page that opens."
    )
    tk.Label(root, text=help_text, font=("Segoe UI", 8), fg=MUTED, bg=BG,
             justify="left", anchor="w").pack(fill="x", padx=18, pady=(0, 8))

    # --- Device Selection ---
    dev_frame = tk.LabelFrame(root, text=" Select Device ",
                              font=("Segoe UI", 10, "bold"),
                              fg=FG, bg=BG, bd=1, relief="groove",
                              highlightbackground="#333", highlightthickness=1)
    dev_frame.pack(fill="x", padx=15, pady=(0, 8))

    device_var = tk.StringVar(value="")
    device_widgets = []

    status_label = tk.Label(dev_frame, text="", font=("Segoe UI", 9), fg=FG, bg=BG)
    status_label.pack(anchor="w", padx=10, pady=(5, 2))

    device_inner = tk.Frame(dev_frame, bg=BG)
    device_inner.pack(fill="x", padx=10, pady=(0, 5))

    def refresh_devices():
        for w in device_widgets:
            w.destroy()
        device_widgets.clear()

        if not exe:
            status_label.config(text="ADB not found - install BlueStacks",
                                fg=ERR_COLOR)
            return

        devices = detect_devices(exe)
        if not devices:
            status_label.config(
                text="No devices - start BlueStacks with ADB + root enabled",
                fg=ERR_COLOR)
            return

        status_label.config(text=f"{len(devices)} device(s) connected",
                            fg=OK_COLOR)

        # Check spoof status for each device (quick ADB queries)
        for dev in devices:
            serial = dev["serial"]
            bs_name = dev["display_name"] or serial
            status = check_spoof_status(exe, serial)

            row = tk.Frame(device_inner, bg=BG)
            row.pack(anchor="w", fill="x")
            device_widgets.append(row)

            rb = tk.Radiobutton(row, text=bs_name,
                                variable=device_var, value=serial,
                                font=("Segoe UI", 10), fg=FG, bg=BG,
                                selectcolor=ENTRY_BG, activebackground=BG,
                                activeforeground=FG, highlightthickness=0)
            rb.pack(side="left")

            if status["spoofed"]:
                detail_parts = []
                if status["model"]:
                    detail_parts.append(status["model"])
                if status["instance"]:
                    detail_parts.append(f"#{status['instance']}")
                detail_str = f"  ({', '.join(detail_parts)})" if detail_parts else ""
                tag = tk.Label(row, text=f"\u2713 Spoofed{detail_str}",
                               font=("Segoe UI", 9, "bold"), fg=OK_COLOR, bg=BG)
                tag.pack(side="left", padx=(4, 0))
            else:
                tag = tk.Label(row, text="\u2717 Not spoofed",
                               font=("Segoe UI", 9), fg="#666", bg=BG)
                tag.pack(side="left", padx=(4, 0))

        if devices and not device_var.get():
            device_var.set(devices[0]["serial"])

    btn_row_top = tk.Frame(dev_frame, bg=BG)
    btn_row_top.pack(fill="x", padx=10, pady=(0, 8))
    tk.Button(btn_row_top, text="Refresh", command=refresh_devices,
              font=("Segoe UI", 9), fg=FG, bg=BTN_BG, activebackground=BTN_ACTIVE,
              activeforeground=FG, bd=0, padx=12, pady=3, cursor="hand2"
              ).pack(side="left")

    # --- Action Buttons ---
    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(fill="x", padx=15, pady=(0, 3))

    running = False

    def set_running(state):
        nonlocal running
        running = state
        state_str = "disabled" if state else "normal"
        for btn in action_buttons:
            btn.config(state=state_str)

    def log_to_gui(text):
        output_text.config(state="normal")
        output_text.insert("end", text + "\n")
        output_text.see("end")
        output_text.config(state="disabled")

    def clear_log():
        output_text.config(state="normal")
        output_text.delete("1.0", "end")
        output_text.config(state="disabled")

    # --- Register flow state ---
    register_event = threading.Event()
    continue_btn_ref = [None]  # mutable ref for cross-thread cleanup

    def gui_clipboard_copy(text):
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()

    def show_continue_button():
        btn = tk.Button(btn_frame, text=" Done - Continue ",
                        command=lambda: register_event.set(),
                        font=("Segoe UI", 10, "bold"),
                        fg="#1a1a2e", bg="#f0c040",
                        activebackground=BTN_ACTIVE,
                        activeforeground="white",
                        bd=0, padx=16, pady=6, cursor="hand2")
        btn.pack(side="right", padx=(10, 0))
        continue_btn_ref[0] = btn

    def hide_continue_button():
        if continue_btn_ref[0]:
            continue_btn_ref[0].destroy()
            continue_btn_ref[0] = None

    def run_action(action_name):
        if running:
            return
        serial = device_var.get()
        if not serial:
            log_to_gui("[ERR] No device selected - click Refresh")
            return

        clear_log()
        set_running(True)
        result_label.config(text="Running...", fg="#f0c040")

        def worker():
            try:
                p = extract()
                if action_name == "spoof":
                    log_to_gui("Running pre-flight checks...")
                    if not run_preflight(exe, serial, p, log_fn=log_to_gui):
                        root.after(0, lambda: result_label.config(
                            text="Pre-flight FAILED", fg=ERR_COLOR))
                        return
                    log_to_gui("")
                    instance_id = _random_instance_id()
                    ok, msg = run_spoof(exe, serial, instance_id, p,
                                        log_fn=log_to_gui)
                elif action_name == "test":
                    ok, msg = run_test(exe, serial, p, log_fn=log_to_gui)
                elif action_name == "register":
                    register_event.clear()

                    def clipboard_fn(text):
                        root.after(0, lambda: gui_clipboard_copy(text))
                        time.sleep(0.1)  # let tk process

                    def open_browser_fn(url):
                        import webbrowser
                        webbrowser.open(url)

                    def wait_for_user():
                        root.after(0, lambda: result_label.config(
                            text="Paste code in browser (Ctrl+V), register, then click 'Done - Continue'",
                            fg="#f0c040"))
                        root.after(0, show_continue_button)
                        register_event.wait()
                        root.after(0, hide_continue_button)

                    ok, msg = run_register(
                        exe, serial, p, log_fn=log_to_gui,
                        clipboard_fn=clipboard_fn,
                        open_browser_fn=open_browser_fn,
                        wait_fn=wait_for_user)
                else:
                    ok, msg = False, "Unknown action"

                color = OK_COLOR if ok else ERR_COLOR
                root.after(0, lambda: result_label.config(text=msg, fg=color))
            except Exception as e:
                root.after(0, lambda: result_label.config(
                    text=f"Error: {e}", fg=ERR_COLOR))
                log_to_gui(f"\n[EXCEPTION] {e}")
            finally:
                root.after(0, hide_continue_button)
                root.after(0, lambda: set_running(False))
                # Refresh device list to update spoof status indicators
                root.after(500, refresh_devices)

        threading.Thread(target=worker, daemon=True).start()

    action_buttons = []

    spoof_btn = tk.Button(btn_frame, text="  Spoof  ",
                          command=lambda: run_action("spoof"),
                          font=("Segoe UI", 12, "bold"), fg="white", bg=ACCENT,
                          activebackground=BTN_ACTIVE, activeforeground="white",
                          bd=0, padx=24, pady=8, cursor="hand2")
    spoof_btn.pack(side="left", padx=(0, 10))
    action_buttons.append(spoof_btn)

    test_btn = tk.Button(btn_frame, text="  Test  ",
                         command=lambda: run_action("test"),
                         font=("Segoe UI", 12, "bold"), fg="white", bg=OK_COLOR,
                         activebackground=BTN_ACTIVE, activeforeground="white",
                         bd=0, padx=24, pady=8, cursor="hand2")
    test_btn.pack(side="left", padx=(0, 10))
    action_buttons.append(test_btn)

    register_btn = tk.Button(btn_frame, text=" Register ",
                             command=lambda: run_action("register"),
                             font=("Segoe UI", 10), fg="white", bg="#555",
                             activebackground=BTN_ACTIVE,
                             activeforeground="white",
                             bd=0, padx=14, pady=6, cursor="hand2")
    register_btn.pack(side="left")
    action_buttons.append(register_btn)

    # --- Result Label ---
    result_label = tk.Label(root, text="Ready", font=("Segoe UI", 11, "bold"),
                            fg="#888", bg=BG)
    result_label.pack(fill="x", padx=15, pady=(5, 5))

    # --- Log Output ---
    log_frame = tk.LabelFrame(root, text=" Output ", font=("Segoe UI", 10, "bold"),
                              fg=FG, bg=BG, bd=1, relief="groove",
                              highlightbackground="#333", highlightthickness=1)
    log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 12))

    output_text = scrolledtext.ScrolledText(log_frame, wrap="word",
                                            font=("Consolas", 9), fg=FG,
                                            bg="#0a0a1a", insertbackground=FG,
                                            bd=0, padx=8, pady=8,
                                            state="disabled")
    output_text.pack(fill="both", expand=True, padx=5, pady=5)

    # --- Initial device scan ---
    refresh_devices()

    # --- Run ---
    root.protocol("WM_DELETE_WINDOW", lambda: (cleanup_tmp(), root.destroy()))
    root.mainloop()


# =============================================================================
#  CLI MAIN (legacy / fallback)
# =============================================================================

def main():
    # If no arguments provided, launch GUI
    if len(sys.argv) == 1:
        launch_gui()
        return

    parser = argparse.ArgumentParser(
        description="BlueStacks OSRS Anti-Detection Spoofer (single-file edition)")
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
                        help="ADB device serial (e.g. emulator-5554)")
    parser.add_argument("--skip-checks", action="store_true",
                        help="Skip pre-flight checks (root, Magisk)")
    parser.add_argument("--gui", action="store_true",
                        help="Launch the GUI")
    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return

    print("=" * 50)
    print("  BlueStacks OSRS Anti-Detection Spoofer")
    print("  (single-file edition)")
    print("=" * 50)
    print()

    # --- Auto-enable root + ADB on all instances ---
    _ensure_bluestacks_config()

    # --- Find ADB ---
    exe = args.adb or find_adb()
    if not exe:
        print("[ERR] Cannot find ADB.")
        print()
        print("  BlueStacks ADB is usually at:")
        print(r"      C:\Program Files\BlueStacks_nxt\HD-Adb.exe")
        print()
        print("  If you have Android SDK, ensure adb is on your PATH.")
        print("  Or specify manually: python osrs_spoof.py --adb <path>")
        sys.exit(1)
    print(f"[ADB] {exe}")

    # --- Check device ---
    devices = detect_devices(exe)
    if not devices:
        print("[ERR] No device connected.")
        print()
        print("  Make sure BlueStacks is running and ADB is enabled:")
        print("  BlueStacks Settings > Advanced > Enable Android Debug Bridge (ADB)")
        sys.exit(1)

    serials = [d["serial"] for d in devices]
    if args.device:
        if args.device not in serials:
            print(f"[ERR] Device '{args.device}' not found. Connected: {', '.join(serials)}")
            sys.exit(1)
        serial = args.device
    elif len(devices) > 1:
        print(f"[ERR] Multiple devices connected: {', '.join(serials)}")
        print("      Use --device <serial> to select one.")
        sys.exit(1)
    else:
        serial = serials[0]

    print(f"[DEV] {serial}")
    print()

    # --- Extract embedded assets ---
    tmpdir, paths = extract_assets()
    try:
        # --- Pre-flight checks (skip for --test which just reads state) ---
        if not args.skip_checks and not args.test:
            if not check_root(exe, serial):
                print("[ERR] No root access on device.")
                print()
                print("  Enable root in BlueStacks:")
                print("  Settings > Advanced > Enable root access (check the box)")
                print("  Then restart the instance.")
                sys.exit(1)
            print("[OK] Root access confirmed")

            if not check_magisk(exe, serial):
                if install_magisk(exe, serial, paths):
                    print("[OK] KitsuneMask installed")
                else:
                    print("[OK] resetprop will be auto-installed by spoof.sh")
            else:
                print("[OK] KitsuneMask/resetprop available")
            print()

        _run_mode(args, exe, serial, paths)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _run_mode(args, exe, serial, paths):
    """Execute the selected mode (CLI only)."""

    if args.register:
        ok, msg = run_register(exe, serial, paths)
        if not ok:
            sys.exit(1)
        return

    if args.cleanup:
        ok, msg = run_cleanup(exe, serial, paths)
        if not ok:
            sys.exit(1)
        return

    if args.test:
        print("--- Test Only Mode ---")
        if not adb_push(exe, paths["test.sh"], "/data/local/tmp/test.sh", serial=serial):
            print("[ERR] Failed to push test.sh. Aborting.")
            sys.exit(1)
        print()
        out, rc = adb_root_shell(exe, "/data/local/tmp/test.sh", serial=serial)
        print(out)
        exit_code = parse_test_results(out, rc)
        sys.exit(exit_code)

    print(f"--- Deploying (instance {args.instance}) ---")
    print()

    print("[PUSH] Uploading files...")
    files = [
        (paths["spoof.sh"], "/data/local/tmp/spoof.sh"),
        (paths["test.sh"], "/data/local/tmp/test.sh"),
        (paths["sensors64_patched.so"], "/data/local/tmp/sensors64_patched.so"),
        (paths["sensors32_patched.so"], "/data/local/tmp/sensors32_patched.so"),
        (paths["magisk64"], "/data/local/tmp/magisk64"),
    ]

    gl64 = paths.get("gl_spoof.so")
    gl32 = paths.get("gl_spoof32.so")
    gl_conf = paths.get("gl_spoof.conf")
    if gl64:
        files.append((gl64, "/data/local/tmp/gl_spoof.so"))
        print("  [GL]  GL string hook (64-bit) embedded")
    if gl32:
        files.append((gl32, "/data/local/tmp/gl_spoof32.so"))
        print("  [GL]  GL string hook (32-bit) embedded")
    if gl_conf:
        files.append((gl_conf, "/data/local/tmp/gl_spoof.conf"))

    for local, remote in files:
        if not adb_push(exe, local, remote, serial=serial):
            print("[ERR] Failed to push files. Aborting.")
            sys.exit(1)

    print()
    print("[RUN] Applying spoofer...")
    out, rc = adb_root_shell(exe, f"/data/local/tmp/spoof.sh {args.instance}", serial=serial)
    print(out)
    if rc != 0:
        if "SPOOF v7 COMPLETE" in out:
            print("[WARN] Spoofer completed with property failures (see above).")
        else:
            print("[ERR] Spoofer execution failed (root shell error).")
            sys.exit(1)

    time.sleep(1)

    print("[TEST] Validating...")
    out, rc = adb_root_shell(exe, "/data/local/tmp/test.sh", serial=serial)
    print(out)
    exit_code = parse_test_results(out, rc)
    if exit_code == 0:
        print()
        print("[OK] Deployment successful - device is clean")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
