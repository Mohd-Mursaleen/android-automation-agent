#!/bin/bash

# Screen Wake + Swipe Up Unlock Script
# For Android devices via ADB

echo "=== Screen Wake + Unlock Script ==="
echo ""

# Check if ADB is available
if ! command -v adb &> /dev/null; then
    echo "❌ ADB not found. Make sure ADB is installed."
    exit 1
fi

# Check device connection
echo "Checking device connection..."
DEVICES=$(adb devices | grep -v "List of devices" | grep -v "^$" | wc -l)

if [ "$DEVICES" -eq 0 ]; then
    echo "❌ No devices connected. Connect your Android device via USB or WiFi."
    echo "For WiFi connection: adb connect <device_ip>:5555"
    exit 1
fi

echo "✅ Device connected"

# Step 1: Wake screen (ensure it is ON, never toggle it OFF)
echo "1. Ensuring screen is ON..."
# keyevent 224 (WAKEUP) turns the screen ON and does nothing if it's already ON.
# This prevents the toggle-off issue with keyevent 26.
adb shell input keyevent 224
sleep 1.0

# Step 2: Verify screen state
echo "2. Verifying screen state..."
SCREEN_STATE=$(adb shell dumpsys power | grep "mWakefulness=" | cut -d= -f2)

if [ "$SCREEN_STATE" = "Asleep" ] || [ "$SCREEN_STATE" = "Dozing" ]; then
    echo "   ⚠️ Screen still report as $SCREEN_STATE. Trying backup wake..."
    adb shell input keyevent 26
    sleep 1.0
else
    echo "   ✅ Screen is awake ($SCREEN_STATE)."
fi

# Step 3: Check and Force Unlock
echo "3. Unlocking..."
# Get screen dimensions for swipe
SCREEN_SIZE=$(adb shell wm size | awk '{print $3}' | tr 'x' ' ')
SCREEN_WIDTH=$(echo $SCREEN_SIZE | awk '{print $1}')
SCREEN_HEIGHT=$(echo $SCREEN_SIZE | awk '{print $2}')

START_X=$((SCREEN_WIDTH / 2))
START_Y=$((SCREEN_HEIGHT * 8 / 10))
END_X=$START_X
END_Y=$((SCREEN_HEIGHT * 2 / 10))

# Perform the swipe to unlock/clear shades
echo "   Performing unlock swipe..."
adb shell input swipe $START_X $START_Y $END_X $END_Y 500
sleep 1.0

# Optional: Extra swipe in case of stubborn notification shades
IS_SHADE=$(adb shell dumpsys window | grep "mCurrentFocus" | grep "NotificationShade")
if [ -n "$IS_SHADE" ]; then
    echo "   ⚠️ Notification shade detected. Attempting to clear..."
    adb shell input swipe $START_X $START_Y $END_X $END_Y 500
    sleep 0.5
fi


# Step 4: Optional - Press back in case of any popups
echo "4. Clearing any popups (Back button)..."
adb shell input keyevent 4  # BACK button
sleep 0.3

# Step 5: Verify we're on home screen or unlocked
echo "5. Verifying unlock..."
CURRENT_APP=$(adb shell dumpsys window | grep "mCurrentFocus" | head -1)

if echo "$CURRENT_APP" | grep -q "StatusBar\|Keyguard\|LockScreen"; then
    echo "   ⚠️ Still on lock screen. Trying alternative unlock..."
    # Alternative: Swipe from different position
    adb shell input swipe $((SCREEN_WIDTH / 3)) $START_Y $((SCREEN_WIDTH / 3)) $END_Y 500
    sleep 0.5
fi

echo ""
echo "✅ Screen wake + unlock completed!"
echo "Current app: $CURRENT_APP"

# Optional: Go to home screen to ensure clean state
echo ""
echo "Optional: Pressing Home button for clean state..."
adb shell input keyevent 3  # HOME button
sleep 0.5

FINAL_APP=$(adb shell dumpsys window | grep "mCurrentFocus" | head -1)
echo "Final state: $FINAL_APP"

echo ""
echo "=== Script Complete ==="