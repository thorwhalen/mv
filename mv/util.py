"""Utility functions for the mv package."""

from typing import Literal, Iterable
import cv2


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

CameraProperty = Literal[tuple(camera_properties.keys())]
DFLT_CAMERA_PROPERTIES = ('frame_width', 'frame_height', 'fps', 'zoom', 'backend')

def scan_for_openable_video_indices(
        properties: Iterable[CameraProperty] = DFLT_CAMERA_PROPERTIES,
        *, 
        max_indices: int = 5, 
        verbose: bool = False
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

