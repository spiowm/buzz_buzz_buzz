import streamlit as st
import cv2
import tempfile
import pandas as pd
import os
import subprocess

from src.core.tracker import BeeTracker
from src.core.database import db
from src.config import DEFAULT_CONFIDENCE

st.set_page_config(page_title="BuzzTrack Dashboard", layout="wide")

def convert_video_to_h264(input_path, output_path):
    """
    Конвертує відео у формат H.264, який підтримується браузерами.
    Використовує системний FFmpeg.
    """
    command = [
        "ffmpeg",
        "-y",                 # Перезаписати файл без питань
        "-i", input_path,     # Вхідний файл
        "-vcodec", "libx264", # Кодек відео (сумісний з браузерами)
        "-f", "mp4",          # Формат контейнера
        output_path           # Вихідний файл
    ]

    # Запускаємо процес конвертації.
    # stdout/stderr приховані, щоб не смітити в консоль,
    # але якщо буде помилка - ми її побачимо через check=True
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        st.error("FFmpeg не знайдено! Встановіть його: sudo dnf install ffmpeg")
        return False

def main():
    st.title("🐝 BuzzTrack: Bee Monitoring System")

    # Сайдбар
    st.sidebar.header("Налаштування")
    conf_threshold = st.sidebar.slider("Поріг впевненості", 0.0, 1.0, DEFAULT_CONFIDENCE)
    line_pos = st.sidebar.slider("Позиція лінії", 0.1, 0.9, 0.5)

    # Вкладки
    tab1, tab2 = st.tabs(["📊 Аналітика", "🎥 Тестування Системи"])

    # --- TAB 1 ---
    with tab1:
        st.header("Жива статистика")
        if st.button("Оновити дані"):
            stats = db.get_stats()
            c1, c2 = st.columns(2)
            c1.metric("Влетіло (IN)", stats["in"])
            c2.metric("Вилетіло (OUT)", stats["out"])

            events = db.get_recent_events(15)
            if events:
                st.dataframe(pd.DataFrame(events), use_container_width=True)
            else:
                st.info("Немає даних")

    # --- TAB 2 ---
    with tab2:
        st.header("Аналіз відео")
        uploaded_file = st.file_uploader("Завантажте відео", type=['mp4', 'avi'])

        if uploaded_file is not None:
            # Зберігаємо вхідний файл
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(uploaded_file.read())
            input_path = tfile.name

            # Тимчасовий файл для сирого виводу OpenCV
            raw_output_path = tempfile.NamedTemporaryFile(delete=False, suffix='_raw.mp4').name
            # Фінальний файл для браузера
            browser_output_path = tempfile.NamedTemporaryFile(delete=False, suffix='_browser.mp4').name

            if st.button("🔴 Почати обробку"):
                tracker = BeeTracker()

                # Елементи інтерфейсу
                progress_bar = st.progress(0)
                status_text = st.empty()
                preview_image = st.empty()

                def update_progress(prog, frame):
                    progress_bar.progress(prog)
                    if int(prog * 100) % 5 == 0:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        preview_image.image(frame_rgb, caption="Обробка...", width="stretch")

                status_text.text("⏳ Обробка відео...")

                # 1. Запуск трекера (пише в raw_output_path)
                tracker.process_video(input_path, raw_output_path, conf_threshold, line_pos, update_progress)

                status_text.text("⚙️ Конвертація для перегляду...")

                # 2. Конвертація ffmpeg
                success = convert_video_to_h264(raw_output_path, browser_output_path)

                preview_image.empty()

                if success:
                    status_text.success("✅ Готово!")
                    st.subheader("🎬 Результат:")
                    st.video(browser_output_path)
                    st.info("Події записані в Базу Даних.")
                else:
                    status_text.error("Помилка конвертації відео. Перевірте, чи встановлено FFmpeg.")
                    # На всяк випадок даємо скачати сирий файл
                    with open(raw_output_path, "rb") as f:
                        st.download_button("Завантажити сире відео (AVI)", f, file_name="result.mp4")

if __name__ == "__main__":
    main()