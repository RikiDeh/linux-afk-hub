#define _DEFAULT_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <linux/input-event-codes.h>

static void sleep_ms(long long ms) {
    if (ms <= 0) return;
    struct timespec ts;
    ts.tv_sec = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000L;
    nanosleep(&ts, NULL);
}

// Terjemahkan Linux evdev keycode ke X11 keycode (+8 offset XKB)
static int evdev_to_x11_key(int code) {
    return code + 8;
}

// Terjemahkan Linux evdev mouse button ke X11 button index
static int evdev_to_x11_button(int code) {
    switch (code) {
        case BTN_LEFT:   return 1;
        case BTN_MIDDLE: return 2;
        case BTN_RIGHT:  return 3;
        case BTN_SIDE:   return 8;
        case BTN_EXTRA:  return 9;
        default: return 0;
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <macro_file> [speed_multiplier]\n", argv[0]);
        return 1;
    }
    double speed = (argc > 2) ? atof(argv[2]) : 1.0;
    if (speed <= 0.0) speed = 1.0;

    FILE *f = fopen(argv[1], "r");
    if (!f) {
        perror("Gagal membuka file makro");
        return 1;
    }

    Display *dpy = XOpenDisplay(NULL);
    if (!dpy) {
        fprintf(stderr, "Gagal konek ke display: %s\n", getenv("DISPLAY"));
        fclose(f);
        return 1;
    }

    char line[256];
    long long last_ms = 0;

    while (fgets(line, sizeof(line), f)) {
        char type[32];
        if (sscanf(line, "%s", type) != 1) continue;

        if (strcmp(type, "EV_KEY") == 0) {
            int code, value;
            long long ms;
            if (sscanf(line, "%*s %d %d %lld", &code, &value, &ms) == 3) {
                long long delta = (long long)((ms - last_ms) / speed);
                if (delta > 0) sleep_ms(delta);
                last_ms = ms;

                if (code >= BTN_MISC && code <= BTN_TASK) {
                    // Event Mouse Button
                    int xbtn = evdev_to_x11_button(code);
                    if (xbtn > 0) {
                        XTestFakeButtonEvent(dpy, xbtn, (value == 1) ? True : False, CurrentTime);
                        XFlush(dpy);
                    }
                } else {
                    // Event Keyboard Key
                    int xkey = evdev_to_x11_key(code);
                    if (xkey > 0 && xkey < 256) {
                        XTestFakeKeyEvent(dpy, xkey, (value == 1) ? True : False, CurrentTime);
                        XFlush(dpy);
                    }
                }
            }
        } else if (strcmp(type, "EV_REL") == 0) {
            int code, value;
            long long ms;
            if (sscanf(line, "%*s %d %d %lld", &code, &value, &ms) == 3) {
                long long delta = (long long)((ms - last_ms) / speed);
                if (delta > 0) sleep_ms(delta);
                last_ms = ms;

                if (code == REL_X) {
                    XTestFakeRelativeMotionEvent(dpy, value, 0, CurrentTime);
                    XFlush(dpy);
                } else if (code == REL_Y) {
                    XTestFakeRelativeMotionEvent(dpy, 0, value, CurrentTime);
                    XFlush(dpy);
                } else if (code == REL_WHEEL) {
                    int btn = (value > 0) ? 4 : 5; // Scroll Wheel Up / Down
                    XTestFakeButtonEvent(dpy, btn, True, CurrentTime);
                    XTestFakeButtonEvent(dpy, btn, False, CurrentTime);
                    XFlush(dpy);
                }
            }
        }
    }

    XCloseDisplay(dpy);
    fclose(f);
    return 0;
}
