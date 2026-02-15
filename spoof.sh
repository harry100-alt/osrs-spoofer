#!/system/bin/sh
# =============================================================
# BlueStacks OSRS Anti-Detection Spoofer v7
# =============================================================
# Requires: resetprop (KitsuneMask/Magisk installed to /system)
#
# Usage: echo '/system/bin/sh /data/local/tmp/spoof.sh <instance_id>' | /system/xbin/.s
#        instance_id: 0-255 (unique per account)
# =============================================================

INSTANCE_ID="${1:-0}"
RESETPROP="/system/xbin/resetprop"
SYSGREP="/system/bin/grep"

# Validate INSTANCE_ID is a non-negative integer 0-255
case "$INSTANCE_ID" in
    ''|*[!0-9]*)
        echo "[FATAL] Invalid instance ID: '$INSTANCE_ID' (must be 0-255)"
        exit 1
        ;;
esac
if [ "$INSTANCE_ID" -gt 255 ]; then
    echo "[FATAL] Instance ID $INSTANCE_ID out of range (must be 0-255)"
    exit 1
fi

log() { echo "[SPOOF] $1"; }
ok()  { echo "  [OK] $1"; }
skip(){ echo "  [SKIP] $1"; }
fail(){ echo "  [FAIL] $1"; }

# Verify resetprop is available — auto-install from /data/local/tmp if missing
if [ ! -x "$RESETPROP" ]; then
    MAGISK_SRC="/data/local/tmp/magisk64"
    if [ -f "$MAGISK_SRC" ]; then
        echo "[SETUP] resetprop not found — installing from $MAGISK_SRC"
        # Try remount first (primary instances)
        /system/bin/mount -o remount,rw /system 2>/dev/null
        /system/bin/cp "$MAGISK_SRC" /system/xbin/magisk64 2>/dev/null
        /system/bin/chmod 755 /system/xbin/magisk64 2>/dev/null
        /system/bin/ln -sf /system/xbin/magisk64 /system/xbin/resetprop 2>/dev/null
        /system/bin/ln -sf /system/xbin/magisk64 /system/xbin/magisk 2>/dev/null
        /system/bin/mount -o remount,ro /system 2>/dev/null
        if [ -x "$RESETPROP" ]; then
            echo "  [OK] resetprop installed to /system/xbin/"
        else
            echo "[FATAL] Failed to install resetprop"
            exit 1
        fi
    else
        echo "[FATAL] resetprop not found at $RESETPROP and no magisk64 in /data/local/tmp/"
        exit 1
    fi
fi

