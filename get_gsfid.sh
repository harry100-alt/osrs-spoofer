#!/system/bin/sh
echo "=== GSF ID FOR PLAY PROTECT REGISTRATION ==="
echo ""

# Check sqlite3 is available (check PATH and common manual-push location)
SQLITE3=""
if command -v sqlite3 >/dev/null 2>&1; then
    SQLITE3="sqlite3"
elif [ -x "/data/local/tmp/sqlite3" ]; then
    SQLITE3="/data/local/tmp/sqlite3"
else
    echo "[ERR] sqlite3 not found on this device."
    echo "      sqlite3 is required to read the GSF database."
    echo "      Push it manually:"
    echo "        adb push sqlite3 /data/local/tmp/"
    echo "        adb shell chmod 755 /data/local/tmp/sqlite3"
    exit 1
fi

# Get GSF ID from database
GSFDB="/data/data/com.google.android.gsf/databases/gservices.db"
if [ -f "$GSFDB" ]; then
    DECIMAL=$("$SQLITE3" "$GSFDB" "SELECT value FROM main WHERE name='android_id'" 2>/dev/null)
    case "$DECIMAL" in
        ''|*[!0-9]*)
            echo "[ERR] GSF ID query returned invalid value: '$DECIMAL'"
            echo "Try: sqlite3 $GSFDB '.tables'"
            "$SQLITE3" "$GSFDB" ".tables" 2>/dev/null
            echo ""
            echo "=== END ==="
            exit 1
            ;;
    esac
    HEX=$(printf "%x" "$DECIMAL")
    echo "GSF ID (decimal): $DECIMAL"
    echo "GSF ID (hex):     $HEX"
    echo ""
    echo ">>> Register this HEX value at: <<<"
    echo "    https://www.google.com/android/uncertified"
    echo ""
    echo "After registering:"
    echo "  1. Clear Google Play Services data:"
    echo "     Settings > Apps > Google Play Services > Storage > Clear All Data"
    echo "  2. Clear Google Play Store data:"
    echo "     Settings > Apps > Google Play Store > Storage > Clear All Data"
    echo "  3. Reboot the device"
    echo "  4. Wait 15-30 minutes"
else
    echo "[ERR] GSF database not found at $GSFDB"
    echo "Is Google Services Framework installed?"
    pm list packages 2>/dev/null | /system/bin/grep gsf
    echo ""
    echo "=== END ==="
    exit 1
fi
echo ""
echo "=== END ==="
