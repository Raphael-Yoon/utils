import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import sys
import cv2
import numpy as np
import pyautogui
from datetime import datetime
from PIL import ImageGrab
import subprocess

# 어디서 실행해도 이미지를 찾을 수 있도록 현재 스크립트의 절대 경로 확보
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# 1. 자동 클릭 에이전트 클래스 (로직 분리)
# ==========================================
class ClickAgentThread(threading.Thread):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.daemon = True
        self.running = False
        self.enabled = True
        
    def log(self, message, is_status=False):
        self.gui.update_log_signal(message, is_status)

    def capture_all_monitors(self):
        try:
            # 찰칵 소리가 나는 pyautogui(gnome-screenshot) 대신, 빠르고 '조용한' mss 라이브러리를 사용합니다.
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]  # 모든 모니터의 통합 화면
                sct_img = sct.grab(monitor)
                # mss는 BGRA 포맷을 반환하므로 cv2에서 사용하기 위해 BGR로 변환
                img = np.array(sct_img)
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except ImportError:
            self.log("⚠️ mss 라이브러리가 설치되지 않았습니다. 터미널에서 'pip install mss'를 실행해주세요.")
            return None
        except Exception as e:
            self.log(f"Capture Error (mss): {e}")
            return None

    def find_image(self, confidence):
        """여러 이미지 중 가장 유사도가 높은 것을 찾음"""
        screen = self.capture_all_monitors()
        if screen is None: return (None, None, None, None, 0, None)
        
        targets = ['button.png', 'button2.png', 'image.jpg']
        best_match = (None, None, None, None, 0, None) # x, y, w, h, val, name
        
        for name in targets:
            img_path = os.path.join(BASE_DIR, name)
            if not os.path.exists(img_path): continue
            template = cv2.imread(img_path)
            if template is None: continue
            
            res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            if max_val >= confidence and max_val > best_match[4]:
                h, w = template.shape[:2]
                # Windows 특화 Offset 로직 제거 -> 리눅스 좌표 체계에 맞게 단순화
                x = max_loc[0]
                y = max_loc[1]
                best_match = (x, y, w, h, max_val, name)
        
        return best_match

    def run(self):
        self.running = True
        self.log("▶ 에이전트 서비스가 시작되었습니다. (Linux 버전)")
        
        while self.running:
            conf_threshold = self.gui.get_confidence()
            target_title = self.gui.get_target_title()
            check_interval = self.gui.get_interval()
            cool_down = 2.0

            if not self.enabled:
                time.sleep(0.1)
                continue

            try:
                res = self.find_image(conf_threshold)
                current_max = res[4]
                match_name = res[5]
                self.gui.update_confidence_ui(current_max)
                
                status_msg = f"🔍 분석 중... (유사도: {current_max:.3f})"
                if match_name: status_msg += f" [{match_name}]"
                self.log(status_msg, is_status=True)

                if res[0] is not None:
                    confidence = res[4]
                    
                    if target_title.strip():
                        if self.find_window(target_title):
                            self.activate_window(target_title)
                            time.sleep(0.1)
                        else:
                            self.log(f"⚠️ '{target_title}' 창을 찾을 수 없습니다.", is_status=True)
                            time.sleep(1.0)
                            continue

                    pyautogui.hotkey('alt', 'enter')
                    self.log(f"✅ 발견({confidence:.2f}) [{match_name}] & 🚀 Alt+Enter 입력 완료")
                        
                    for i in range(int(cool_down * 10), 0, -1):
                         self.log(f"⏳ 대기 중... {i/10:.1f}s", is_status=True)
                         time.sleep(0.1)
                    self.log("🔄 모니터링 재개...", is_status=True)

            except Exception as e:
                self.log(f"❌ 오류: {e}", is_status=True)

            time.sleep(check_interval)

    def find_window(self, partial_title):
        """wmctrl 명령어로 창 검색 (Linux 환경)"""
        try:
            output = subprocess.check_output(['wmctrl', '-l']).decode('utf-8', errors='ignore')
            for line in output.splitlines():
                parts = line.split(maxsplit=3)
                if len(parts) >= 4:
                    title = parts[3]
                    if partial_title.lower() in title.lower():
                        return True
            return False
        except FileNotFoundError:
            self.log("⚠️ wmctrl 패키지가 없습니다. (sudo apt install wmctrl 필요)")
            return True # 테스트 및 강제진행을 위해 True를 반환
        except Exception:
            return False

    def activate_window(self, partial_title):
        """wmctrl 명령어로 창 활성화 (Linux 환경)"""
        try:
            subprocess.run(['wmctrl', '-a', partial_title], check=False)
        except Exception as e:
             self.log(f"⚠️ 창 활성화 실패: {e}")

    def stop(self):
        self.running = False


