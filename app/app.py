# app.py
import os, time
import cv2
import win32api
from app.config import load_config
from app.camera import open_camera, read_frame
from app.tracker import HandTracker
from app.gestures import TouchZoomController, clamp
from app.hud import draw_hud

def flip_horizontal(frame):
    return cv2.flip(frame, 1)

def to_screen_xy(x, y, SW, SH):
    return int(x * SW), int(y * SH)

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg  = load_config(os.path.join(here, "config.json"))

    cap = open_camera(
    cfg["camera_index"],
    cfg["use_cap_dshow"],
    width=int(cfg.get("camera_width", 1280)),
    height=int(cfg.get("camera_height", 720))
)
    if not cap or not cap.isOpened():
        print("Camera open failed"); return

    tracker = HandTracker()
    zoom = TouchZoomController(cfg)

    # 주 모니터 해상도
    SW, SH = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)

    mirror    = bool(cfg["mirror"])
    smoothing = float(cfg["smoothing"])
    ema_x = ema_y = None
    Xs = Ys = 0

    prev = time.time()
    fps_ma = 30.0

    print("[Keys] q/ESC: exit, m: mirror, s: smoothing toggle")

    try:
        while True:
            ok, frame = read_frame(cap)
            if not ok: break

            if mirror:
                frame = flip_horizontal(frame)
            H, W = frame.shape[0], frame.shape[1]

            res = tracker.process(frame)
            has = res is not None
            if has:
                nx, ny, nz = res['index_tip']
                tx, ty, thz = res['thumb_tip']
                nx, ny = clamp(nx,0,1), clamp(ny,0,1)
                tx, ty = clamp(tx,0,1), clamp(ty,0,1)
                u, v = int(nx*W), int(ny*H)

                X, Y = to_screen_xy(nx, ny, SW, SH)
                if ema_x is None:
                    ema_x, ema_y = X, Y
                else:
                    ema_x = smoothing*X + (1-smoothing)*ema_x
                    ema_y = smoothing*Y + (1-smoothing)*ema_y
                    ema_x = clamp(ema_x, 0, SW-1)
                    ema_y = clamp(ema_y, 0, SH-1)
                Xs, Ys = int(ema_x), int(ema_y)
            else:
                nx = ny = nz = 0.0
                tx = ty = thz = 0.0
                u = v = Xs = Ys = 0

            now = time.time()
            dt = max(1e-6, now - prev)
            fps = 1.0 / dt
            fps_ma = 0.9*fps_ma + 0.1*fps
            prev = now

            overlay = {}
            if has:
                overlay = zoom.update(
                    nx, ny, nz, tx, ty, thz,
                    Xs, Ys, int(now*1000), SW, SH
                )

            info = {
                "u": u, "v": v, "nx": nx, "ny": ny, "nz": nz,
                "X": Xs, "Y": Ys, "fps": fps_ma, "mirror": mirror,
                "has_target": has
            }
            hud = draw_hud(frame, info, overlay)
            cv2.imshow("Airtouch - Touch + Pinch Zoom", hud)

            k = cv2.waitKey(1) & 0xFF
            if k in (27, ord('q')): break
            if k == ord('m'): mirror = not mirror
            if k == ord('s'): smoothing = 0.5 if abs(smoothing-0.3)<1e-9 else 0.3

    finally:
        try: cap.release()
        except: pass
        cv2.destroyAllWindows()
        tracker.close()

if __name__ == "__main__":
    main()