# --- Device profiles: Samsung Galaxy flagships ---
# Each instance gets a deterministic device identity
case $(( INSTANCE_ID % 8 )) in
    0) DEV_DEVICE="b0q";   DEV_MODEL="SM-S908E"; DEV_NAME="b0qxxx";  DEV_BUILD_FP="samsung/b0qxxx/b0q:14/UP1A.231005.007/S908EXXS8DWL1:user/release-keys";   DEV_DESC="b0qxxx-user 14 UP1A.231005.007 S908EXXS8DWL1 release-keys";  DEV_INCREMENTAL="S908EXXS8DWL1"; DEV_BOARD="s5e9925";  DEV_PLATFORM="exynos2200"; DEV_HW="samsungexynos2200"; DEV_BOOTLOADER="S908EXXS8DWL1"; DEV_FIRST_API="31"; DEV_FLAVOR="b0qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    1) DEV_DEVICE="r0q";   DEV_MODEL="SM-S901E"; DEV_NAME="r0qxxx";  DEV_BUILD_FP="samsung/r0qxxx/r0q:14/UP1A.231005.007/S901EXXS8DWL2:user/release-keys";   DEV_DESC="r0qxxx-user 14 UP1A.231005.007 S901EXXS8DWL2 release-keys";  DEV_INCREMENTAL="S901EXXS8DWL2"; DEV_BOARD="s5e9925";  DEV_PLATFORM="exynos2200"; DEV_HW="samsungexynos2200"; DEV_BOOTLOADER="S901EXXS8DWL2"; DEV_FIRST_API="31"; DEV_FLAVOR="r0qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    2) DEV_DEVICE="g0q";   DEV_MODEL="SM-S906E"; DEV_NAME="g0qxxx";  DEV_BUILD_FP="samsung/g0qxxx/g0q:14/UP1A.231005.007/S906EXXU8DWL1:user/release-keys";   DEV_DESC="g0qxxx-user 14 UP1A.231005.007 S906EXXU8DWL1 release-keys";  DEV_INCREMENTAL="S906EXXU8DWL1"; DEV_BOARD="s5e9925";  DEV_PLATFORM="exynos2200"; DEV_HW="samsungexynos2200"; DEV_BOOTLOADER="S906EXXU8DWL1"; DEV_FIRST_API="31"; DEV_FLAVOR="g0qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    3) DEV_DEVICE="dm1q";  DEV_MODEL="SM-S911B"; DEV_NAME="dm1qxxx"; DEV_BUILD_FP="samsung/dm1qxxx/dm1q:14/UP1A.231005.007/S911BXXS6DWK3:user/release-keys";  DEV_DESC="dm1qxxx-user 14 UP1A.231005.007 S911BXXS6DWK3 release-keys"; DEV_INCREMENTAL="S911BXXS6DWK3"; DEV_BOARD="kalama";   DEV_PLATFORM="kalama";     DEV_HW="qcom";              DEV_BOOTLOADER="S911BXXS6DWK3"; DEV_FIRST_API="33"; DEV_FLAVOR="dm1qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    4) DEV_DEVICE="dm2q";  DEV_MODEL="SM-S916B"; DEV_NAME="dm2qxxx"; DEV_BUILD_FP="samsung/dm2qxxx/dm2q:14/UP1A.231005.007/S916BXXU6DWK2:user/release-keys";  DEV_DESC="dm2qxxx-user 14 UP1A.231005.007 S916BXXU6DWK2 release-keys"; DEV_INCREMENTAL="S916BXXU6DWK2"; DEV_BOARD="kalama";   DEV_PLATFORM="kalama";     DEV_HW="qcom";              DEV_BOOTLOADER="S916BXXU6DWK2"; DEV_FIRST_API="33"; DEV_FLAVOR="dm2qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    5) DEV_DEVICE="dm3q";  DEV_MODEL="SM-S918B"; DEV_NAME="dm3qxxx"; DEV_BUILD_FP="samsung/dm3qxxx/dm3q:14/UP1A.231005.007/S918BXXS6DWK1:user/release-keys";  DEV_DESC="dm3qxxx-user 14 UP1A.231005.007 S918BXXS6DWK1 release-keys"; DEV_INCREMENTAL="S918BXXS6DWK1"; DEV_BOARD="kalama";   DEV_PLATFORM="kalama";     DEV_HW="qcom";              DEV_BOOTLOADER="S918BXXS6DWK1"; DEV_FIRST_API="33"; DEV_FLAVOR="dm3qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    6) DEV_DEVICE="q2q";   DEV_MODEL="SM-S908B"; DEV_NAME="q2qxxx";  DEV_BUILD_FP="samsung/q2qxxx/q2q:14/UP1A.231005.007/S908BXXS8DWL2:user/release-keys";    DEV_DESC="q2qxxx-user 14 UP1A.231005.007 S908BXXS8DWL2 release-keys";  DEV_INCREMENTAL="S908BXXS8DWL2"; DEV_BOARD="s5e9925";  DEV_PLATFORM="exynos2200"; DEV_HW="samsungexynos2200"; DEV_BOOTLOADER="S908BXXS8DWL2"; DEV_FIRST_API="31"; DEV_FLAVOR="q2qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    7) DEV_DEVICE="o1q";   DEV_MODEL="SM-G991B"; DEV_NAME="o1qxxx";  DEV_BUILD_FP="samsung/o1qxxx/o1q:14/UP1A.231005.007/G991BXXSADWL1:user/release-keys";    DEV_DESC="o1qxxx-user 14 UP1A.231005.007 G991BXXSADWL1 release-keys";  DEV_INCREMENTAL="G991BXXSADWL1"; DEV_BOARD="s5e9925";  DEV_PLATFORM="exynos2200"; DEV_HW="samsungexynos2200"; DEV_BOOTLOADER="G991BXXSADWL1"; DEV_FIRST_API="30"; DEV_FLAVOR="o1qxxx-user"; DEV_BUILD_ID="UP1A.231005.007" ;;
    *) echo "[FATAL] Invalid profile index: $(( INSTANCE_ID % 8 )) (instance=$INSTANCE_ID)"; exit 1 ;;
esac

# Verify device profile was set (guards against unset variables from edge cases)
if [ -z "$DEV_DEVICE" ] || [ -z "$DEV_MODEL" ]; then
    echo "[FATAL] Device profile not initialized. Instance ID: $INSTANCE_ID"
    exit 1
fi

