#!/system/bin/sh
# =============================================================
# OSRS Detection Test — validates all vectors are clean
# =============================================================
PASS=0; FAIL=0; CRIT=0
pass() { echo "  [PASS] $1"; PASS=$((PASS+1)); }
crit() { echo "  [CRIT] $1"; CRIT=$((CRIT+1)); FAIL=$((FAIL+1)); }
warn() { echo "  [WARN] $1"; }

echo "============================================"
echo "  OSRS Detection Vector Test"
echo "============================================"
echo ""

# --- z() EMULATOR ---
echo "=== z() EMULATOR ==="
P=$(/system/bin/getprop ro.build.product)
H=$(/system/bin/getprop ro.hardware)
# getprop always succeeds; echo|grep is safe
if echo "$P" | /system/bin/grep -qi sdk; then crit "PRODUCT=sdk"; else pass "PRODUCT=$P"; fi
if echo "$H" | /system/bin/grep -qi goldfish; then crit "HARDWARE=goldfish"; else pass "HARDWARE=$H"; fi
if echo "$H" | /system/bin/grep -qi ranchu; then crit "HARDWARE=ranchu"; else pass "HARDWARE clean"; fi

# --- A() ROOT ---
echo "=== A() ROOT ==="
T=$(/system/bin/getprop ro.build.tags)
if echo "$T" | /system/bin/grep -qi test-keys; then crit "TAGS=test-keys"; else pass "TAGS=$T"; fi
if [ -f /system/app/Superuser.apk ]; then crit "Superuser.apk"; else pass "Superuser.apk absent"; fi
# Check multiple su locations (not just /system/xbin/su)
# A bind-mounted empty file still shows as -f but has 0 bytes and isn't executable
SU_FOUND=0
for su_path in /system/xbin/su /system/bin/su /sbin/su /su/bin/su /data/local/su /data/local/bin/su /data/local/xbin/su; do
    if [ -f "$su_path" ] && [ -s "$su_path" ]; then
        crit "su found at $su_path"
        SU_FOUND=1
        break
    fi
done
if [ "$SU_FOUND" = "0" ]; then pass "su hidden"; fi

# --- p() PROXIMITY ---
echo "=== p() PROXIMITY ==="
SENSOR_OUT=$(dumpsys sensorservice 2>/dev/null)
if [ -z "$SENSOR_OUT" ]; then
    warn "dumpsys sensorservice unavailable — cannot verify proximity sensor"
    crit "Sensor check unavailable"
elif echo "$SENSOR_OUT" | /system/bin/grep -q "android.sensor.proximity"; then
    pass "Proximity sensor present"
else
    crit "No proximity sensor"
fi

# --- BUILD FINGERPRINT ---
echo "=== BUILD FINGERPRINT ==="
F=$(/system/bin/getprop ro.build.fingerprint)
if echo "$F" | /system/bin/grep -qi generic; then crit "FP generic"; else pass "FP=$F"; fi

# --- JNI BUILD PROPS ---
echo "=== JNI BUILD PROPS ==="
B=$(/system/bin/getprop ro.product.brand)
D=$(/system/bin/getprop ro.product.device)
M=$(/system/bin/getprop ro.product.model)
if echo "$B" | /system/bin/grep -qiE "generic|unknown"; then crit "BRAND"; else pass "BRAND=$B"; fi
if echo "$D" | /system/bin/grep -qiE "generic|emulator|vbox"; then crit "DEVICE"; else pass "DEVICE=$D"; fi
if echo "$M" | /system/bin/grep -qiE "sdk|emulator"; then crit "MODEL"; else pass "MODEL=$M"; fi

# --- SENSOR VENDOR ---
echo "=== SENSOR VENDOR ==="
SENSOR_OUT=$(dumpsys sensorservice 2>/dev/null)
if [ -z "$SENSOR_OUT" ]; then
    warn "dumpsys sensorservice unavailable — cannot verify sensor vendor"
    crit "Sensor vendor check unavailable"
elif echo "$SENSOR_OUT" | /system/bin/grep -qi "bluestacks"; then
    crit "BST vendor"
else
    pass "Vendor clean"
fi

