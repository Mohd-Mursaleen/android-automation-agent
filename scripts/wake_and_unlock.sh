#!/bin/bash
# Smart Screen Wake — only does what's necessary, preserves current app state.
# Safe to run repeatedly — idempotent on an already-awake-unlocked screen.

# --- Step 1: Check if screen is ON ---
WAKEFULNESS=$(adb shell dumpsys power 2>/dev/null | grep "mWakefulness=" | head -1 | cut -d= -f2 | tr -d '[:space:]')

if [ "$WAKEFULNESS" != "Awake" ]; then
    echo "Screen is off ($WAKEFULNESS). Waking up..."
    adb shell input keyevent KEYCODE_WAKEUP
    sleep 1.5
else
    echo "Screen is already awake."
fi

# --- Step 2: Check if device is locked ---
# Method 1: trust service (most reliable)
DEVICE_LOCKED=$(adb shell dumpsys trust 2>/dev/null | grep "deviceLocked=" | head -1 | grep -o "true\|false")

# Method 2: fallback — check window focus for lock screen indicators
if [ -z "$DEVICE_LOCKED" ]; then
    LOCK_FOCUS=$(adb shell dumpsys window 2>/dev/null | grep "mCurrentFocus" | head -1)
    if echo "$LOCK_FOCUS" | grep -qi "StatusBar\|Keyguard\|Bouncer\|LockScreen"; then
        DEVICE_LOCKED="true"
    else
        DEVICE_LOCKED="false"
    fi
fi

if [ "$DEVICE_LOCKED" = "true" ]; then
    echo "Device is locked. Swiping to unlock..."
    # Get screen dimensions for a proper swipe
    SCREEN_SIZE=$(adb shell wm size 2>/dev/null | awk '{print $3}' | tr 'x' ' ')
    SW=$(echo $SCREEN_SIZE | awk '{print $1}')
    SH=$(echo $SCREEN_SIZE | awk '{print $2}')

    # Default to common resolution if wm size fails
    SW=${SW:-1080}
    SH=${SH:-2340}

    MID_X=$((SW / 2))
    START_Y=$((SH * 8 / 10))
    END_Y=$((SH * 2 / 10))

    adb shell input swipe $MID_X $START_Y $MID_X $END_Y 500
    sleep 1.0

    # Check if still locked (might have notification shade instead of lock)
    STILL_LOCKED=$(adb shell dumpsys trust 2>/dev/null | grep "deviceLocked=" | head -1 | grep -o "true\|false")
    if [ "$STILL_LOCKED" = "true" ]; then
        echo "Still locked after swipe. Trying again..."
        adb shell input swipe $MID_X $START_Y $MID_X $END_Y 500
        sleep 1.0
    fi

    echo "Unlock complete."
else
    echo "Device is already unlocked."
fi

# --- NO Home button press. EVER. ---
# The current app stays in foreground. If the automation goal needs
# to start from home screen, the Planner will add that as a subgoal.

echo "Ready. Screen is awake and unlocked."