# Unique per-instance values
AID_SUFFIX=$(printf "%02x" $(( (INSTANCE_ID * 7 + 19) % 256 )))
UNIQUE_AID="e6251bc52c04${AID_SUFFIX}98"
SER_MID=$(printf "%04d" $(( (INSTANCE_ID * 37 + 1234) % 10000 )))
UNIQUE_SERIAL="R3CT${SER_MID}ABCD"
OP_SUFFIX=$(printf "%02d" $(( (INSTANCE_ID * 3 + 26) % 100 )))

log "Instance $INSTANCE_ID: $DEV_MODEL ($DEV_DEVICE) AID=$UNIQUE_AID"

# Detect /system block device dynamically (don't assume /dev/sda1)
SYSTEM_DEV=$(mount 2>/dev/null | "$SYSGREP" " /system " | /system/bin/awk '{print $1}' | head -1)
if [ -z "$SYSTEM_DEV" ]; then
    SYSTEM_DEV="/dev/sda1"  # Fallback for typical BlueStacks
    log "Could not detect /system device, using fallback: $SYSTEM_DEV"
fi

# === 0. PERSISTENT PATCHES (sensor HAL + su rename) ===
log "0: Persistent patches"
NEED_REMOUNT=0
SENSOR64_DIRTY=0
SENSOR32_DIRTY=0
SENSOR64_CHECK=$("$SYSGREP" -c "BlueStacks" /system/vendor/lib64/hw/sensors.default.so 2>/dev/null)
SENSOR32_CHECK=$("$SYSGREP" -c "BlueStacks" /system/vendor/lib/hw/sensors.default.so 2>/dev/null)
# Default empty to "0" so missing files don't trigger false dirty
[ -z "$SENSOR64_CHECK" ] && SENSOR64_CHECK="0"
[ -z "$SENSOR32_CHECK" ] && SENSOR32_CHECK="0"
[ "$SENSOR64_CHECK" != "0" ] && [ -f "/data/local/tmp/sensors64_patched.so" ] && { NEED_REMOUNT=1; SENSOR64_DIRTY=1; }
[ "$SENSOR32_CHECK" != "0" ] && [ -f "/data/local/tmp/sensors32_patched.so" ] && { NEED_REMOUNT=1; SENSOR32_DIRTY=1; }
[ -f "/system/xbin/su" ] && NEED_REMOUNT=1

if [ "$NEED_REMOUNT" = "1" ]; then
    if ! /system/bin/mount -o remount,rw $SYSTEM_DEV /system 2>/dev/null; then
        fail "Cannot remount /system RW — sensor patches and su rename will be skipped"
        # Fallback: hide su via bind mount (works on read-only /system, e.g. clone instances)
        # Mount an empty non-executable file over su — makes it appear as empty/broken
        if [ -f "/system/xbin/su" ]; then
            touch /data/local/tmp/.empty_su 2>/dev/null
            chmod 000 /data/local/tmp/.empty_su 2>/dev/null
            if /system/bin/mount -o bind /data/local/tmp/.empty_su /system/xbin/su 2>/dev/null; then
                ok "Hidden su via bind mount (read-only /system)"
            else
                fail "Could not hide su (bind mount also failed)"
            fi
        fi
    else
        if [ "$SENSOR64_DIRTY" = "1" ]; then
            if /system/bin/cp /data/local/tmp/sensors64_patched.so /system/vendor/lib64/hw/sensors.default.so 2>/dev/null; then
                ok "Patched sensor HAL (64-bit)"
            else
                fail "Failed to patch sensor HAL (64-bit)"
            fi
            /system/bin/chmod 644 /system/vendor/lib64/hw/sensors.default.so 2>/dev/null
        fi
        if [ "$SENSOR32_DIRTY" = "1" ]; then
            if /system/bin/cp /data/local/tmp/sensors32_patched.so /system/vendor/lib/hw/sensors.default.so 2>/dev/null; then
                ok "Patched sensor HAL (32-bit)"
            else
                fail "Failed to patch sensor HAL (32-bit)"
            fi
            /system/bin/chmod 644 /system/vendor/lib/hw/sensors.default.so 2>/dev/null
        fi
        if [ -f "/system/xbin/su" ]; then
            if /system/bin/mv /system/xbin/su /system/xbin/.s 2>/dev/null; then
                ok "Renamed su -> .s"
            else
                fail "Failed to rename su -> .s"
            fi
        fi
        /system/bin/mount -o remount,ro $SYSTEM_DEV /system 2>/dev/null
    fi
else
    ok "Persistent patches already applied"
fi

