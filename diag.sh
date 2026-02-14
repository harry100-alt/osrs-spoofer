#!/system/bin/sh
echo "=== PLAY PROTECT DIAGNOSTIC ==="
echo ""

echo "--- Secure Android ID ---"
settings get secure android_id 2>/dev/null

echo ""
echo "--- GSF Database Android ID ---"
if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 /data/data/com.google.android.gsf/databases/gservices.db "SELECT value FROM main WHERE name='android_id'" 2>/dev/null
    echo "(above is the GSF ID used for device registration)"
else
    echo "[WARN] sqlite3 not found — cannot read GSF database"
fi

echo ""
echo "--- Build Fingerprint ---"
/system/bin/getprop ro.build.fingerprint

echo ""
echo "--- Build Description ---"
/system/bin/getprop ro.build.description

echo ""
echo "--- CTS-critical properties ---"
echo "security_patch=$(/system/bin/getprop ro.build.version.security_patch)"
echo "build.type=$(/system/bin/getprop ro.build.type)"
echo "build.tags=$(/system/bin/getprop ro.build.tags)"
echo "first_api_level=$(/system/bin/getprop ro.product.first_api_level)"
echo "version.release=$(/system/bin/getprop ro.build.version.release)"
echo "version.sdk=$(/system/bin/getprop ro.build.version.sdk)"
echo "build.flavor=$(/system/bin/getprop ro.build.flavor)"

echo ""
echo "--- Device identity ---"
echo "brand=$(/system/bin/getprop ro.product.brand)"
echo "device=$(/system/bin/getprop ro.product.device)"
echo "model=$(/system/bin/getprop ro.product.model)"
echo "name=$(/system/bin/getprop ro.product.name)"
echo "manufacturer=$(/system/bin/getprop ro.product.manufacturer)"
echo "board=$(/system/bin/getprop ro.product.board)"
echo "platform=$(/system/bin/getprop ro.board.platform)"
echo "hardware=$(/system/bin/getprop ro.hardware)"

echo ""
echo "--- Google Play Services ---"
dumpsys package com.google.android.gms 2>/dev/null | /system/bin/grep versionName | head -1

echo ""
echo "--- Play Store ---"
dumpsys package com.android.vending 2>/dev/null | /system/bin/grep versionName | head -1

echo ""
echo "--- SELinux ---"
getenforce 2>/dev/null

echo ""
echo "--- Verified boot state ---"
echo "verifiedbootstate=$(/system/bin/getprop ro.boot.verifiedbootstate)"
echo "flash.locked=$(/system/bin/getprop ro.boot.flash.locked)"
echo "vbmeta.device_state=$(/system/bin/getprop ro.boot.vbmeta.device_state)"

echo ""
echo "--- Full ro.build.* dump ---"
/system/bin/getprop | /system/bin/grep "ro.build\."

echo ""
echo "--- Full ro.product.* dump ---"
/system/bin/getprop | /system/bin/grep "ro.product\."

echo ""
echo "=== END ==="