# --- VBOX ARTIFACTS ---
echo "=== VBOX ARTIFACTS ==="
if [ -c /dev/vboxguest ]; then crit "/dev/vboxguest"; else pass "vboxguest removed"; fi
if [ -c /dev/vboxuser ]; then crit "/dev/vboxuser"; else pass "vboxuser removed"; fi
if [ -d /sys/module/vboxguest/parameters ]; then crit "vboxguest sysfs"; else pass "vboxguest sysfs hidden"; fi
if [ -d /proc/bus/pci ]; then
    PCI_ENTRIES=$(ls /proc/bus/pci 2>/dev/null)
    if [ -n "$PCI_ENTRIES" ]; then crit "/proc/bus/pci has entries"; else pass "/proc/bus/pci hidden (empty)"; fi
else
    pass "/proc/bus/pci hidden"
fi

# --- BST ARTIFACTS ---
echo "=== BST ARTIFACTS ==="
if [ -f /data/.bluestacks.prop ]; then crit "bluestacks.prop"; else pass "bluestacks.prop gone"; fi
BSTENV=$(/system/bin/cat /boot/bstsetup.env 2>/dev/null)
if [ -n "$BSTENV" ]; then crit "bstsetup.env readable"; else pass "bstsetup.env hidden"; fi
# Check /mnt/windows broadly: directory existence, any children, or mount point
if [ -d /mnt/windows ]; then
    MNT_ENTRIES=$(ls /mnt/windows 2>/dev/null)
    if [ -n "$MNT_ENTRIES" ]; then
        crit "/mnt/windows has contents: $MNT_ENTRIES"
    else
        pass "/mnt/windows hidden (empty/blocked)"
    fi
else
    pass "/mnt/windows hidden"
fi

# --- /proc SPOOF ---
echo "=== /proc SPOOF ==="
INPUT_DEVS=$(/system/bin/cat /proc/bus/input/devices 2>/dev/null)
if [ -z "$INPUT_DEVS" ]; then
    warn "/proc/bus/input/devices unreadable"
    crit "Input devices check unavailable"
elif echo "$INPUT_DEVS" | /system/bin/grep -qi "vbox"; then
    crit "input devices contain vbox"
else
    pass "Input spoofed"
fi
MODULES=$(/system/bin/cat /proc/modules 2>/dev/null)
if echo "$MODULES" | /system/bin/grep -qi vbox; then crit "modules contain vbox"; else pass "Modules spoofed"; fi

# --- GETPROP ---
echo "=== GETPROP ==="
Q=$(/system/bin/getprop ro.kernel.qemu)
if [ "$Q" = "1" ]; then crit "ro.kernel.qemu=1"; else pass "qemu clean"; fi

# --- ANDROID ID ---
echo "=== ANDROID ID ==="
AID=$(settings get secure android_id 2>/dev/null)
case "$AID" in
    ""|null|error|unknown)
        crit "AID invalid: '$AID'" ;;
    9774d56d682e549c|000000000000000*|DEFACE*)
        crit "Blacklisted AID: $AID" ;;
    *)
        # Verify it's a reasonable hex string (at least 8 chars)
        AID_LEN=$(printf "%s" "$AID" | wc -c)
        if [ "$AID_LEN" -lt 8 ]; then
            crit "AID suspiciously short ($AID_LEN chars): $AID"
        else
            pass "AID=$AID"
        fi
        ;;
esac

# --- GL RENDERER ---
echo "=== GL RENDERER ==="
GL=$(dumpsys SurfaceFlinger 2>/dev/null | /system/bin/grep -i "GLES" | head -1)
if [ -z "$GL" ]; then
    warn "dumpsys SurfaceFlinger returned no GLES info"
    crit "GL renderer check unavailable"
elif echo "$GL" | /system/bin/grep -qiE "swiftshader|android emulator|virtualbox"; then
    crit "GL emulator"
else
    pass "GL clean"
fi

# --- PLAY SERVICES ---
echo "=== PLAY SERVICES ==="
PM_OUT=$(pm list packages 2>/dev/null)
if [ -z "$PM_OUT" ]; then
    warn "pm list packages failed"
    crit "Package manager unavailable"
elif echo "$PM_OUT" | /system/bin/grep -q "com.google.android.gms"; then
    pass "Play Services"
else
    crit "No Play Services (required for certification)"
fi

echo ""
echo "============================================"
echo "  PASS: $PASS | FAIL: $FAIL | CRIT: $CRIT"
echo "============================================"
if [ "$FAIL" -eq 0 ]; then
    echo "  >>> ALL CLEAR <<<"
else
    echo "  >>> FAILURES DETECTED <<<"
fi
echo "============================================"

exit "$FAIL"