# === 1. VirtualBox devices ===
log "1: VirtualBox devices"
VBOX_OK=1
for vdev in /dev/vboxguest /dev/vboxuser; do
    if [ -e "$vdev" ]; then
        if /system/bin/rm -f "$vdev" 2>/dev/null && [ ! -e "$vdev" ]; then
            ok "Removed $vdev"
        else
            fail "Failed to remove $vdev"
            VBOX_OK=0
        fi
    fi
done
[ "$VBOX_OK" = "1" ] && ok "VirtualBox devices clean"

# === 2. Sysfs modules ===
log "2: Sysfs modules"
SYSFS_OK=1
for mod in vboxguest vboxsf; do
    if [ -d "/sys/module/$mod" ]; then
        # Check if already mounted (idempotent)
        if /system/bin/grep -q " /sys/module/$mod " /proc/self/mountinfo 2>/dev/null; then
            ok "/sys/module/$mod already hidden"
        elif /system/bin/mount -t tmpfs tmpfs "/sys/module/$mod" 2>/dev/null; then
            /system/bin/chmod 000 "/sys/module/$mod" 2>/dev/null
            ok "Hidden /sys/module/$mod"
        else
            fail "Failed to hide /sys/module/$mod"
            SYSFS_OK=0
        fi
    fi
done
[ "$SYSFS_OK" = "1" ] && ok "Sysfs modules clean"

# === 3. PCI bus + drivers ===
log "3: PCI bus"
PCI_OK=1
if [ -d "/proc/bus/pci" ]; then
    if /system/bin/grep -q " /proc/bus/pci " /proc/self/mountinfo 2>/dev/null; then
        ok "/proc/bus/pci already hidden"
    elif ! /system/bin/mount -t tmpfs tmpfs /proc/bus/pci 2>/dev/null; then
        fail "Failed to hide /proc/bus/pci"
        PCI_OK=0
    fi
fi
for drv in vboxguest bstaudio bstcamera bstpgaipc bstvmsg vmw_pvscsi virtio-pci; do
    if [ -d "/sys/bus/pci/drivers/$drv" ]; then
        if /system/bin/grep -q " /sys/bus/pci/drivers/$drv " /proc/self/mountinfo 2>/dev/null; then
            : # Already hidden
        elif /system/bin/mount -t tmpfs tmpfs "/sys/bus/pci/drivers/$drv" 2>/dev/null; then
            /system/bin/chmod 000 "/sys/bus/pci/drivers/$drv" 2>/dev/null
        else
            fail "Failed to hide /sys/bus/pci/drivers/$drv"
            PCI_OK=0
        fi
    fi
done
[ "$PCI_OK" = "1" ] && ok "PCI artifacts clean"

# === 4. BlueStacks files + /mnt/windows ===
log "4: BlueStacks files"
BST_OK=1
[ -f "/data/.bluestacks.prop" ] && /system/bin/mv /data/.bluestacks.prop /data/.bluestacks.prop.bak 2>/dev/null
/system/bin/touch /data/local/tmp/.empty 2>/dev/null
if [ -f "/boot/bstsetup.env" ]; then
    if /system/bin/grep -q " /boot/bstsetup.env " /proc/self/mountinfo 2>/dev/null; then
        ok "bstsetup.env already hidden"
    elif ! /system/bin/mount -o bind /data/local/tmp/.empty /boot/bstsetup.env 2>/dev/null; then
        fail "Failed to hide bstsetup.env"
        BST_OK=0
    fi
fi
# Hide /mnt/windows (jorkSpoofer approach: unmount children, rmdir, fallback to tmpfs)
for share in Documents Pictures InputMapper BstSharedFolder; do
    [ -d "/mnt/windows/$share" ] && { /system/bin/umount "/mnt/windows/$share" 2>/dev/null; rmdir "/mnt/windows/$share" 2>/dev/null; }
done
rm -f /mnt/windows/.nomedia 2>/dev/null
/system/bin/umount /mnt/windows 2>/dev/null
rmdir /mnt/windows 2>/dev/null
if [ -d "/mnt/windows" ]; then
    if ! /system/bin/mount -t tmpfs -o size=0,mode=000 tmpfs /mnt/windows 2>/dev/null; then
        fail "Failed to hide /mnt/windows with tmpfs"
        BST_OK=0
    fi
fi
[ "$BST_OK" = "1" ] && ok "BlueStacks files + /mnt/windows clean"

