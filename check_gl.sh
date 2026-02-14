#!/system/bin/sh
# GL renderer diagnostics — uses resetprop if available, falls back to getprop

# Choose property reader: resetprop (can read deleted props) > getprop
if [ -x /system/xbin/resetprop ]; then
    PROP="/system/xbin/resetprop"
elif [ -x /system/bin/getprop ]; then
    PROP="/system/bin/getprop"
else
    PROP="getprop"
fi

echo "=== GL RENDERER CHECK ==="
echo "(using $PROP)"
echo ""
echo "--- SurfaceFlinger GLES ---"
dumpsys SurfaceFlinger 2>/dev/null | /system/bin/grep -i "GLES"
echo ""
echo "--- ro.hardware.egl ---"
$PROP ro.hardware.egl 2>/dev/null
echo ""
echo "--- EGL implementation ---"
dumpsys SurfaceFlinger 2>/dev/null | /system/bin/grep -iE "vendor|renderer|version" | head -10
echo ""
echo "--- GPU Info from dumpsys ---"
dumpsys gpu 2>/dev/null | head -20
echo ""
echo "--- /proc/driver/gpu ---"
/system/bin/cat /proc/driver/gpu 2>/dev/null || echo "(not present)"
echo ""
echo "--- EGL libs ---"
ls /system/lib64/egl/ 2>/dev/null
echo ""
echo "=== END ==="
