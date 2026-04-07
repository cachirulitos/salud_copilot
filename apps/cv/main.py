import argparse
import asyncio
import sys
import threading
import time

import cv2

from config import settings
from models.people_detector import PeopleDetector
from services.count_publisher import publish_people_count
from utils.overlay import draw_demo_frame, draw_frame

DEMO_PEOPLE_PATTERN = [3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 2, 2, 2]
WINDOW_TITLE = "SaludCopilot — Monitoreo en tiempo real"
WINDOW_REFRESH_MS = 60  # ~30 fps


def _open_camera() -> cv2.VideoCapture:
    """Open the configured camera index or exit with a clear error."""
    cap = cv2.VideoCapture(settings.camera_index)
    if not cap.isOpened():
        print(
            f"Error: no se pudo abrir la camara (indice {settings.camera_index}). "
            "Verifica que este conectada."
        )
        sys.exit(1)
    return cap


def _open_video(video_path: str) -> cv2.VideoCapture:
    """Open a video file as the frame source or exit with a clear error."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: no se pudo abrir el video '{video_path}'.")
        sys.exit(1)
    return cap


def _publish_in_background(area_id: str, people_count: int) -> None:
    """Fire-and-forget HTTP publish on a background thread."""
    try:
        asyncio.run(publish_people_count(area_id, people_count))
    except Exception as exc:
        print(f"Error publicando conteo: {exc}")


def _resolve_area_id(video_path: str, area_id_override: str) -> str:
    """Resolve the area UUID for this worker instance.

    Priority:
    1. --area-id CLI flag (explicit, works for camera and video)
    2. CAMERA_TO_AREA_MAPPING[camera_index] (camera mode only)
    """
    if area_id_override:
        return area_id_override

    if video_path:
        print(
            "ERROR: --area-id es obligatorio cuando se usa --video.\n"
            "Ejemplo: python main.py --video sala.mp4 --area-id <UUID>"
        )
        sys.exit(1)

    area_id = settings.area_mapping.get(str(settings.camera_index))
    if not area_id:
        print(
            f"ERROR: CAMERA_INDEX={settings.camera_index} no tiene entrada en "
            "CAMERA_TO_AREA_MAPPING. Agrega la clave al .env o usa --area-id."
        )
        sys.exit(1)
    return area_id


def run_loop(
    demo_mode: bool = False,
    show_window: bool = True,
    video_path: str = "",
    area_id_override: str = "",
    area_name: str = "Sala de espera",
) -> None:
    """Main capture loop: read frames, detect people, publish count to API.

    Each worker instance handles exactly one video source (camera or file)
    and publishes to exactly one clinical area. Run one instance per camera.

    Args:
        demo_mode: Use a synthetic pattern instead of a real video source.
        show_window: Show the annotated preview window.
        video_path: Path to video file. Empty = use CAMERA_INDEX. Ignored
            in demo_mode.
        area_id_override: UUID of the area to publish to. Required with
            --video; optional for camera mode.
        area_name: Human-readable area name shown in the overlay.
    """
    if not demo_mode:
        area_id = _resolve_area_id(video_path, area_id_override)
    else:
        area_id = area_id_override or next(iter(settings.area_mapping.values()), "")
        if not area_id:
            print("ERROR: CAMERA_TO_AREA_MAPPING esta vacio.")
            sys.exit(1)

    roi = settings.roi_rect
    detector = PeopleDetector(settings.yolo_model_name, settings.confidence_threshold)
    capture = None
    demo_index = 0

    if not demo_mode:
        capture = _open_video(video_path) if video_path else _open_camera()
        mode_label = f"VIDEO: {video_path}" if video_path else "CAMARA REAL"
    else:
        mode_label = "DEMO"

    print(f"SaludCopilot CV Worker | Modo: {mode_label} | Area: {area_name} ({area_id})")
    if roi:
        print(f"ROI activo: {roi}")
    if show_window:
        print("Presiona 'q' en la ventana para salir.")

    last_publish_time = 0.0
    publish_interval = settings.capture_interval_seconds
    people_count = 0
    last_nonzero_count = 0
    last_nonzero_time = 0.0
    zero_sustain_seconds = 8.0

    if show_window:
        cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)

    try:
        while True:
            # ── Capture & detect ─────────────────────────────────────────
            if demo_mode:
                people_count = DEMO_PEOPLE_PATTERN[demo_index % len(DEMO_PEOPLE_PATTERN)]
                demo_index += 1
                display_frame = draw_demo_frame(people_count, area_name, last_publish_time)

            else:
                ok, raw_frame = capture.read()
                if not ok:
                    if video_path:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    print("Advertencia: frame no capturado, reintentando...")
                    time.sleep(0.1)
                    continue

                detection = detector.detect(raw_frame, roi=roi)
                raw_count = detection.count

                # Floor temporal: no reportar 0 hasta que se sostenga
                # por zero_sustain_seconds — evita caídas momentáneas
                now_mono = time.monotonic()
                if raw_count > 0:
                    last_nonzero_count = raw_count
                    last_nonzero_time = now_mono
                    people_count = raw_count
                elif now_mono - last_nonzero_time < zero_sustain_seconds:
                    people_count = last_nonzero_count
                else:
                    people_count = 0

                detection.count = people_count
                display_frame = draw_frame(
                    raw_frame, detection, area_name, roi, last_publish_time
                )

            # ── Publish at configured interval ───────────────────────────
            now = time.monotonic()
            if now - last_publish_time >= publish_interval:
                last_publish_time = now
                threading.Thread(
                    target=_publish_in_background,
                    args=(area_id, people_count),
                    daemon=True,
                ).start()

            # ── Display ──────────────────────────────────────────────────
            if show_window:
                cv2.imshow(WINDOW_TITLE, display_frame)
                key = cv2.waitKey(WINDOW_REFRESH_MS) & 0xFF
                window_closed = cv2.getWindowProperty(
                    WINDOW_TITLE, cv2.WND_PROP_VISIBLE
                ) < 1
                if key == ord("q") or window_closed:
                    break
            else:
                time.sleep(publish_interval)

    except KeyboardInterrupt:
        print("\nCV Worker detenido.")
    finally:
        if capture:
            capture.release()
        if show_window:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SaludCopilot CV Worker")
    parser.add_argument(
        "--demo", action="store_true",
        help="Usar patron simulado en lugar de camara o video",
    )
    parser.add_argument(
        "--no-window", action="store_true",
        help="No mostrar ventana de preview (headless / Wayland)",
    )
    parser.add_argument(
        "--video", metavar="PATH", default="",
        help="Ruta a un archivo de video (mp4, avi...). "
             "Omitir para usar CAMERA_INDEX.",
    )
    parser.add_argument(
        "--area-id", metavar="UUID", default="",
        help="UUID del area clinica a la que publicar. "
             "Obligatorio con --video.",
    )
    parser.add_argument(
        "--area-name", metavar="NOMBRE", default="Sala de espera",
        help="Nombre del area mostrado en el overlay (default: 'Sala de espera')",
    )
    args = parser.parse_args()
    run_loop(
        demo_mode=args.demo,
        show_window=not args.no_window,
        video_path=args.video,
        area_id_override=args.area_id,
        area_name=args.area_name,
    )