# === 5. BlueStacks apps ===
log "5: BlueStacks apps"
APP_OK=1
for app in com.bluestacks.BstCommandProcessor com.bluestacks.settings; do
    for dir in /system/app/$app /system/priv-app/$app; do
        if [ -d "$dir" ]; then
            if /system/bin/grep -q " $dir " /proc/self/mountinfo 2>/dev/null; then
                : # Already hidden
            elif ! /system/bin/mount -t tmpfs tmpfs "$dir" 2>/dev/null; then
                fail "Failed to hide $dir"
                APP_OK=0
            fi
        fi
    done
done
[ "$APP_OK" = "1" ] && ok "BlueStacks apps clean"

# === 6. Init scripts ===
log "6: Init scripts"
INIT_OK=1
for rc in RTVboxGuestService.rc; do
    if [ -f "/vendor/etc/init/$rc" ]; then
        /system/bin/touch /data/local/tmp/.empty_rc 2>/dev/null
        if ! /system/bin/mount -o bind /data/local/tmp/.empty_rc "/vendor/etc/init/$rc" 2>/dev/null; then
            fail "Failed to hide /vendor/etc/init/$rc"
            INIT_OK=0
        fi
    fi
done
[ "$INIT_OK" = "1" ] && ok "Init scripts clean"

# === 7. /proc spoofs ===
log "7: /proc spoofs"
export TMPDIR=/data/local/tmp  # Shell needs writable dir for heredoc temp files

# 7a. Input devices
/system/bin/cat > /data/local/tmp/fake_input << 'EOF'
I: Bus=0019 Vendor=0001 Product=0001 Version=0100
N: Name="gpio_keys"
P: Phys=gpio-keys/input0
S: Sysfs=/devices/platform/gpio_keys/input/input0
U: Uniq=
H: Handlers=event0
B: PROP=0
B: EV=3
B: KEY=8000 10000000000000 0

I: Bus=0000 Vendor=0000 Product=0000 Version=0000
N: Name="sec_touchscreen"
P: Phys=
S: Sysfs=/devices/virtual/input/input1
U: Uniq=
H: Handlers=event1
B: PROP=2
B: EV=b
B: KEY=420 0 0 0 0 0
B: ABS=6f3800000000003

I: Bus=0019 Vendor=0001 Product=0001 Version=0100
N: Name="sec_touchkey"
P: Phys=sec_touchkey/input0
S: Sysfs=/devices/virtual/input/input2
U: Uniq=
H: Handlers=event2
B: PROP=0
B: EV=3
B: KEY=4 0 0 0 0 0 0 0

I: Bus=0000 Vendor=0000 Product=0000 Version=0000
N: Name="fingerprint_sensor"
P: Phys=
S: Sysfs=/devices/virtual/input/input4
U: Uniq=
H: Handlers=event4
B: PROP=0
B: EV=3
B: KEY=4 0 0 0

EOF
if /system/bin/grep -q " /proc/bus/input/devices " /proc/self/mountinfo 2>/dev/null; then
    ok "Input devices already spoofed"
elif /system/bin/mount -o bind /data/local/tmp/fake_input /proc/bus/input/devices 2>/dev/null; then
    ok "Spoofed input devices"
else
    fail "Failed to bind-mount fake input devices"
fi

# 7b. Network interfaces
/system/bin/cat > /data/local/tmp/fake_net << 'EOF'
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:  123456      789    0    0    0     0          0         0   123456      789    0    0    0     0       0          0
 wlan0: 98765432   54321    0    0    0     0          0         0 12345678    9876    0    0    0     0       0          0
rmnet_data0:    0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
EOF
if /system/bin/grep -q " /proc/net/dev " /proc/self/mountinfo 2>/dev/null; then
    ok "/proc/net/dev already spoofed"
elif /system/bin/mount -o bind /data/local/tmp/fake_net /proc/net/dev 2>/dev/null; then
    ok "Spoofed /proc/net/dev"
else
    fail "Failed to bind-mount fake /proc/net/dev"
fi

# 7c. Kernel modules
/system/bin/cat > /data/local/tmp/fake_mod << 'EOF'
wlan 8192000 0 - Live 0x0000000000000000
sec_nfc 49152 0 - Live 0x0000000000000000
EOF
if /system/bin/grep -q " /proc/modules " /proc/self/mountinfo 2>/dev/null; then
    ok "/proc/modules already spoofed"
elif /system/bin/mount -o bind /data/local/tmp/fake_mod /proc/modules 2>/dev/null; then
    ok "Spoofed /proc/modules"
else
    fail "Failed to bind-mount fake /proc/modules"
fi

