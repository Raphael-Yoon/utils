
import cv2
import numpy as np

def debug_match():
    screen = cv2.imread('current_screen.png')
    template = cv2.imread('button.png')
    
    if screen is None or template is None:
        print("Images not found")
        return

    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    print(f"Max match confidence: {max_val}")
    print(f"Location: {max_loc}")

if __name__ == "__main__":
    debug_match()
