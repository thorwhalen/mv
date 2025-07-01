"""Utility functions for the mv package."""

from typing import Literal, Iterable
from functools import partial
import cv2
from config2py import (
    get_app_data_folder,
    process_path,
)
import os
import datetime

pkg_name = 'mv'
app_dir = get_app_data_folder(pkg_name, ensure_exists=True)
app_filepath = partial(process_path, ensure_dir_exists=True, rootdir=app_dir)


# Note: Got this list by asking AI to give me the twenty most important properties,
# with a short description of each, from the list I provided it by running the following code:
# list(filter(lambda x: x.startswith('CAP_PROP_'), dir(cv2)))
camera_properties = {
    "frame_width": "Width of the frames in the video stream.",
    "frame_height": "Height of the frames in the video stream.",
    "fps": "Frame rate of the video capture.",
    "brightness": "Brightness of the image (only for cameras).",
    "contrast": "Contrast of the image (only for cameras).",
    "saturation": "Saturation of the image (only for cameras).",
    "hue": "Hue of the image (only for cameras).",
    "gain": "Gain of the image (only for cameras).",
    "exposure": "Exposure time of the camera (only for cameras).",
    "focus": "Focus setting of the camera (only for cameras).",
    "auto_exposure": "Auto exposure setting (0=auto, 1=manual).",
    "auto_wb": "Enable/disable auto white balance.",
    "wb_temperature": "White balance temperature (if auto white balance is off).",
    "zoom": "Camera zoom level.",
    "pan": "Pan (horizontal movement) of the camera.",
    "tilt": "Tilt (vertical movement) of the camera.",
    "roll": "Roll angle of the camera.",
    "sharpness": "Sharpness of the image.",
    "gamma": "Gamma correction value.",
    "backend": "Current backend used for video capture.",
}

CameraProperty = Literal[
    "frame_width",
    "frame_height",
    "fps",
    "brightness",
    "contrast",
    "saturation",
    "hue",
    "gain",
    "exposure",
    "focus",
    "auto_exposure",
    "auto_wb",
    "wb_temperature",
    "zoom",
    "pan",
    "tilt",
    "roll",
    "sharpness",
    "gamma",
    "backend",
]
DFLT_CAMERA_PROPERTIES = ('frame_width', 'frame_height', 'fps', 'zoom', 'backend')


def scan_for_openable_video_indices(
    properties: Iterable[CameraProperty] = DFLT_CAMERA_PROPERTIES,
    *,
    max_indices: int = 5,
    verbose: bool = False,
):
    """
    Scans for video capture devices by trying indices 0 to max_indices-1.

    Parameters:
        max_indices (int): The maximum number of indices to test.
        verbose (bool): If True, print status messages.

    Returns:
        List[dict]: A list of dictionaries, each containing information
                    about an openable video source.
                    For example:
                      {'index': 0,
                       'frame_width': 640.0,
                       'frame_height': 480.0,
                       'fps': 30.0}
                    If no additional information is available,
                    the dict will contain the index and any properties that could be queried.
    """
    video_sources = []

    for i in range(max_indices):
        if verbose:
            print(f"Testing video source index: {i}")

        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            info = {'index': i}
            for prop in properties:
                prop_cv2_name = cv2.__dict__[f'CAP_PROP_{prop.upper()}']
                value = cap.get(prop_cv2_name)
                if value is not None:
                    info[prop] = value

            yield info
            if verbose:
                print(f"Index {i} is open: {info}")
            cap.release()

    return video_sources


def record_video_from_camera(
    filename: str = None,
    source: int = 0,
    fourcc: str = "mp4v",
    fps: float = 20.0,
    frame_size: tuple = None,
    show_window: bool = True,
    window_name: str = "Recording (ESC or Ctrl+C to stop)",
):
    """
    Record video from the camera and save to a file.

    Args:
        filename: Output video file path. If None, auto-generates a timestamped filename.
        source: Camera index (default 0).
        fourcc: FourCC code for video encoding (default 'mp4v' for .mp4).
        fps: Frames per second.
        frame_size: (width, height). If None, uses camera's default.
        show_window: Whether to display a live preview window.
        window_name: Name of the preview window.

    Stops recording on KeyboardInterrupt, ESC key, or error.
    """
    import cv2

    # Auto-generate filename if not provided
    if filename is None:
        now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"video-{now}.mp4"
        filename = os.path.abspath(filename)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera (index {source})")

    # Get frame size if not provided
    if frame_size is None:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_size = (width, height)

    # Define the codec and create VideoWriter object
    fourcc_code = cv2.VideoWriter_fourcc(*fourcc)
    out = cv2.VideoWriter(filename, fourcc_code, fps, frame_size)

    print(f"Recording started. Saving to: {filename}")
    print("Press ESC in the window or Ctrl+C in the terminal to stop.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame. Exiting.")
                break
            out.write(frame)
            if show_window:
                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1)
                if key == 27:  # ESC key
                    print("ESC pressed. Exiting.")
                    break
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Exiting.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        out.release()
        if show_window:
            cv2.destroyAllWindows()
        print(f"Recording stopped. Video saved to: {filename}")
        return filename
