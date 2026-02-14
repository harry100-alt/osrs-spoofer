/*
 * gl_spoof.c - LD_PRELOAD hook for glGetString / glGetStringi
 *
 * Intercepts OpenGL ES string queries to hide emulator GPU identity.
 * When apps call glGetString(GL_VENDOR), glGetString(GL_RENDERER), or
 * glGetString(GL_VERSION), this returns spoofed values matching the
 * target device profile (e.g., Qualcomm Adreno 660 on Samsung S21).
 *
 * Build:
 *   $NDK/toolchains/llvm/prebuilt/$HOST/bin/x86_64-linux-android30-clang
 *       -shared -fPIC -O2 -o gl_spoof.so gl_spoof.c -ldl -llog
 *
 * Deploy:
 *   Push to /data/local/tmp/gl_spoof.so
 *   Set wrapper: setprop wrap.<package> "LD_PRELOAD=/data/local/tmp/gl_spoof.so"
 *
 * Copyright 2026 - BlueStacks Anti-Detection System
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <android/log.h>

#define TAG "GLSpoof"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, TAG, __VA_ARGS__)

/* OpenGL ES constants */
#define GL_VENDOR                         0x1F00
#define GL_RENDERER                       0x1F01
#define GL_VERSION                        0x1F02
#define GL_EXTENSIONS                     0x1F03
#define GL_SHADING_LANGUAGE_VERSION       0x8B8C

/* ============================================================
 * Spoofed values — match the device profile from spoof.sh
 * These should match a real device (Samsung Galaxy S21 / Adreno 660)
 * ============================================================ */
static const char *SPOOF_VENDOR   = "Qualcomm";
static const char *SPOOF_RENDERER = "Adreno (TM) 660";
static const char *SPOOF_VERSION  = "OpenGL ES 3.2 V@0615.73 (GIT@d93af58fcd, Ie67da92a76, 1683932973) (Date:05/12/23)";
static const char *SPOOF_GLSL_VERSION = "OpenGL ES GLSL ES 3.20";

/* ============================================================
 * Config file support — override spoofed values at runtime
 * Reads from /data/local/tmp/gl_spoof.conf if present
 * Format: key=value (one per line)
 *   gl_vendor=Qualcomm
 *   gl_renderer=Adreno (TM) 660
 *   gl_version=OpenGL ES 3.2 V@...
 *   gl_glsl_version=OpenGL ES GLSL ES 3.20
 * ============================================================ */
#define CONFIG_PATH "/data/local/tmp/gl_spoof.conf"
#define MAX_LINE 512

static char cfg_vendor[MAX_LINE]   = {0};
static char cfg_renderer[MAX_LINE] = {0};
static char cfg_version[MAX_LINE]  = {0};
static char cfg_glsl[MAX_LINE]     = {0};
static int  config_loaded = 0;

static void load_config(void) {
    if (config_loaded) return;
    config_loaded = 1;

    FILE *f = fopen(CONFIG_PATH, "r");
    if (!f) {
        LOGI("No config file at %s, using defaults", CONFIG_PATH);
        return;
    }

    char line[MAX_LINE];
    while (fgets(line, sizeof(line), f)) {
        /* Strip newline */
        char *nl = strchr(line, '\n');
        if (nl) *nl = '\0';
        nl = strchr(line, '\r');
        if (nl) *nl = '\0';

        /* Skip comments and empty lines */
        if (line[0] == '#' || line[0] == '\0') continue;

        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        char *key = line;
        char *val = eq + 1;

        if (strcmp(key, "gl_vendor") == 0) {
            strncpy(cfg_vendor, val, MAX_LINE - 1);
            LOGI("Config: vendor = %s", cfg_vendor);
        } else if (strcmp(key, "gl_renderer") == 0) {
            strncpy(cfg_renderer, val, MAX_LINE - 1);
            LOGI("Config: renderer = %s", cfg_renderer);
        } else if (strcmp(key, "gl_version") == 0) {
            strncpy(cfg_version, val, MAX_LINE - 1);
            LOGI("Config: version = %s", cfg_version);
        } else if (strcmp(key, "gl_glsl_version") == 0) {
            strncpy(cfg_glsl, val, MAX_LINE - 1);
            LOGI("Config: glsl = %s", cfg_glsl);
        }
    }
    fclose(f);
}

