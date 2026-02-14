#!/system/bin/sh
# Install KitsuneMask (Magisk) to /system on BlueStacks
# Must run as root

echo "=== KitsuneMask System Install ==="
FAIL=0

# Detect /system block device dynamically (don't assume /dev/sda1)
SYSTEM_DEV=$(mount 2>/dev/null | /system/bin/grep " /system " | /system/bin/awk '{print $1}' | head -1)
if [ -z "$SYSTEM_DEV" ]; then
    SYSTEM_DEV="/dev/sda1"
    echo "[WARN] Could not detect /system device, using fallback: $SYSTEM_DEV"
fi

# Helper to copy with error checking
safe_cp() {
    local src="$1" dst="$2"
    if [ ! -f "$src" ]; then
        echo "  [ERR] Source not found: $src"
        FAIL=$((FAIL + 1))
        return 1
    fi
    if cp "$src" "$dst" 2>/dev/null; then
        echo "  [OK] $(basename "$dst")"
    else
        echo "  [ERR] Failed to copy: $src -> $dst"
        FAIL=$((FAIL + 1))
        return 1
    fi
}

# Create magisk directories
mkdir -p /data/adb/magisk
mkdir -p /data/adb/modules
mkdir -p /data/adb/post-fs-data.d
mkdir -p /data/adb/service.d

# Remount system RW
echo ""
echo "Remounting /system read-write..."
if ! /system/bin/mount -o remount,rw $SYSTEM_DEV /system 2>/dev/null; then
    echo "[ERR] Failed to remount /system RW. Is this running as root?"
    exit 1
fi

# Install magisk binaries to system
echo ""
echo "Installing to /system/xbin/..."
safe_cp /data/local/tmp/magisk64 /system/xbin/magisk64
safe_cp /data/local/tmp/magisk32 /system/xbin/magisk32
safe_cp /data/local/tmp/busybox /system/xbin/busybox_magisk
safe_cp /data/local/tmp/magiskinit /system/xbin/magiskinit
safe_cp /data/local/tmp/magiskpolicy /system/xbin/magiskpolicy

# Create magisk symlinks
echo ""
echo "Creating symlinks..."
for link_pair in "magisk64:magisk" "magisk64:resetprop" "magisk64:su_magisk"; do
    target="/system/xbin/${link_pair%%:*}"
    link="/system/xbin/${link_pair#*:}"
    if ln -sf "$target" "$link" 2>/dev/null; then
        echo "  [OK] $link -> $target"
    else
        echo "  [ERR] Failed to create symlink: $link -> $target"
        FAIL=$((FAIL + 1))
    fi
done

# Set permissions
echo ""
echo "Setting permissions..."
for bin in magisk64 magisk32 busybox_magisk magiskinit magiskpolicy magisk resetprop; do
    if [ -e "/system/xbin/$bin" ]; then
        if chmod 755 "/system/xbin/$bin" 2>/dev/null; then
            : # OK
        else
            echo "  [ERR] Failed to chmod 755 /system/xbin/$bin"
            FAIL=$((FAIL + 1))
        fi
    fi
done

# Also install to /data/adb/magisk for standard location
echo ""
echo "Installing to /data/adb/magisk/..."
safe_cp /data/local/tmp/magisk64 /data/adb/magisk/magisk64
safe_cp /data/local/tmp/magisk32 /data/adb/magisk/magisk32
safe_cp /data/local/tmp/busybox /data/adb/magisk/busybox
safe_cp /data/local/tmp/magiskinit /data/adb/magisk/magiskinit
safe_cp /data/local/tmp/magiskpolicy /data/adb/magisk/magiskpolicy
safe_cp /data/local/tmp/util_functions.sh /data/adb/magisk/util_functions.sh
safe_cp /data/local/tmp/main.jar /data/adb/magisk/main.jar
safe_cp /data/local/tmp/stub.apk /data/adb/magisk/stub.apk
chmod -R 755 /data/adb/magisk/ 2>/dev/null

# Remount system RO
/system/bin/mount -o remount,ro $SYSTEM_DEV /system 2>/dev/null

# Test
echo ""
echo "Testing resetprop..."
/system/xbin/resetprop --version 2>&1
echo ""

echo "Testing resetprop write..."
/system/xbin/resetprop ro.test.magisk "installed" 2>/dev/null
RESULT=$(/system/xbin/resetprop ro.test.magisk 2>/dev/null)
echo "ro.test.magisk = $RESULT"
/system/xbin/resetprop --delete ro.test.magisk 2>/dev/null

if [ "$RESULT" = "installed" ]; then
    echo ""
    if [ "$FAIL" -gt 0 ]; then
        echo "=== MAGISK INSTALL COMPLETED WITH $FAIL ERROR(S) ==="
        echo "resetprop works but some files failed to copy — check output above"
    else
        echo "=== MAGISK INSTALL SUCCESS ==="
        echo "resetprop is working!"
    fi
else
    echo ""
    echo "=== INSTALL FAILED ==="
    echo "resetprop is NOT working."
    # Try running as magisk daemon
    /system/xbin/magisk64 --version 2>&1
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== DONE ==="
exit "$FAIL"
