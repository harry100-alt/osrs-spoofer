# BlueStacks OSRS Anti-Detection Spoofer v7

Makes BlueStacks 5.x completely undetectable for Old School RuneScape, with unique device fingerprints per instance.

## Download

Download **`osrs_spoof.py`** — that's the only file you need. Everything is bundled inside it.

## Usage

Double-click or run:

```bash
python osrs_spoof.py
```

A GUI opens with device selection, one-click Spoof/Test/Register buttons, and live output.

### CLI

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

1. **File System** — removes VirtualBox devices, hides BlueStacks files and apps via bind mounts
2. **/proc Spoofing** — fakes input devices, network interfaces, CPU info, kernel version, loaded modules
3. **Library Patching** — replaces "bluestacks" strings in runtime libraries, hides ARM translation layers
4. **Property Spoofing** — 90+ Android properties set via resetprop (build fingerprint, model, CTS flags)
5. **GL String Spoofing** — native LD_PRELOAD hook replaces GPU vendor/renderer/version strings
6. **Instance Identity** — unique Android ID, serial number, and operator per instance

## Multi-Instance Support

Each BlueStacks instance gets a unique device identity based on its instance number. Clone instances are fully supported.

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
2. Click **Register** — copies GSF ID to clipboard
3. Paste on the page that opens and submit
4. Reboot BlueStacks and check Play Store settings

## Test Results

```
PASS: 25 | FAIL: 0 | CRIT: 0
>>> ALL CLEAR <<<
```

## Development

The other files in this repo are source code used to build `osrs_spoof.py`:

```bash
python _build_single.py    # Rebuilds osrs_spoof.py from _tail.py + assets
```
