#!/system/bin/sh
# Post-registration cleanup: clear GMS + Play Store data (NOT GSF), then reboot
echo "=== POST-REGISTRATION CLEANUP ==="
echo ""

# Confirm GSF ID is still the one we registered
GSFDB="/data/data/com.google.android.gsf/databases/gservices.db"
HEX=""
# Check sqlite3 is available (check PATH and common manual-push location)
SQLITE3=""
if command -v sqlite3 >/dev/null 2>&1; then
    SQLITE3="sqlite3"
elif [ -x "/data/local/tmp/sqlite3" ]; then
    SQLITE3="/data/local/tmp/sqlite3"
fi

if [ -z "$SQLITE3" ]; then
    echo "[WARN] sqlite3 not available — cannot verify GSF ID"
elif [ ! -f "$GSFDB" ]; then
    echo "[WARN] GSF database not found — cannot verify GSF ID"
else
    DECIMAL=$("$SQLITE3" "$GSFDB" "SELECT value FROM main WHERE name='android_id'" 2>/dev/null)
    # Validate DECIMAL is a non-empty numeric value
    case "$DECIMAL" in
        ''|*[!0-9]*)
            echo "[WARN] GSF ID query returned invalid value: '$DECIMAL'"
            ;;
        *)
            HEX=$(printf "%x" "$DECIMAL")
            echo "Registered GSF ID: $HEX"
            ;;
    esac
fi
echo "(This ID is preserved — NOT clearing GSF data)"
echo ""

FAIL=0

echo "[1/2] Clearing Google Play Services data..."
if pm clear com.google.android.gms >/dev/null 2>&1; then
    echo "  Done"
else
    echo "  [WARN] pm clear com.google.android.gms failed (package missing or permission denied)"
    FAIL=$((FAIL + 1))
fi

echo "[2/2] Clearing Google Play Store data..."
if pm clear com.android.vending >/dev/null 2>&1; then
    echo "  Done"
else
    echo "  [WARN] pm clear com.android.vending failed (package missing or permission denied)"
    FAIL=$((FAIL + 1))
fi

echo ""
if [ "$FAIL" -gt 0 ]; then
    echo "=== CLEANUP COMPLETED WITH $FAIL WARNING(S) ==="
else
    echo "=== CLEANUP COMPLETE ==="
fi
echo ""
echo "Now reboot the device and wait 15-30 minutes."
echo "Play Protect should show as registered after reboot."
if [ -n "$HEX" ]; then
    echo ""
    echo "GSF ID $HEX has been preserved."
    echo "Google will match this ID against your registration."
fi

exit "$FAIL"
