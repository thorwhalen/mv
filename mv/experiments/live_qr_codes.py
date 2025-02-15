"""Live QR code detection and decoding"""

import cv2
import numpy as np
import contextlib
import time


# ----------------------------------------------------------------
# Overlay Manager (persistent overlays for a set duration)
# ----------------------------------------------------------------
class OverlayManager:
    """
    Manages persistent overlays on video frames.

    Each overlay (polygon or text) is stored along with a timestamp.
    When rendering, only overlays added within the last `overlay_duration`
    seconds are drawn.
    """

    def __init__(self, overlay_duration=2.0):
        self.overlay_duration = overlay_duration
        self.overlays = {'polygons': [], 'texts': []}

    def update(self, new_overlays):
        """Adds new overlay items from the provided dictionary."""
        now = time.time()
        if 'polygons' in new_overlays:
            for poly in new_overlays['polygons']:
                self.overlays['polygons'].append((poly, now))
        if 'texts' in new_overlays:
            for text_item in new_overlays['texts']:
                self.overlays['texts'].append((text_item, now))

    def render(self, frame):
        """Renders all overlays that are still fresh onto the frame."""
        now = time.time()

        def keep(overlay):
            _, timestamp = overlay
            return (now - timestamp) <= self.overlay_duration

        self.overlays['polygons'] = list(filter(keep, self.overlays['polygons']))
        self.overlays['texts'] = list(filter(keep, self.overlays['texts']))

        for poly, _ in self.overlays['polygons']:
            cv2.polylines(frame, [poly], isClosed=True, color=(0, 255, 0), thickness=2)

        for text_item, _ in self.overlays['texts']:
            cv2.putText(
                frame,
                text_item['text'],
                text_item['position'],
                text_item.get('font', cv2.FONT_HERSHEY_SIMPLEX),
                text_item.get('scale', 0.6),
                text_item.get('color', (255, 0, 0)),
                text_item.get('thickness', 2),
            )
        return frame


# Global overlay manager instance.
overlay_manager = OverlayManager(overlay_duration=2.0)


def default_displayer(frame, display_data):
    """
    Updates the persistent overlays and then displays the frame.

    This function updates the global OverlayManager with any new overlays
    provided in display_data, renders all persistent overlays on the frame,
    and then shows the result.
    """
    if display_data is None:
        display_data = {}
    overlay_manager.update(display_data)
    window_name = display_data.get('window_name', "Video")
    overlay_manager.render(frame)
    cv2.imshow(window_name, frame)


# ----------------------------------------------------------------
# Video capture context manager and pipeline
# ----------------------------------------------------------------
@contextlib.contextmanager
def video_capture(source=0):
    cap = cv2.VideoCapture(source)
    try:
        yield cap
    finally:
        cap.release()
        cv2.destroyAllWindows()


def run_video_pipeline(detector, compute_display_data, displayer, source=0):
    with video_capture(source) as cap:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            detection_result = detector(frame)
            display_data = compute_display_data(detection_result, frame)
            displayer(frame, display_data)
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                break


# ----------------------------------------------------------------
# QR Code detector factory
# ----------------------------------------------------------------
def make_qr_detector():
    qr_detector_obj = cv2.QRCodeDetector()

    def detector(frame):
        data, points, _ = qr_detector_obj.detectAndDecode(frame)
        if points is not None and data:
            return {'data': data, 'points': points}
        return None

    return detector


# ----------------------------------------------------------------
# Example 1: Display only the QR code rectangle and the text it encodes.
# ----------------------------------------------------------------
def compute_display_data_example1(detection_result, frame):
    display_data = {}
    if detection_result is not None:
        pts = detection_result['points'][0].astype(int)
        poly = pts.reshape((-1, 1, 2))
        display_data.setdefault('polygons', []).append(poly)

        # Display the encoded text near the bounding box.
        x, y, _, _ = cv2.boundingRect(pts.reshape((-1, 1, 2)))
        text_position = (x, max(y - 10, 20))
        display_data.setdefault('texts', []).append(
            {
                'text': detection_result['data'],
                'position': text_position,
                'font': cv2.FONT_HERSHEY_SIMPLEX,
                'scale': 0.8,
                'color': (255, 0, 0),
                'thickness': 2,
            }
        )
    display_data['window_name'] = "QR Code Display"
    return display_data