# 7d. /proc/cpuinfo — fake ARM64 (from jorkSpoofer)
/system/bin/cat > /data/local/tmp/fake_cpuinfo << 'CPUEOF'
processor	: 0
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd05
CPU revision	: 0

processor	: 1
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd05
CPU revision	: 0

processor	: 2
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd05
CPU revision	: 0

processor	: 3
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd05
CPU revision	: 0

processor	: 4
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd41
CPU revision	: 0

processor	: 5
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd41
CPU revision	: 0

processor	: 6
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd41
CPU revision	: 0

processor	: 7
BogoMIPS	: 1804.80
Features	: fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp
CPU implementer	: 0x41
CPU architecture: 8
CPU variant	: 0x1
CPU part	: 0xd41
CPU revision	: 0

Hardware	: Exynos 2200
Revision	: 0000
Serial		: 0000000000000000
CPUEOF
/system/bin/mount -o bind /data/local/tmp/fake_cpuinfo /proc/cpuinfo 2>/dev/null && ok "Spoofed /proc/cpuinfo (ARM64)" || skip "cpuinfo bind-mount failed"

# 7e. /proc/version — fake kernel
printf "Linux version 5.10.198-android14-11-g5b8ef77b48ac-ab12345678 #1 SMP PREEMPT Thu Dec 5 12:00:00 UTC 2024\n" > /data/local/tmp/fake_version
/system/bin/mount -o bind /data/local/tmp/fake_version /proc/version 2>/dev/null && ok "Spoofed /proc/version" || skip "version bind-mount failed"

# 7f. /proc/mounts — filter vboxsf entries
"$SYSGREP" -v 'vboxsf\|/mnt/windows' /proc/mounts > /data/local/tmp/fake_mounts 2>/dev/null
/system/bin/mount -o bind /data/local/tmp/fake_mounts /proc/mounts 2>/dev/null && ok "Filtered /proc/mounts (vboxsf hidden)" || skip "mounts filter failed"

# === 8. Patch "bluestacks" from system libraries ===
log "8: Library patching"
LIB_PATCH_OK=1
patch_library() {
    local src="$1"
    local name="$(basename "$src")"
    local dst="/data/local/tmp/patched_${name}"
    [ ! -f "$src" ] && return 0
    if ! "$SYSGREP" -qioa 'bluestacks' "$src" 2>/dev/null; then
        return 0  # Clean already (case-insensitive check)
    fi
    if ! /system/bin/cp "$src" "$dst" 2>/dev/null; then
        fail "Failed to copy $src for patching"
        LIB_PATCH_OK=0
        return 1
    fi
    /system/bin/chmod 755 "$dst" 2>/dev/null
    for pat in bluestacks BlueStacks Bluestacks BLUESTACKS; do
        offsets=$("$SYSGREP" -boa "$pat" "$dst" 2>/dev/null | cut -d: -f1)
        for offset in $offsets; do
            printf 'stockbuild' | dd of="$dst" bs=1 seek="$offset" conv=notrunc 2>/dev/null
        done
    done
    if /system/bin/grep -q " $src " /proc/self/mountinfo 2>/dev/null; then
        : # Already patched from previous run
    elif ! /system/bin/mount -o bind "$dst" "$src" 2>/dev/null; then
        fail "Failed to bind-mount patched $name"
        LIB_PATCH_OK=0
        return 1
    fi
}
patch_library /system/lib/libandroid_runtime.so
patch_library /system/lib64/libandroid_runtime.so
[ "$LIB_PATCH_OK" = "1" ] && ok "Library strings clean"

# === 9. Hide ARM translation libraries ===
log "9: ARM translation hiding"
/system/bin/touch /data/local/tmp/.blocked 2>/dev/null
/system/bin/chmod 000 /data/local/tmp/.blocked 2>/dev/null
for lib in /system/lib/libhoudini.so /system/lib64/libhoudini.so \
           /system/lib/libndk_translation.so /system/lib64/libndk_translation.so \
           /system/bin/houdini /system/bin/houdini64; do
    [ -f "$lib" ] && /system/bin/mount -o bind /data/local/tmp/.blocked "$lib" 2>/dev/null
done
ok "Hidden ARM translation libraries"

# === 10. Property spoofing (ALL via resetprop) ===
log "10: Property spoofing (resetprop)"
SPOOF_OK=0
SPOOF_FAIL=0
rp() {
    local prop="$1" val="$2"
    [ -z "$val" ] && return
    "$RESETPROP" -n "$prop" "$val" 2>/dev/null
    actual=$("$RESETPROP" "$prop" 2>/dev/null)
    if [ "$actual" = "$val" ]; then
        SPOOF_OK=$((SPOOF_OK + 1))
    else
        SPOOF_FAIL=$((SPOOF_FAIL + 1))
        fail "resetprop $prop (expected=$val actual=$actual)"
    fi
}

