import cv2
import numpy as np
import os

def crop_button(src_path, dst_path):
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found.")
        return False

    img = cv2.imread(src_path)
    if img is None:
        print("Error: Could not read image.")
        return False

    # 이미지를 HSV 색공간으로 변환 (파란색 버튼 검출 목적)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 파란색 범위 설정 (일반적인 파란색)
    lower_blue = np.array([100, 150, 0])
    upper_blue = np.array([140, 255, 255])
    
    # 마스크 생성
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # 컨투어 찾기
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("No button found in the image.")
        return False
    
    # 가장 큰 사각형 영역 찾기
    largest_cnt = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_cnt)
    
    # 영역 크롭
    button_img = img[y:y+h, x:x+w]
    
    # 저장
    cv2.imwrite(dst_path, button_img)
    print(f"Successfully cropped button and saved to {dst_path}")
    return True

if __name__ == "__main__":
    crop_button('current_screen.png', 'button.png')