# ----------------------------------------------------------------
# Example 2: Constantly display the computed mean HCL values at a fixed location.
# ----------------------------------------------------------------
def compute_display_data_example2(detection_result, frame):
    display_data = {}
    if detection_result is not None:
        pts = detection_result['points'][0].astype(int)
        x, y, w, h = cv2.boundingRect(pts.reshape((-1, 1, 2)))
        roi = frame[y : y + h, x : x + w]
        if roi.size > 0:
            lab_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
            # Convert L from [0, 255] to [0, 100]
            L_channel = lab_roi[:, :, 0] * (100.0 / 255.0)
            # a and b channels are offset by 128 in OpenCV's LAB
            a_channel = lab_roi[:, :, 1] - 128.0
            b_channel = lab_roi[:, :, 2] - 128.0
            hue = (np.degrees(np.arctan2(b_channel, a_channel)) + 360) % 360
            chroma = np.sqrt(a_channel**2 + b_channel**2)
            mean_L = np.mean(L_channel)
            mean_H = np.mean(hue)
            mean_C = np.mean(chroma)
            # Use a fixed-width format to ease visual tracking
            text = f"H: {mean_H:6.2f}  C: {mean_C:6.2f}  L: {mean_L:6.2f}"
            # Fixed display location (e.g., top-left corner)
            text_position = (20, 30)
            display_data.setdefault('texts', []).append(
                {
                    'text': text,
                    'position': text_position,
                    'font': cv2.FONT_HERSHEY_SIMPLEX,
                    'scale': 1.5,
                    'color': (0, 0, 255),
                    'thickness': 2,
                }
            )
    display_data['window_name'] = "Color Values Display"
    return display_data


# ----------------------------------------------------------------
# Example launchers
# ----------------------------------------------------------------
def run_example1(source=0):
    """
    Runs the video pipeline using Example 1:
    Display the QR code's bounding rectangle and the text it encodes.
    """
    qr_detector = make_qr_detector()
    run_video_pipeline(
        qr_detector, compute_display_data_example1, default_displayer, source
    )


def run_example2(source=0):
    """
    Runs the video pipeline using Example 2:
    Constantly display the computed mean HCL values at a fixed location.
    """
    qr_detector = make_qr_detector()
    run_video_pipeline(
        qr_detector, compute_display_data_example2, default_displayer, source
    )


if __name__ == "__main__":
    # Uncomment one of the following to run the desired example.
    # run_example1()
    run_example2()
    pass

# import cv2
# import numpy as np

# # Use the proper VideoCapture source.
# # If your iPhone is exposed as a webcam (e.g., via Continuity Camera or a third-party app),
# # you might be able to simply use device index 0 or 1.
# # Alternatively, if your phone streams video over IP, use the appropriate URL.
# cap = cv2.VideoCapture(0)

# # Create an instance of the QR code detector
# detector = cv2.QRCodeDetector()

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break

#     # Detect and decode the QR code in the frame
#     # data: decoded text (if any), points: corner points of the QR code
#     data, points, _ = detector.detectAndDecode(frame)

#     if points is not None and data:
#         # points is a 4x1x2 array, so reshape it to a simple 4x2 array
#         pts = points[0].astype(int)
#         # Draw a green polygon around the detected QR code
#         cv2.polylines(frame, [pts.reshape((-1, 1, 2))], isClosed=True, color=(0, 255, 0), thickness=2)

#         # Compute an axis-aligned bounding rectangle around the QR code
#         x, y, w, h = cv2.boundingRect(pts.reshape((-1, 1, 2)))
#         roi = frame[y:y+h, x:x+w]

#         # Convert the ROI from BGR to LAB color space
#         # Note: OpenCV’s LAB has L scaled to [0,255]. We convert L to [0,100]
#         lab_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
#         L_channel = lab_roi[:, :, 0] * (100.0 / 255.0)
#         # In OpenCV’s LAB, the a and b channels are offset by 128
#         a_channel = lab_roi[:, :, 1] - 128.0
#         b_channel = lab_roi[:, :, 2] - 128.0

#         # Compute hue (in degrees) and chroma for each pixel.
#         # Hue is computed using arctan2(b, a) and normalized to [0,360)
#         hue = (np.degrees(np.arctan2(b_channel, a_channel)) + 360) % 360
#         chroma = np.sqrt(a_channel**2 + b_channel**2)

#         # Calculate mean values over the ROI
#         mean_L = np.mean(L_channel)
#         mean_H = np.mean(hue)
#         mean_C = np.mean(chroma)

#         # Prepare text to overlay on the frame
#         text = f"Mean HCL: H: {mean_H:.2f}, C: {mean_C:.2f}, L: {mean_L:.2f}"
#         # Put the text slightly above the bounding rectangle
#         cv2.putText(frame, text, (x, max(y-10, 20)), cv2.FONT_HERSHEY_SIMPLEX,
#                     0.6, (255, 0, 0), 2)

#     # Show the frame in a window
#     cv2.imshow("iPhone Camera", frame)
#     key = cv2.waitKey(1)
#     # Press 'q' to quit the loop
#     if key & 0xFF == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()
