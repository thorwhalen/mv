"""A bunch of video transformation tools."""


def reverse_video_w_moviepy(input_path, output_path=None):
    """
    Reverse both video and audio of a video file.

    Parameters:
    input_path (str): Path to the input video file
    output_path (str, optional): Path for the output reversed video file.
                                If not provided, will use the input filename with '_reversed' added.

    Returns:
    str: Path to the reversed video file

    Example:

    ```python
    reversed_video_path = reverse_video_w_moviepy("input.mp4", "output.mp4")
    ```
    """

    from moviepy.video.io.VideoFileClip import VideoFileClip
    import numpy as np
    import os

    # Create output filename if not provided
    if output_path is None:
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_reversed{ext}"

    try:
        # Load the video file
        print(f"Loading video: {input_path}")
        video = VideoFileClip(input_path)

        # The issue with MoviePy 2.1.2 is that some functions have changed
        # We need to create a new clip with a custom make_frame function
        original_duration = video.duration

        # Define a function to get frames in reverse order
        def reverse_frames(t):
            return video.get_frame(original_duration - t)

        # Create a new clip with the same duration but reversed frames
        print("Creating reversed video...")
        from moviepy.video.VideoClip import VideoClip

        reversed_video_clip = VideoClip(
            make_frame=reverse_frames, duration=original_duration
        )

        # For audio, we need to extract it, reverse it, and attach it back
        if video.audio is not None:
            print("Reversing audio...")
            audio_array = video.audio.to_soundarray()
            reversed_audio_array = audio_array[::-1]  # Reverse the audio array

            from moviepy.audio.AudioClip import AudioArrayClip

            reversed_audio = AudioArrayClip(reversed_audio_array, fps=video.audio.fps)
            reversed_video_clip = reversed_video_clip.set_audio(reversed_audio)

        # Write the result to file with the same fps as the original
        print(f"Writing reversed video to: {output_path}")
        reversed_video_clip.write_videofile(output_path, fps=video.fps)

        # Close the clips to free resources
        video.close()

        print("Video reversal complete!")
        return output_path

    except Exception as e:
        print(f"Error reversing video with MoviePy: {str(e)}")
        print("Falling back to FFmpeg method...")
        return reverse_video_ffmpeg(input_path, output_path)


def reverse_video_w_ffmpeg(input_path, output_path=None):
    """
    Reverse both video and audio of a video file using FFmpeg directly.
    This is a more reliable approach that works at a lower level.

    Parameters:
    input_path (str): Path to the input video file
    output_path (str, optional): Path for the output reversed video file.
                               If not provided, will use the input filename with '_reversed' added.

    Returns:
    str: Path to the reversed video file

    Example:

    ```python
    reversed_video_path = reverse_video_w_ffmpeg("input.mp4", "output.mp4")
    ```

    """

    import subprocess
    import os
    import tempfile

    # Create output filename if not provided
    if output_path is None:
        filename, ext = os.path.splitext(input_path)
        output_path = f"{filename}_reversed{ext}"

    try:
        # Create temporary file paths
        temp_dir = tempfile.gettempdir()
        base_name = os.path.basename(input_path).replace(" ", "_")
        temp_video = os.path.join(temp_dir, f"temp_rev_video_{base_name}")
        temp_audio = os.path.join(temp_dir, f"temp_rev_audio_{base_name}.aac")

        print(f"Processing video with FFmpeg: {input_path}")

        # Step 1: Reverse the video stream (without audio)
        print("Reversing video stream...")
        video_cmd = [
            'ffmpeg',
            '-y',
            '-i',
            input_path,
            '-vf',
            'reverse',
            '-an',  # No audio
            '-c:v',
            'libx264',
            '-preset',
            'medium',
            '-crf',
            '22',
            temp_video,
        ]
        print(f"Running command: {' '.join(video_cmd)}")
        subprocess.run(video_cmd, check=True)

        # Check if the video has audio
        has_audio = False
        probe_cmd = [
            'ffprobe',
            '-i',
            input_path,
            '-show_streams',
            '-select_streams',
            'a',
            '-loglevel',
            'error',
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if probe_result.stdout.strip():
            has_audio = True

        if has_audio:
            # Step 2: Extract and reverse the audio stream
            print("Extracting and reversing audio stream...")
            audio_cmd = [
                'ffmpeg',
                '-y',
                '-i',
                input_path,
                '-vn',  # No video
                '-af',
                'areverse',
                '-c:a',
                'aac',
                '-b:a',
                '192k',
                temp_audio,
            ]
            print(f"Running command: {' '.join(audio_cmd)}")
            subprocess.run(audio_cmd, check=True)

            # Step 3: Combine reversed video and audio
            print(f"Combining reversed video and audio to: {output_path}")
            combine_cmd = [
                'ffmpeg',
                '-y',
                '-i',
                temp_video,
                '-i',
                temp_audio,
                '-c:v',
                'copy',  # Copy video stream without re-encoding
                '-c:a',
                'aac',  # Make sure audio is in AAC format
                '-map',
                '0:v:0',
                '-map',
                '1:a:0',  # Map first video stream and first audio stream
                '-shortest',  # Take the shortest of the streams
                output_path,
            ]
            print(f"Running command: {' '.join(combine_cmd)}")
            subprocess.run(combine_cmd, check=True)
        else:
            # If no audio, just rename the temp video to output
            print("No audio detected. Copying video to output.")
            import shutil

            shutil.move(temp_video, output_path)

        # Clean up temporary files
        for file in [temp_video, temp_audio]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    print(f"Could not remove temporary file: {file}")

        print("Video reversal complete!")
        return output_path

    except Exception as e:
        print(f"Error reversing video with FFmpeg: {str(e)}")
        raise


reverse_video = reverse_video_with_ffmpeg = (
    reverse_video_ffmpeg  # Alias for the main function
)
