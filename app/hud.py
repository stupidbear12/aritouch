# hud.py
import cv2

def _fmt3(x):
    return "—" if x is None else f"{x:.3f}"

def draw_hud(frame, info, overlay):
    hud = frame.copy()
    u, v   = info['u'], info['v']
    nx, ny = info['nx'], info['ny']
    nz     = info['nz']
    X, Y   = info['X'], info['Y']
    fps    = info['fps']
    mirror = info['mirror']
    has    = info['has_target']

    if has:
        cv2.circle(hud, (u, v), 12, (0,255,0), 2)
        cv2.drawMarker(hud, (u, v), (255,0,0), markerType=cv2.MARKER_CROSS, thickness=2)

    cv2.putText(hud, f"x={nx:.3f} y={ny:.3f} z={nz:.3f}",
                (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    cv2.putText(hud, f"X={X} Y={Y} FPS={fps:.1f} MIRROR={mirror}",
                (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

    z0    = overlay.get("z0")
    dz    = overlay.get("dz")
    sigma = overlay.get("sigma")
    din   = overlay.get("delta_in")
    dout  = overlay.get("delta_out")
    touching = overlay.get("touching", False)
    pd0   = overlay.get("pinch_d0")
    pd    = overlay.get("pinch_d")
    ticks = overlay.get("zoom_ticks", 0)
    pol   = overlay.get("polarity", "?")

    cv2.putText(hud, f"z0={_fmt3(z0)} dz={_fmt3(dz)} sigma={_fmt3(sigma)}  Δin={_fmt3(din)} Δout={_fmt3(dout)} TOUCH={touching}",
                (10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,200,255), 2)
    cv2.putText(hud, f"pinch0={_fmt3(pd0)} pinch={_fmt3(pd)}  wheelTicks={ticks}  polarity={pol}",
                (10,115), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,220,255), 2)

    return hud