# ==========================================
# 2. 메인 GUI 클래스
# ==========================================
class AutoClickGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Antigravity Auto Click v1.0 (Linux)")
        self.root.geometry("500x700")
        self.root.resizable(False, False)
        
        # 스타일 설정
        self.setup_styles()
        
        # 메인 프레임
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 상태 표시 영역
        self.status_label = tk.Label(main_frame, text="에이전트 중지됨", font=("NanumGothicBold", 18), 
                                    fg="white", bg="#666666", pady=10)
        self.status_label.pack(fill=tk.X, pady=(0, 20))

        # 2. 실시간 유사도 바
        ttk.Label(main_frame, text="현재 최대 유사도 (실시간)").pack(anchor=tk.W)
        self.conf_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.conf_bar.pack(fill=tk.X, pady=(5, 5))
        self.conf_val_label = ttk.Label(main_frame, text="0.000", font=("Consolas", 10))
        self.conf_val_label.pack(anchor=tk.E, pady=(0, 15))

        # 3. 설정 영역
        settings_group = ttk.LabelFrame(main_frame, text=" 에이전트 설정 ", padding="15")
        settings_group.pack(fill=tk.X, pady=10)

        # 목표 신뢰도 슬라이더
        ttk.Label(settings_group, text="목표 신뢰도 (Threshold)").pack(anchor=tk.W)
        self.conf_scale = ttk.Scale(settings_group, from_=0.1, to=1.0, orient=tk.HORIZONTAL)
        self.conf_scale.set(0.65)
        self.conf_scale.pack(fill=tk.X, pady=(5, 15))
        self.conf_target_label = ttk.Label(settings_group, text="현재 설정: 0.65")
        self.conf_target_label.pack(anchor=tk.E)
        self.conf_scale.configure(command=self.on_scale_change)

        # 타겟 윈도우 제목
        ttk.Label(settings_group, text="대상 윈도우 제목 (선택 또는 붙여넣기)").pack(anchor=tk.W)
        
        title_frame = ttk.Frame(settings_group)
        title_frame.pack(fill=tk.X, pady=(5, 15))

        self.title_entry = ttk.Combobox(title_frame)
        self.title_entry.insert(0, "Antigravity")
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.refresh_btn = ttk.Button(title_frame, text="🔄 창 목록 새로고침", command=self.refresh_window_list)
        self.refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # 체크 간격
        ttk.Label(settings_group, text="검색 주기 (초)").pack(anchor=tk.W)
        self.interval_entry = ttk.Entry(settings_group)
        self.interval_entry.insert(0, "1.0")
        self.interval_entry.pack(fill=tk.X, pady=(5, 0))

        # 5. 하단 버튼 영역
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

        btn_frame = ttk.Frame(footer_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.toggle_btn = tk.Button(btn_frame, text="에이전트 시작 (F9)", command=self.toggle_agent,
                                   bg="#28a745", fg="white", font=("DejaVu Sans", 11, "bold"),
                                   relief="flat", pady=10, cursor="hand2")
        self.toggle_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # 4. 로그 영역
        ttk.Label(main_frame, text="작업 로그").pack(anchor=tk.W, pady=(15, 5))
        self.log_area = scrolledtext.ScrolledText(main_frame, height=8, font=("Consolas", 9), state='disabled', bg="#f8f9fa")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.agent = None
        
        self.root.after(500, self.start_agent)
        self.root.bind("<F9>", lambda e: self.toggle_agent())

    def refresh_window_list(self):
        try:
            output = subprocess.check_output(['wmctrl', '-l']).decode('utf-8', errors='ignore')
            titles = []
            for line in output.splitlines():
                parts = line.split(maxsplit=3)
                if len(parts) >= 4:
                    title = parts[3]
                    if title not in titles:
                        titles.append(title)
            self.title_entry['values'] = titles
            self._append_log("현재 열려있는 창 목록을 새로고침했습니다.", is_status=False)
        except Exception as e:
            messagebox.showwarning("경고", f"창 목록을 불러올 수 없습니다.\n{e}")

    def setup_styles(self):
        style = ttk.Style()
        # 리눅스 환경 기본 폰트 적용
        style.configure(".", font=("DejaVu Sans", 10))
        style.configure("TLabelframe", borderwidth=1)
        style.configure("TLabelframe.Label", font=("DejaVu Sans", 10, "bold"))

    def on_scale_change(self, val):
        self.conf_target_label.config(text=f"현재 설정: {float(val):.2f}")

    def get_confidence(self):
        return self.conf_scale.get()

    def get_target_title(self):
        return self.title_entry.get()

    def get_interval(self):
        try:
            return float(self.interval_entry.get())
        except:
            return 1.0

    def toggle_agent(self):
        if self.agent and self.agent.running:
            self.stop_agent()
        else:
            self.start_agent()

    def start_agent(self):
        targets = ['button.png', 'button2.png', 'image.jpg']
        if not any(os.path.exists(os.path.join(BASE_DIR, t)) for t in targets):
            messagebox.showerror("오류", f"매칭할 이미지 파일({', '.join(targets)})이 하나도 없습니다.\n경로: {BASE_DIR}")
            return

        self.agent = ClickAgentThread(self)
        self.agent.start()
        
        self.toggle_btn.config(text="에이전트 중지 (F9)", bg="#dc3545")
        self.status_label.config(text="모니터링 작동 중", bg="#28a745")

    def stop_agent(self):
        if self.agent:
            self.agent.stop()
            self.agent = None
        
        self.toggle_btn.config(text="에이전트 시작 (F9)", bg="#28a745")
        self.set_status_stopped()

    def set_status_stopped(self):
        self.status_label.config(text="에이전트 중지됨", bg="#666666", fg="white")
        self.conf_bar['value'] = 0
        self.conf_val_label.config(text="0.000")

    def update_confidence_ui(self, val):
        self.root.after(0, self._update_conf, val)

    def _update_conf(self, val):
        self.conf_bar['value'] = val * 100
        self.conf_val_label.config(text=f"{val:.3f}")

    def update_log_signal(self, message, is_status=False):
        self.root.after(0, self._append_log, message, is_status)

    def _append_log(self, message, is_status):
        now = datetime.now().strftime('%H:%M:%S')
        full_msg = f"[{now}] {message}"
        
        if is_status:
            self.root.title(f"Auto Click (Linux) - {message}")
            return

        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, full_msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClickGUI(root)
    root.mainloop()