static const char *get_vendor(void) {
    return cfg_vendor[0] ? cfg_vendor : SPOOF_VENDOR;
}
static const char *get_renderer(void) {
    return cfg_renderer[0] ? cfg_renderer : SPOOF_RENDERER;
}
static const char *get_version(void) {
    return cfg_version[0] ? cfg_version : SPOOF_VERSION;
}
static const char *get_glsl_version(void) {
    return cfg_glsl[0] ? cfg_glsl : SPOOF_GLSL_VERSION;
}

/* ============================================================
 * glGetString hook
 * ============================================================ */
typedef const unsigned char* (*glGetString_t)(unsigned int name);
static glGetString_t real_glGetString = NULL;

const unsigned char* glGetString(unsigned int name) {
    if (!real_glGetString) {
        real_glGetString = (glGetString_t)dlsym(RTLD_NEXT, "glGetString");
        if (!real_glGetString) {
            LOGW("Failed to find real glGetString!");
            return NULL;
        }
    }

    load_config();

    switch (name) {
        case GL_VENDOR:
            LOGI("glGetString(GL_VENDOR) -> spoofed: %s", get_vendor());
            return (const unsigned char*)get_vendor();

        case GL_RENDERER:
            LOGI("glGetString(GL_RENDERER) -> spoofed: %s", get_renderer());
            return (const unsigned char*)get_renderer();

        case GL_VERSION:
            LOGI("glGetString(GL_VERSION) -> spoofed: %s", get_version());
            return (const unsigned char*)get_version();

        case GL_SHADING_LANGUAGE_VERSION:
            LOGI("glGetString(GL_SHADING_LANGUAGE_VERSION) -> spoofed: %s", get_glsl_version());
            return (const unsigned char*)get_glsl_version();

        default:
            /* GL_EXTENSIONS and anything else — pass through */
            return real_glGetString(name);
    }
}

/* ============================================================
 * glGetStringi hook (indexed string queries, OpenGL ES 3.0+)
 *
 * Per the GL spec, glGetStringi is only valid for GL_EXTENSIONS
 * (returns extension name at given index). GL_VENDOR, GL_RENDERER,
 * GL_VERSION are NOT valid name arguments for glGetStringi — those
 * are only for glGetString (non-indexed). We hook this primarily
 * to ensure the function symbol is intercepted so no implementation
 * can bypass our glGetString hook, and pass everything through.
 * ============================================================ */
typedef const unsigned char* (*glGetStringi_t)(unsigned int name, unsigned int index);
static glGetStringi_t real_glGetStringi = NULL;

const unsigned char* glGetStringi(unsigned int name, unsigned int index) {
    if (!real_glGetStringi) {
        real_glGetStringi = (glGetStringi_t)dlsym(RTLD_NEXT, "glGetStringi");
        if (!real_glGetStringi) {
            LOGW("Failed to find real glGetStringi!");
            return NULL;
        }
    }

    /* Pass through — glGetStringi is only spec-valid for GL_EXTENSIONS.
     * Returning spoofed values for other enums violates the spec and
     * could trigger sanity check failures in apps. */
    return real_glGetStringi(name, index);
}

/* ============================================================
 * EGL hooks — eglQueryString can also leak GPU info
 * ============================================================ */
#define EGL_VENDOR      0x3053
#define EGL_VERSION     0x3054
#define EGL_EXTENSIONS  0x3055
#define EGL_CLIENT_APIS 0x308D

typedef const char* (*eglQueryString_t)(void *dpy, int name);
static eglQueryString_t real_eglQueryString = NULL;

const char* eglQueryString(void *dpy, int name) {
    if (!real_eglQueryString) {
        real_eglQueryString = (eglQueryString_t)dlsym(RTLD_NEXT, "eglQueryString");
        if (!real_eglQueryString) {
            LOGW("Failed to find real eglQueryString!");
            return NULL;
        }
    }

    load_config();

    switch (name) {
        case EGL_VENDOR:
            LOGI("eglQueryString(EGL_VENDOR) -> spoofed: %s", get_vendor());
            return get_vendor();

        case EGL_VERSION: {
            /* Pass through but log for debugging */
            const char *real = real_eglQueryString(dpy, name);
            LOGI("eglQueryString(EGL_VERSION) -> passthrough: %s", real ? real : "null");
            return real;
        }

        default:
            return real_eglQueryString(dpy, name);
    }
}

/* ============================================================
 * Constructor — runs when library is loaded
 * ============================================================ */
__attribute__((constructor))
static void gl_spoof_init(void) {
    LOGI("GL Spoof library loaded (LD_PRELOAD)");
    LOGI("Target: %s / %s", SPOOF_VENDOR, SPOOF_RENDERER);
    load_config();
}
