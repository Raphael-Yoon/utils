import pyautogui
import time
import cv2
import numpy as np
import os
import sys
from datetime import datetime
from PIL import ImageGrab
import win32gui
import win32con
import ctypes

# ==========================================
# 1. 환경 설정 (Configuration)
# ==========================================
IMAGE_NAME = 'image.jpg'
MATCH_CONFIDENCE = 0.7  # 0.8에서 0.7로 조정
CHECK_INTERVAL = 1.0  
COOL_DOWN_TIME = 2.0  
TARGET_WINDOW_TITLE = 'Antigravity'
TOGGLE_KEY = 0x78  # F9

pyautogui.FAILSAFE = True
LAST_WAS_STATUS = False

def log(message, is_status=False):
    global LAST_WAS_STATUS
    now = datetime.now().strftime('%H:%M:%S')
    msg = f"[{now}] {message}"
    if is_status:
        sys.stdout.write(f"\r{msg}".ljust(100))
        sys.stdout.flush()
        LAST_WAS_STATUS = True
    else:
        sys.stdout.write(f"\r{msg}".ljust(100) + "\n")
        sys.stdout.flush()
        LAST_WAS_STATUS = False

def capture_all_monitors():
    screenshot = ImageGrab.grab(all_screens=True)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

def find_image_on_all_screens(template_path, confidence=0.7):
    template = cv2.imread(template_path)
    if template is None: return None
    
    screen = capture_all_monitors()
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 발견 여부와 상관없이 현재 최대 신뢰도(max_val)를 반환값에 포함
    if max_val >= confidence:
        h, w = template.shape[:2]
        user32 = ctypes.windll.user32
        virtual_left = user32.GetSystemMetrics(76)
        virtual_top = user32.GetSystemMetrics(77)
        x = max_loc[0] + virtual_left
        y = max_loc[1] + virtual_top
        return (x, y, w, h, max_val)
    
    return (None, None, None, None, max_val) # 발견 못 해도 max_val 반환

def find_window_by_partial_title(partial_title):
    result = []
    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if partial_title.lower() in title.lower():
                result.append((hwnd, title))
        return True
    win32gui.EnumWindows(enum_callback, None)
    return result[0] if result else None

def run_agent():
    log("Auto Click Agent 시작...")
    if not os.path.exists(IMAGE_NAME):
        log(f"❌ 오류: '{IMAGE_NAME}' 없음")
        return

    log(f"🔍 모니터링 시작 (목표 신뢰도: {MATCH_CONFIDENCE})")
    log("--------------------------------------------------")
    log("💡 토글: [F9] / 활성화 시에만 분석")
    log("--------------------------------------------------")

    enabled = True

    try:
        while True:
            if ctypes.windll.user32.GetAsyncKeyState(TOGGLE_KEY) & 1:
                enabled = not enabled
                if enabled: log("▶ 모니터링 활성화")
                else: log("⏸ 일시정지 상태 (F9로 재개)", is_status=True)

            if not enabled:
                time.sleep(0.1)
                continue

            # 분석 중 상태 표시와 실시간 유사도 노출
            try:
                # result의 마지막 값이 max_val
                res = find_image_on_all_screens(IMAGE_NAME, MATCH_CONFIDENCE)
                current_max = res[4]
                
                log(f"🔍 화면 분석 중... (최대 유사도: {current_max:.3f})", is_status=True)

                if res[0] is not None:
                    x, y, w, h, confidence = res
                    window_info = find_window_by_partial_title(TARGET_WINDOW_TITLE)
                    if window_info:
                        hwnd, full_title = window_info
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.1)
                        pyautogui.hotkey('alt', 'enter')
                        log(f"✅ 발견({confidence:.2f}) & 🚀 '{full_title}' 완료")
                        
                        for i in range(int(COOL_DOWN_TIME * 10), 0, -1):
                             log(f"⏳ 대기 중... {i/10:.1f}s", is_status=True)
                             time.sleep(0.1)
                        log("🔄 모니터링 재개...", is_status=True)
                    else:
                        log(f"⚠️ '{TARGET_WINDOW_TITLE}' 창 없음", is_status=True)

            except Exception as e:
                log(f"❌ 오류: {e}", is_status=True)

            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        log("중단됨")
    except Exception as e:
        log(f"시스템 오류: {e}")

if __name__ == "__main__":
    run_agent()