# Product identity (all namespace variants)
for ns in "" system vendor vendor_dlkm odm product system_ext system_dlkm; do
    if [ -z "$ns" ]; then
        rp "ro.product.brand" "samsung"
        rp "ro.product.manufacturer" "Samsung"
        rp "ro.product.model" "$DEV_MODEL"
        rp "ro.product.name" "$DEV_NAME"
        rp "ro.product.device" "$DEV_DEVICE"
    else
        rp "ro.product.${ns}.brand" "samsung"
        rp "ro.product.${ns}.manufacturer" "Samsung"
        rp "ro.product.${ns}.model" "$DEV_MODEL"
        rp "ro.product.${ns}.name" "$DEV_NAME"
        rp "ro.product.${ns}.device" "$DEV_DEVICE"
    fi
done

# Board/hardware
rp "ro.product.board" "$DEV_BOARD"
rp "ro.board.platform" "$DEV_PLATFORM"
rp "ro.hardware" "$DEV_HW"
rp "ro.boot.hardware" "$DEV_HW"

# Build fingerprint (all partition variants)
rp "ro.build.fingerprint" "$DEV_BUILD_FP"
rp "ro.system.build.fingerprint" "$DEV_BUILD_FP"
rp "ro.system_ext.build.fingerprint" "$DEV_BUILD_FP"
rp "ro.vendor.build.fingerprint" "$DEV_BUILD_FP"
rp "ro.odm.build.fingerprint" "$DEV_BUILD_FP"
rp "ro.bootimage.build.fingerprint" "$DEV_BUILD_FP"
rp "ro.product.build.fingerprint" "$DEV_BUILD_FP"

# Build info
rp "ro.build.display.id" "$DEV_BUILD_ID"
rp "ro.build.id" "$DEV_BUILD_ID"
rp "ro.build.description" "$DEV_DESC"
rp "ro.build.type" "user"
rp "ro.build.tags" "release-keys"
rp "ro.build.flavor" "$DEV_FLAVOR"
rp "ro.build.product" "$DEV_DEVICE"
rp "ro.build.device" "$DEV_DEVICE"
rp "ro.build.version.incremental" "$DEV_INCREMENTAL"
rp "ro.build.version.security_patch" "2024-12-01"
rp "ro.build.characteristics" "nosdcard"

# Version props
rp "ro.build.version.release" "14"
rp "ro.build.version.release_or_codename" "14"
rp "ro.build.version.sdk" "34"
rp "ro.build.version.codename" "REL"

# CPU/ABI (critical for appearing as ARM device)
rp "ro.product.cpu.abi" "arm64-v8a"
rp "ro.product.cpu.abilist" "arm64-v8a,armeabi-v7a,armeabi"
rp "ro.product.cpu.abilist64" "arm64-v8a"
rp "ro.product.cpu.abilist32" "armeabi-v7a,armeabi"
rp "ro.product.first_api_level" "$DEV_FIRST_API"

# Security/CTS props (Play Protect critical)
rp "ro.debuggable" "0"
rp "ro.secure" "1"
rp "ro.adb.secure" "1"
rp "ro.build.selinux" "0"
rp "ro.boot.verifiedbootstate" "green"
rp "ro.boot.flash.locked" "1"
rp "ro.boot.vbmeta.device_state" "locked"
rp "ro.boot.warranty_bit" "0"
rp "sys.oem_unlock_allowed" "0"
rp "ro.boot.veritymode" "enforcing"
rp "ro.crypto.state" "encrypted"

# Boot props
rp "ro.bootloader" "$DEV_BOOTLOADER"
rp "ro.boot.mode" "normal"

# Anti-emulator props
rp "ro.kernel.qemu" "0"
rp "ro.boot.qemu" "0"
rp "ro.dalvik.vm.native.bridge" "0"
rp "ro.enable.native.bridge.exec" "0"
rp "persist.sys.nativebridge" "0"
rp "ro.hardware.egl" "adreno"
rp "ro.opengles.version" "196610"

# Clean BlueStacks-specific props
/system/bin/setprop gsm.sim.bstserial "" 2>/dev/null
/system/bin/setprop ctl.stop bstsvcmgrtest 2>/dev/null
/system/bin/setprop ctl.stop vendor.RTVboxGuestService 2>/dev/null
rp "persist.sys.usb.config" "none"

