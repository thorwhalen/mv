"""Live QR code detection and decoding"""


def dotpath_to_pyobj(dotpath: str):
    """
    Convert a dotpath (e.g., "a.b.c") to a Python object (e.g., a.b.c).

    Args:
        dotpath (str): The dotpath string to convert.

    Returns:
        object: The Python object corresponding to the dotpath.

    Raises:
        ValueError: If the dotpath is empty or invalid.
        ImportError: If the module cannot be imported.
        AttributeError: If the attribute cannot be found in the module.
    """
    import importlib

    if not dotpath or not isinstance(dotpath, str):
        raise ValueError("dotpath must be a non-empty string")

    parts = dotpath.split('.')
    if not parts:
        raise ValueError(f"Invalid dotpath: {dotpath}")

    # Handle module import
    module_name = parts[0]
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        raise ImportError(f"Could not import module: {module_name}")

    # Handle remainder of the path
    obj = module
    for part in parts[1:]:
        try:
            obj = getattr(obj, part)
        except AttributeError:
            raise AttributeError(
                f"'{type(obj).__name__}' object has no attribute '{part}'"
            )

    return obj


def create_qr_code(
    data,
    *,
    fill_color='black',
    back_color='white',
    box_size=10,
    border=4,
    **extra_qrcode_kwargs,
):
    """
    Generate a QR code image for a given string with customizable colors and dimensions.

    Parameters:
        data (str): The string to encode into the QR code.
        fill_color (str, optional): Color of the QR code modules. Defaults to 'black'.
        back_color (str, optional): Color of the background. Defaults to 'white'.
        box_size (int, optional): Size of each box in pixels. Defaults to 10.
        border (int, optional): Width of the border (in boxes). Defaults to 4.
        **extra_qrcode_kwargs: Additional keyword arguments for the qrcode.QRCode constructor.

    Returns:
        PIL.Image.Image: The generated QR code image.

    Examples:

    >>> qr_img = create_qr_code("https://www.example.com")  # doctest: +SKIP
    >>> qr_img.size  # doctest: +SKIP
    (410, 410)
    """
    import qrcode  # pip install qrcode[pil]

    qr = qrcode.QRCode(box_size=box_size, border=border, **extra_qrcode_kwargs)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color)
    return img


