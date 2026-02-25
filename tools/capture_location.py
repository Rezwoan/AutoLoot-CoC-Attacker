"""
Requirements (install these first):

    pip install pynput

Usage:

1. Run this script (inside your venv if you made one).
2. Move your mouse and LEFT-CLICK anywhere you want to capture.
3. After each click, look at the console:
   - Type a variable name (e.g. "login_button") and press Enter to save.
   - Just press Enter with no text to skip that point.
   - Type 'q' and press Enter to quit.
4. You can also press ESC at any time to stop capturing.
5. When you stop, the script prints all variables like:
       LOGIN_BUTTON = (123, 456)
"""

from pynput import mouse, keyboard
from queue import Queue
import threading
import re
import time

# Queue for click positions (x, y)
click_queue = Queue()

# List of (var_name, (x, y))
saved_points = []

# Shared flag to signal stopping
stop_flag = False


def normalize_var_name(raw: str) -> str:
    """
    Turn user input into a valid Python variable name in UPPER_SNAKE_CASE.
    Example:
        "login button"  -> "LOGIN_BUTTON"
        "1field"        -> "_1FIELD"
    """
    raw = raw.strip()
    if not raw:
        return ""

    # Uppercase and replace spaces with underscore
    name = raw.upper().replace(" ", "_")

    # Replace any non-alphanumeric/underscore with underscore
    name = re.sub(r"\W+", "_", name)

    # Ensure it doesn't start with a digit
    if name and name[0].isdigit():
        name = "_" + name

    # Avoid empty / all underscores
    name = name.strip("_") or "VAR"

    return name


def on_click(x, y, button, pressed):
    """
    Mouse callback: when left button is pressed, enqueue its position.
    """
    if pressed and button == mouse.Button.left:
        click_queue.put((x, y))


def on_key_press(key):
    """
    Keyboard callback: press ESC to stop.
    """
    global stop_flag
    try:
        if key == keyboard.Key.esc:
            print("\n[INFO] ESC pressed. Stopping capture...")
            stop_flag = True
            # Returning False stops the keyboard listener
            return False
    except:
        pass


def main():
    global stop_flag

    print("=== Mouse Position Capture ===")
    print("Instructions:")
    print("  - Left-click anywhere to capture a point.")
    print("  - After each click, you'll be asked for a variable name.")
    print("  - Just press Enter with no name to skip that point.")
    print("  - Type 'q' as the name to quit.")
    print("  - You can also press ESC at any time to stop capturing.")
    print("================================\n")

    # Start mouse listener
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    # Start keyboard listener
    keyboard_listener = keyboard.Listener(on_press=on_key_press)
    keyboard_listener.start()

    try:
        while not stop_flag:
            # Check if we have a new click to process
            if not click_queue.empty():
                x, y = click_queue.get()

                print(f"\nCaptured position: ({x}, {y})")
                name = input(
                    "Enter variable name (or press Enter to skip, 'q' to quit): "
                ).strip()

                # Quit via console command
                if name.lower() == "q":
                    stop_flag = True
                    print("[INFO] Quit command received. Stopping capture...")
                    break

                # Skip if empty
                if name == "":
                    print("[INFO] Point skipped.")
                    continue

                # Save if name provided
                var_name = normalize_var_name(name)
                if not var_name:
                    print("[WARN] Invalid name, skipping this point.")
                    continue

                saved_points.append((var_name, (x, y)))
                print(f"[SAVED] {var_name} = ({x}, {y})")

            else:
                # No clicks yet; sleep briefly to avoid busy-waiting
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received. Stopping capture...")

    # Stop listeners
    mouse_listener.stop()
    keyboard_listener.stop()

    # Print the collected variables in a copy-pastable format
    print("\n==================== Saved Positions ====================")
    if not saved_points:
        print("No positions were saved.")
    else:
        print("# Copy these into your PyAutoGUI script:")
        for name, (x, y) in saved_points:
            print(f"{name} = ({x}, {y})")
    print("=========================================================")


if __name__ == "__main__":
    main()
