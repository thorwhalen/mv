# mv

Live video ML pipeline toolbox.

To install:	```pip install mv```

Make it easy to build components for live video processing, to compute video features, 
run ML models, and display results. 


# Examples

## Reverse video

```py
import mv.wip.video_transforms as vt 
reversed_video_path = vt.reverse_video_w_moviepy("input.mp4", "output.mp4")
```

or, with only builtins (but you need `ffmpeg` installed on your system)

```py
import mv.wip.video_transforms as vt 
reversed_video_path = vt.reverse_video_w_ffmpeg("input.mp4", "output.mp4")
```

## OverlayManager: Manages persistent overlays on video frames.

To see examples of use, run `mv.wip.live_qr_codes.run_example_with_qr_detector(...)` or 
from terminal, `python ...path_to__live_qr_codes__module`

# More examples (for images)

## Make qr code

```py
>>> qr_img = create_qr_code("https://www.example.com")  # doctest: +SKIP
>>> qr_img.size  # doctest: +SKIP
(410, 410)
```

## grid_image: Create a grid of images from a list of images.

```py
>>> from PIL import Image
>>> img1 = Image.new('RGB', (100, 100), color='red')
>>> img2 = Image.new('RGB', (100, 100), color='blue')
>>> img3 = Image.new('RGB', (100, 100), color='green')
>>> img4 = Image.new('RGB', (100, 100), color='yellow')
>>> imgs = [img1, img2, img3, img4]
>>> grid = grid_image(imgs, n_rows=2, n_cols=2, v_padding=10, h_padding=10)
>>> grid.size  # Check the size of the resulting grid image
(220, 220)
```
