import os, time
import cv2
import win32api
from app.config import load_config
from app.camera import open_camera, read_frame
from app.hud import draw_hud
from core.mediapipe_runner import MPRunner
from gesture.config import GestureConfig
from gesture.feature_extractor import (
    extract_hand_points, extract_eye_midpoint,
    compute_joint_angles, compute_pinch_dist, compute_z_delta,
)
from gesture.candidate_scorer import RuleBasedScorer
from gesture.gesture_decider import GestureDecider
from gesture.context_fusion import ContextFusion, ContextInfo
from gesture.gesture_applier import GestureApplier, CursorMapper
from control.mouse_actions import MouseController
from control.zoom_actions import ZoomActions
from control.cursor_manager import CursorManager
from utils.constants import IDX_TIP
from utils.geometry import normalize_landmark


def _make_event_queue(cfg):
    srv = cfg.get("server_url", "")
    bid = cfg.get("bed_id", "")
    if not srv or not bid:
        return None, bid
    try:
        from net.api_client import AirTouchClient
        from net.event_queue import EventQueue
        client = AirTouchClient(base_url=srv)
        eq = EventQueue(client, flush_interval=5.0)
        eq.start()
        return eq, bid
    except Exception:
        return None, bid


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

    SW, SH = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)

    runner  = MPRunner()
    g_cfg   = GestureConfig()
    scorer  = RuleBasedScorer(g_cfg)
    decider = GestureDecider(min_stable_frames=2, min_confidence=0.3)
    fusion  = ContextFusion()
    context = ContextInfo()
    mapper  = CursorMapper(SW, SH, ema_alpha=g_cfg.ema_cursor)
    applier = GestureApplier(
        config=g_cfg,
        mouse=MouseController(),
        zoom=ZoomActions(),
        cursor=CursorManager(),
        cursor_mapper=mapper,
    )

    mirror = bool(cfg["mirror"])
    eq, bed_id = _make_event_queue(cfg)

    prev   = time.time()
    fps_ma = 30.0
    Xs = Ys = 0

    print("[Keys] q/ESC: exit, m: mirror")

    try:
        while True:
            ok, frame = read_frame(cap)
            if not ok:
                break

            if mirror:
                frame = cv2.flip(frame, 1)
            H, W = frame.shape[:2]

            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = runner.process(rgb)
            has    = result.hand_landmarks is not None

            nx = ny = nz = 0.0
            u = v = 0
            label_str = "IDLE"

            if has:
                hp      = extract_hand_points(result.hand_landmarks, W, H)
                angles  = compute_joint_angles(hp)
                pinch_d = compute_pinch_dist(hp)

                _, tip_z = normalize_landmark(result.hand_landmarks.landmark[IDX_TIP], W, H)

                if result.face_landmarks is not None:
                    _, eye_z = extract_eye_midpoint(result.face_landmarks, W, H)
                    z_delta  = compute_z_delta(eye_z, tip_z)
                else:
                    z_delta = 0.0

                z_active = z_delta > g_cfg.z_margin

                scores  = scorer.score(angles, pinch_d, z_active)
                decided = decider.update(scores)
                label   = fusion.fuse(decided, context)
                label_str = label.name

                anchor = hp.cursor_anchor
                nx = float(anchor[0]) / W
                ny = float(anchor[1]) / H
                nz = tip_z / W
                u, v = int(anchor[0]), int(anchor[1])

                apply_result = applier.apply(label, {
                    "anchor_x": nx,
                    "anchor_y": ny,
                    "pinch_dist": pinch_d,
                })
                Xs, Ys = apply_result.cursor_x, apply_result.cursor_y

                if eq and bed_id:
                    eq.put({
                        "bed_id": bed_id,
                        "event_type": "gesture",
                        "severity": 0,
                        "data": {
                            "gesture": label.name,
                            "fps": round(fps_ma, 1),
                        },
                    })
            else:
                decider.reset()
                Xs = Ys = 0

            runner.draw(frame, result)

            now    = time.time()
            dt     = max(1e-6, now - prev)
            fps_ma = 0.9 * fps_ma + 0.1 / dt
            prev   = now

            info = {
                "u": u, "v": v, "nx": nx, "ny": ny, "nz": nz,
                "X": Xs, "Y": Ys, "fps": fps_ma, "mirror": mirror,
                "has_target": has,
            }
            overlay = {"gesture": label_str}
            hud = draw_hud(frame, info, overlay)
            cv2.imshow("Airtouch", hud)

            k = cv2.waitKey(1) & 0xFF
            if k in (27, ord('q')):
                break
            if k == ord('m'):
                mirror = not mirror

    finally:
        if eq:
            eq.stop()
        try:
            cap.release()
        except Exception:
            pass
        cv2.destroyAllWindows()
        runner.close()


if __name__ == "__main__":
    main()
