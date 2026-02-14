#!/bin/bash
# Build gl_spoof.so for x86_64 Android (BlueStacks)
#
# Requires: Android NDK r27c+ installed
# Usage: ./build.sh [/path/to/ndk]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NDK_DIR="${1:-$SCRIPT_DIR/../../ndk-temp/android-ndk-r27c}"

# Find the clang compiler
TOOLCHAIN="$NDK_DIR/toolchains/llvm/prebuilt"
if [ -d "$TOOLCHAIN/windows-x86_64" ]; then
    TOOLCHAIN="$TOOLCHAIN/windows-x86_64"
elif [ -d "$TOOLCHAIN/linux-x86_64" ]; then
    TOOLCHAIN="$TOOLCHAIN/linux-x86_64"
elif [ -d "$TOOLCHAIN/darwin-x86_64" ]; then
    TOOLCHAIN="$TOOLCHAIN/darwin-x86_64"
else
    echo "ERROR: Cannot find NDK toolchain at $TOOLCHAIN"
    echo "Available: $(ls "$TOOLCHAIN" 2>/dev/null || echo 'none')"
    exit 1
fi

# Target: x86_64 Android API 30 (Android 11 - BlueStacks runs this)
CC="$TOOLCHAIN/bin/x86_64-linux-android30-clang"
if [ ! -f "$CC" ] && [ ! -f "${CC}.cmd" ] && [ ! -f "${CC}.exe" ]; then
    echo "ERROR: Compiler not found at $CC"
    exit 1
fi

# Handle Windows .cmd/.exe wrapper
if [ -f "${CC}.cmd" ]; then
    CC="${CC}.cmd"
elif [ -f "${CC}.exe" ]; then
    CC="${CC}.exe"
fi

echo "Using compiler: $CC"
echo "Building gl_spoof.so for x86_64 Android..."

"$CC" \
    -shared \
    -fPIC \
    -O2 \
    -Wall \
    -Wno-unused-function \
    -DANDROID \
    -o "$SCRIPT_DIR/gl_spoof.so" \
    "$SCRIPT_DIR/gl_spoof.c" \
    -ldl \
    -llog

echo "Built: $SCRIPT_DIR/gl_spoof.so"
file "$SCRIPT_DIR/gl_spoof.so" 2>/dev/null || true
echo ""

# Also build 32-bit version for /system/lib/ if needed
CC32="$TOOLCHAIN/bin/i686-linux-android30-clang"
if [ -f "$CC32" ] || [ -f "${CC32}.cmd" ] || [ -f "${CC32}.exe" ]; then
    if [ -f "${CC32}.cmd" ]; then
        CC32="${CC32}.cmd"
    elif [ -f "${CC32}.exe" ]; then
        CC32="${CC32}.exe"
    fi
    echo "Building gl_spoof32.so for x86 Android..."
    "$CC32" \
        -shared \
        -fPIC \
        -O2 \
        -Wall \
        -Wno-unused-function \
        -DANDROID \
        -o "$SCRIPT_DIR/gl_spoof32.so" \
        "$SCRIPT_DIR/gl_spoof.c" \
        -ldl \
        -llog
    echo "Built: $SCRIPT_DIR/gl_spoof32.so"
else
    echo "Skipping 32-bit build (compiler not found)"
fi

echo ""
echo "=== BUILD COMPLETE ==="
echo "Deploy with: adb push gl_spoof.so /data/local/tmp/"
echo "Then use: setprop wrap.com.jagex.oldschool.android 'LD_PRELOAD=/data/local/tmp/gl_spoof.so'"
