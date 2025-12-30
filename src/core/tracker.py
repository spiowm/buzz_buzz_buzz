import cv2
import numpy as np
from collections import deque
from ultralytics import YOLO
from src.config import MODEL_PATH, TRACKER_TYPE
from src.core.database import db

class BeeTracker:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(model_path)

        # Історія точок для малювання "хвостів" {track_id: deque([(x, y), ...])}
        self.trails = {}
        self.max_trail_length = 30  # Довжина хвоста

        # Статуси бджіл: {track_id: 'in' | 'out' | 'unknown'}
        self.bee_states = {}

        # Сет для ID, які вже були пораховані
        self.counted_ids = set()

    def process_video(self, source_path, output_path, conf_threshold, line_pos_y, progress_callback=None):
        """
        Обробляє відео повністю, зберігає результат у файл і повертає статистику.
        """
        cap = cv2.VideoCapture(source_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Налаштування запису відео (MP4)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        line_y = int(height * line_pos_y)
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # --- 1. Трекінг ---
            results = self.model.track(
                frame,
                persist=True,
                conf=conf_threshold,
                tracker=TRACKER_TYPE,
                verbose=False
            )

            # --- 2. Аналіз та Малювання ---
            # Малюємо лінію підрахунку (візуально)
            cv2.line(frame, (0, line_y), (width, line_y), (0, 255, 255), 2)
            cv2.putText(frame, "ENTRANCE LINE", (10, line_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()

                for box, track_id in zip(boxes, track_ids):
                    x, y, w, h = box
                    center = (float(x), float(y))

                    # 2.1 Оновлення хвостів
                    if track_id not in self.trails:
                        self.trails[track_id] = deque(maxlen=self.max_trail_length)
                    self.trails[track_id].append(center)

                    # 2.2 Визначення статусу (In/Out)
                    # Якщо бджоли ще немає в статусах, вона 'unknown'
                    if track_id not in self.bee_states:
                        self.bee_states[track_id] = 'unknown'

                    # Перевірка перетину
                    if len(self.trails[track_id]) >= 2:
                        prev_y = self.trails[track_id][-2][1]
                        curr_y = center[1]

                        # Логіка перетину:
                        # y збільшується (рух вниз) -> IN
                        # y зменшується (рух вгору) -> OUT
                        if track_id not in self.counted_ids:
                            if prev_y < line_y and curr_y >= line_y:
                                self.bee_states[track_id] = 'in'
                                self.counted_ids.add(track_id)
                                db.log_event("in", track_id, 0.99) # Confidence поки заглушка

                            elif prev_y > line_y and curr_y <= line_y:
                                self.bee_states[track_id] = 'out'
                                self.counted_ids.add(track_id)
                                db.log_event("out", track_id, 0.99)

                    # 2.3 Візуалізація
                    color = (255, 0, 0) # Синій (невідомо)
                    if self.bee_states[track_id] == 'in':
                        color = (0, 255, 0) # Зелений
                    elif self.bee_states[track_id] == 'out':
                        color = (0, 0, 255) # Червоний (BGR формат в OpenCV)

                    # Малюємо рамку
                    x1, y1 = int(x - w/2), int(y - h/2)
                    x2, y2 = int(x + w/2), int(y + h/2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    # Малюємо хвіст
                    points = np.array(self.trails[track_id], dtype=np.int32).reshape((-1, 1, 2))
                    cv2.polylines(frame, [points], False, color, 2)

                    # Підпис ID
                    cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # --- 3. Збереження кадру ---
            out.write(frame)

            # Оновлення прогресу
            frame_idx += 1
            if progress_callback:
                progress_callback(frame_idx / total_frames, frame)

        cap.release()
        out.release()
        return output_path