ok "Properties: $SPOOF_OK OK, $SPOOF_FAIL FAIL"

# === 11. Instance identity ===
log "11: Identity (ID=$INSTANCE_ID)"
settings put secure android_id "$UNIQUE_AID" 2>/dev/null
ACTUAL_AID=$(settings get secure android_id 2>/dev/null)
if [ "$ACTUAL_AID" = "$UNIQUE_AID" ]; then
    ok "Android ID verified: $UNIQUE_AID"
else
    fail "Android ID write failed (expected=$UNIQUE_AID actual=$ACTUAL_AID)"
fi
rp "ro.serialno" "$UNIQUE_SERIAL"
rp "ro.boot.serialno" "$UNIQUE_SERIAL"
rp "gsm.operator.alpha" "T-Mobile"
rp "gsm.operator.numeric" "3102${OP_SUFFIX}"
rp "gsm.sim.operator.alpha" "T-Mobile"
rp "gsm.sim.operator.numeric" "3102${OP_SUFFIX}"
rp "gsm.sim.operator.iso-country" "us"
rp "persist.sys.timezone" "America/New_York"
ok "Set unique identity"

# === 12. GL string spoofing (LD_PRELOAD hook) ===
log "12: GL string hook"
GL_HOOK64="/data/local/tmp/gl_spoof.so"
GL_HOOK32="/data/local/tmp/gl_spoof32.so"
GL_CONF="/data/local/tmp/gl_spoof.conf"
OSRS_PKG="com.jagex.oldschool.android"

if [ -f "$GL_HOOK64" ] || [ -f "$GL_HOOK32" ]; then
    # Build LD_PRELOAD value with whichever hooks are available
    GL_PRELOAD=""
    if [ -f "$GL_HOOK64" ]; then
        GL_PRELOAD="$GL_HOOK64"
        ok "GL hook (64-bit): $GL_HOOK64"
    fi
    if [ -f "$GL_HOOK32" ]; then
        if [ -n "$GL_PRELOAD" ]; then
            GL_PRELOAD="${GL_PRELOAD}:${GL_HOOK32}"
        else
            GL_PRELOAD="$GL_HOOK32"
        fi
        ok "GL hook (32-bit): $GL_HOOK32"
    fi
    # Set the wrap property — Android will LD_PRELOAD our hook(s) into the target app
    /system/bin/setprop "wrap.$OSRS_PKG" "LD_PRELOAD=$GL_PRELOAD"
    ok "GL wrap property set"
    if [ -f "$GL_CONF" ]; then
        ok "GL config: $GL_CONF"
    else
        skip "No gl_spoof.conf (using compiled-in defaults)"
    fi
else
    # Clear stale wrap property if it was previously set but hook is now missing
    CURRENT_WRAP=$(/system/bin/getprop "wrap.$OSRS_PKG" 2>/dev/null)
    if [ -n "$CURRENT_WRAP" ]; then
        "$RESETPROP" --delete "wrap.$OSRS_PKG" 2>/dev/null
        ok "Cleared stale GL wrap property (hook files missing)"
    else
        skip "GL hooks not found (native GL strings not spoofed)"
    fi
fi

# Write instance marker for status checking (used by GUI to detect active spoof)
echo "$INSTANCE_ID" > /data/local/tmp/.spoof_instance
chmod 644 /data/local/tmp/.spoof_instance

# === Done ===
echo ""
echo "=== SPOOF v7 COMPLETE ==="
echo "  Instance:   $INSTANCE_ID"
echo "  Model:      $DEV_MODEL ($DEV_DEVICE)"
echo "  Android ID: $UNIQUE_AID"
echo "  Serial:     $UNIQUE_SERIAL"
echo "  Build FP:   $DEV_BUILD_FP"
echo "  Props:      $SPOOF_OK OK, $SPOOF_FAIL FAIL"
echo "  GL Hook:    $([ -f "$GL_HOOK64" ] || [ -f "$GL_HOOK32" ] && echo "ACTIVE" || echo "NOT INSTALLED")"
echo "  Root:       /system/xbin/.s"
echo "  resetprop:  /system/xbin/resetprop"
echo ""
if [ "$SPOOF_FAIL" -gt 0 ]; then
    echo ">>> WARNING: $SPOOF_FAIL property spoof(s) failed — device may be partially detectable <<<"
    exit 1
else
    echo ">>> Ready to launch OSRS <<<"
fi
