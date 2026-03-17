import cv2

def open_camera(index=0, use_cap_dshow=True, width=1280, height=720):
    api = cv2.CAP_DSHOW if use_cap_dshow else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, api)
    if not cap.isOpened():
        cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap

def read_frame(cap):
    ok, frame = cap.read()
    return ok, frame
