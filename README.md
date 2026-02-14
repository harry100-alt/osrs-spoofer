# BlueStacks OSRS Anti-Detection Spoofer v7

Makes BlueStacks 5.x completely undetectable for Old School RuneScape, with unique device fingerprints per instance.

## Quick Start (GUI)

```bash
python osrs_spoof.py
```

A GUI opens with device selection, one-click Spoof/Test/Register buttons, and live output.

## Quick Start (CLI)

```bash
python osrs_spoof.py --instance 0                # Spoof instance 0 (default)
python osrs_spoof.py --instance 3                 # Spoof instance 3 (unique identity)
python osrs_spoof.py --test --instance 0          # Test only (validate detection vectors)
python osrs_spoof.py --register --instance 0      # Get GSF ID for Play Protect
python osrs_spoof.py --cleanup --instance 0       # Post-registration cleanup
```

## Requirements

- BlueStacks 5.x (Android 11 / Pie64)
- Python 3.7+
- That's it — root, ADB, and dependencies are configured automatically

## How It Works

The spoofer applies 12 layers of anti-detection to make BlueStacks indistinguishable from a real Samsung Galaxy phone. Run it after every reboot.

### Layer 1: File System (bind mounts)
- Removes `/dev/vboxguest`, `/dev/vboxuser`
- Hides `/sys/module/vboxguest`, `/sys/module/vboxsf`
- Hides PCI bus artifacts and BlueStacks drivers
- Removes `/data/.bluestacks.prop`, hides `/boot/bstsetup.env`
- Unmounts and hides `/mnt/windows`
- Hides BlueStacks system apps

### Layer 2: /proc Spoofing
- `/proc/bus/input/devices` — Samsung Galaxy touchscreen + fingerprint
- `/proc/net/dev` — wlan0 + rmnet_data0 (no eth0)
- `/proc/modules` — wlan + sec_nfc only
- `/proc/cpuinfo` — ARM64 Exynos 2200 (8-core)
- `/proc/version` — Android 14 kernel
- `/proc/mounts` — vboxsf entries filtered

### Layer 3: Library Patching
- `libandroid_runtime.so` — "bluestacks" strings replaced
- `libhoudini.so` / `libndk_translation.so` — hidden via bind mounts

### Layer 4: Property Spoofing (resetprop)
- 90+ properties across all Android namespaces
- Samsung Galaxy S22/S23/S21 device profiles (8 variants)
- CTS/Play Protect properties (debuggable=0, secure=1, etc.)
- Verified boot state, encryption status, SELinux

### Layer 5: GL String Spoofing (LD_PRELOAD)
- Native `glGetString()` / `glGetStringi()` / `eglQueryString()` hooks
- Replaces GL_VENDOR, GL_RENDERER, GL_VERSION at the C library level
- Hides host GPU (NVIDIA/Intel) behind Qualcomm Adreno identity
- Configurable via `gl_spoof.conf`

### Layer 6: Instance Identity
- Unique Android ID per instance (deterministic from instance number)
- Unique serial number per instance
- Unique operator identity per instance

## Multi-Instance Support

Each BlueStacks instance gets a unique device identity based on its instance number. Clone instances are fully supported — the spoofer auto-detects available instances and handles root access on clones via an init service.

## Device Profiles

8 Samsung Galaxy device profiles, selected by instance ID:

| ID % 8 | Device | Model | Chipset |
|---------|--------|-------|---------|
| 0 | S22 Ultra | SM-S908E | Exynos 2200 |
| 1 | S22 | SM-S901E | Exynos 2200 |
| 2 | S22+ | SM-S906E | Exynos 2200 |
| 3 | S23 | SM-S911B | Snapdragon 8 Gen 2 |
| 4 | S23+ | SM-S916B | Snapdragon 8 Gen 2 |
| 5 | S23 Ultra | SM-S918B | Snapdragon 8 Gen 2 |
| 6 | S22 Ultra | SM-S908B | Exynos 2200 |
| 7 | S21 | SM-G991B | Exynos 2200 |

## Play Protect Certification

1. Click **Spoof** (or run `--instance N`)
2. Click **Register** (or run `--register`) — copies GSF ID to clipboard
3. Paste on the page that opens and submit
4. Reboot BlueStacks and check Play Store settings

## Test Results

```
PASS: 25 | FAIL: 0 | CRIT: 0
>>> ALL CLEAR <<<
```

## Building GL Hook (from source)

Requires Android NDK r27c+:

```bash
cd gl-hook
./build.sh /path/to/android-ndk-r27c
```

Pre-compiled binaries for x86_64 and x86 are included.
