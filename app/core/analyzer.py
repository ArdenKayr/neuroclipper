import cv2
import os

def extract_frames(self, video_path, interval=1):
    """Вырезает кадры из видео каждую секунду"""
    frames_dir = "assets/temp_frames"
    if not os.path.exists(frames_dir):
        os.makedirs(frames_dir)
        
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = 0
    frame_paths = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Берем каждый N-й кадр (раз в секунду)
        if count % int(fps * interval) == 0:
            frame_name = f"frame_{count}.jpg"
            path = os.path.join(frames_dir, frame_name)
            cv2.imwrite(path, frame)
            frame_paths.append(path)
        count += 1
        
    cap.release()
    return frame_paths