def grid_image(
    imgs, *, n_rows=None, n_cols=1, v_padding=0, h_padding=0, convert_to_rgb=True
):
    """
    Create a grid of images from a list of images.

    Note: Requires PIL

    Args:
        imgs (list of PIL.Image.Image): List of images to arrange in a grid.
        n_rows (int, optional): Number of rows in the grid. If None, computed from n_cols and len(imgs).
        n_cols (int, optional): Number of columns in the grid. Default is 1. If None, computed from n_rows and len(imgs).
        v_padding (int): Vertical padding between images in pixels. Default is 0.
        h_padding (int): Horizontal padding between images in pixels. Default is 0.
        convert_to_rgb (bool): If True, convert images to RGB mode. Default is True.

    Returns:
        PIL.Image.Image: A new image with all input images arranged in a grid.

    Raises:
        ValueError: If `imgs` is empty or both `n_rows` and `n_cols` are None.

    Examples:

    >>> from PIL import Image
    >>> img1 = Image.new('RGB', (100, 100), color='red')
    >>> img2 = Image.new('RGB', (100, 100), color='blue')
    >>> img3 = Image.new('RGB', (100, 100), color='green')
    >>> img4 = Image.new('RGB', (100, 100), color='yellow')
    >>> imgs = [img1, img2, img3, img4]
    >>> grid = grid_image(imgs, n_rows=2, n_cols=2, v_padding=10, h_padding=10)
    >>> grid.size  # Check the size of the resulting grid image
    (220, 220)

    """
    from PIL import Image  # pip install pillow

    if not imgs:
        raise ValueError("The img list is empty.")

    # Determine grid dimensions
    num_imgs = len(imgs)
    if n_rows is None and n_cols is None:
        raise ValueError("At least one of n_rows or n_cols must be specified.")

    if n_rows is None:
        n_rows = -(-num_imgs // n_cols)  # Ceiling division
    elif n_cols is None:
        n_cols = -(-num_imgs // n_rows)  # Ceiling division

    if convert_to_rgb:
        # Convert images to RGB to avoid issues with differing modes
        imgs = [img.convert("RGB") for img in imgs]

    # Get individual image dimensions (assumes all images are the same size)
    img_width, img_height = imgs[0].size

    # Calculate the size of the grid image
    grid_width = n_cols * img_width + (n_cols - 1) * h_padding
    grid_height = n_rows * img_height + (n_rows - 1) * v_padding

    # Create a blank image to hold the grid
    grid_img = Image.new('RGB', (grid_width, grid_height), color=(255, 255, 255))

    # Paste images onto the grid
    for idx, img in enumerate(imgs):
        row, col = divmod(idx, n_cols)
        x = col * (img_width + h_padding)
        y = row * (img_height + v_padding)
        grid_img.paste(img, (x, y))

    return grid_img


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


import numpy as np


def compute_display_data_example3(detection_result, frame):
    """
    Example 3: Always display the mean HCL values computed from the entire frame.
    The values are rendered as a table in the top‐left corner, with fixed-width formatting.
    """
    # Convert the entire frame from BGR to LAB.
    lab_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.float32)
    # Scale L from [0,255] to [0,100].
    L_channel = lab_frame[:, :, 0] * (100.0 / 255.0)
    # a and b channels are offset by 128 in OpenCV's LAB.
    a_channel = lab_frame[:, :, 1] - 128.0
    b_channel = lab_frame[:, :, 2] - 128.0

    # Compute hue in degrees and chroma.
    hue = (np.degrees(np.arctan2(b_channel, a_channel)) + 360) % 360
    chroma = np.sqrt(a_channel**2 + b_channel**2)

    # Compute mean values.
    mean_H = np.mean(hue)
    mean_C = np.mean(chroma)
    mean_L = np.mean(L_channel)

    # Prepare text overlays in a table-like format.
    texts = []
    # Fixed positions for each row (adjust Y positions as needed).
    texts.append(
        {
            'text': f"H: {mean_H:6.2f}",
            'position': (20, 30),
            'font': cv2.FONT_HERSHEY_SIMPLEX,
            'scale': 1.0,
            'color': (0, 255, 0),
            'thickness': 2,
        }
    )
    texts.append(
        {
            'text': f"C: {mean_C:6.2f}",
            'position': (20, 60),
            'font': cv2.FONT_HERSHEY_SIMPLEX,
            'scale': 1.0,
            'color': (0, 255, 0),
            'thickness': 2,
        }
    )
    texts.append(
        {
            'text': f"L: {mean_L:6.2f}",
            'position': (20, 90),
            'font': cv2.FONT_HERSHEY_SIMPLEX,
            'scale': 1.0,
            'color': (0, 255, 0),
            'thickness': 2,
        }
    )

    return {'texts': texts, 'window_name': "HCL Table Display"}


def compute_display_data_example4(detection_result, frame):
    """
    Example 4: Display the mean HCL values (computed from the QR code region)
    and the decoded QR text in a table. The overlay is only updated if a QR code
    is detected (or was recently detected).
    """
    display_data = {}
    if detection_result is not None:
        # Use the bounding rectangle from the detected QR code.
        pts = detection_result['points'][0].astype(int)
        x, y, w, h = cv2.boundingRect(pts.reshape((-1, 1, 2)))
        roi = frame[y : y + h, x : x + w]
        if roi.size > 0:
            lab_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
            L_channel = lab_roi[:, :, 0] * (100.0 / 255.0)
            a_channel = lab_roi[:, :, 1] - 128.0
            b_channel = lab_roi[:, :, 2] - 128.0

            hue = (np.degrees(np.arctan2(b_channel, a_channel)) + 360) % 360
            chroma = np.sqrt(a_channel**2 + b_channel**2)

            mean_H = np.mean(hue)
            mean_C = np.mean(chroma)
            mean_L = np.mean(L_channel)

            texts = []
            # Display each value in a fixed row (e.g., rows 1-3) with fixed-width formatting.
            texts.append(
                {
                    'text': f"H: {mean_H:6.2f}",
                    'position': (20, 30),
                    'font': cv2.FONT_HERSHEY_SIMPLEX,
                    'scale': 1.0,
                    'color': (0, 255, 255),
                    'thickness': 2,
                }
            )
            texts.append(
                {
                    'text': f"C: {mean_C:6.2f}",
                    'position': (20, 60),
                    'font': cv2.FONT_HERSHEY_SIMPLEX,
                    'scale': 1.0,
                    'color': (0, 255, 255),
                    'thickness': 2,
                }
            )
            texts.append(
                {
                    'text': f"L: {mean_L:6.2f}",
                    'position': (20, 90),
                    'font': cv2.FONT_HERSHEY_SIMPLEX,
                    'scale': 1.0,
                    'color': (0, 255, 255),
                    'thickness': 2,
                }
            )
            # Add a fourth row for the decoded QR text.
            texts.append(
                {
                    'text': f"QR: {detection_result['data']}",
                    'position': (20, 120),
                    'font': cv2.FONT_HERSHEY_SIMPLEX,
                    'scale': 1.0,
                    'color': (0, 255, 255),
                    'thickness': 2,
                }
            )

            display_data = {'texts': texts, 'window_name': "QR HCL Table Display"}
    # If no QR is detected, return an empty dict; this lets the overlay manager
    # continue displaying previous overlays until they time out.
    return display_data


# ----------------------------------------------------------------
# Example launchers
# ----------------------------------------------------------------
from typing import Callable

DFLT_SOURCE = 0


def run_example_with_qr_detector(
    display_data_func: Callable = None, source: int = DFLT_SOURCE
):

    if display_data_func is None:
        raise ValueError(
            "display_data_func must be provided. Use a function, int or a string "
            "representing the function name."
        )
    if (
        isinstance(display_data_func, int)
        or isinstance(display_data_func, str)
        and str.isnumeric(display_data_func)
    ):
        display_data_func = f"compute_display_data_example{display_data_func}"
    if isinstance(display_data_func, str):
        if '.' in display_data_func:
            # If the string is a dotpath, convert it to a Python object.
            display_data_func = dotpath_to_pyobj(display_data_func)
        else:
            global_vars = globals()
            display_data_func = global_vars.get(display_data_func)

    qr_detector = make_qr_detector()
    run_video_pipeline(qr_detector, display_data_func, default_displayer, source)


if __name__ == "__main__":
    import argh

    argh.dispatch_command(
        run_example_with_qr_detector,
    )
    # Uncomment one of the following to run the desired example.
    # src_index = 1
    # example_index = 4

    # run_example_with_qr_detector(
    #     f"compute_display_data_example{example_index}", src_index
    # )
    # run_example1(src_index)
    # run_example2(src_index)
