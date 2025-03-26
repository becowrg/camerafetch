import cv2
import os
import argparse
from natsort import natsorted # Import natsorted for natural sorting

def create_timelapse(image_folder, output_file, fps, image_ext):
    """
    Creates a timelapse video from images in a specified folder.

    Args:
        image_folder (str): Path to the directory containing the images.
        output_file (str): Path and filename for the output video (e.g., 'timelapse.mp4').
        fps (int): Frames per second for the output video.
        image_ext (str): The file extension of the images (e.g., '.jpg', '.png').
                         Include the dot.
    """
    print(f"--- Timelapse Creation Started ---")
    print(f"Image Folder: {image_folder}")
    print(f"Output File: {output_file}")
    print(f"FPS: {fps}")
    print(f"Image Extension: {image_ext}")

    # Validate image folder
    if not os.path.isdir(image_folder):
        print(f"Error: Image folder '{image_folder}' not found.")
        return

    # Get list of image files
    image_files = [
        f for f in os.listdir(image_folder)
        if os.path.isfile(os.path.join(image_folder, f)) and f.lower().endswith(image_ext.lower())
    ]

    if not image_files:
        print(f"Error: No images with extension '{image_ext}' found in '{image_folder}'.")
        return

    # --- Sort the images ---
    # Use natsorted for robust sorting (handles numbers correctly, e.g., 1, 10, 2 -> 1, 2, 10)
    # If your filenames are perfectly zero-padded (e.g., img001, img002, img010),
    # a simple sorted() might suffice, but natsorted is safer.
    print(f"Found {len(image_files)} images. Sorting...")
    sorted_image_files = natsorted(image_files)
    # print("First 5 sorted files:", sorted_image_files[:5]) # Uncomment to check sorting

    # --- Determine video dimensions from the first image ---
    first_image_path = os.path.join(image_folder, sorted_image_files[0])
    try:
        frame = cv2.imread(first_image_path)
        if frame is None:
            print(f"Error: Could not read the first image: {first_image_path}")
            print("Check if the file is a valid image and OpenCV is installed correctly.")
            return
        height, width, layers = frame.shape
        size = (width, height)
        print(f"Video dimensions (WxH): {width}x{height}")
    except Exception as e:
        print(f"Error reading first image dimensions: {e}")
        return

    # --- Initialize VideoWriter ---
    # Define the codec. Common options:
    # 'mp4v' for .mp4 files (widely compatible)
    # 'XVID' for .avi files
    # 'MJPG' for .avi files (larger file size)
    # Check FourCC website for more: https://www.fourcc.org/codecs.php
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Use 'mp4v' for MP4 output

    try:
        out = cv2.VideoWriter(output_file, fourcc, fps, size)
        if not out.isOpened():
           print(f"Error: Could not open VideoWriter.")
           print("Check codec compatibility, permissions, and output path.")
           return
    except Exception as e:
        print(f"Error initializing VideoWriter: {e}")
        return

    print(f"Writing video frames...")
    # --- Loop through images and write frames ---
    total_frames = len(sorted_image_files)
    for i, filename in enumerate(sorted_image_files):
        image_path = os.path.join(image_folder, filename)
        try:
            frame = cv2.imread(image_path)
            if frame is None:
                print(f"Warning: Skipping unreadable image: {filename}")
                continue

            # Optional: Resize frame if dimensions are inconsistent
            # if (frame.shape[1], frame.shape[0]) != size:
            #     print(f"Warning: Resizing frame {filename} from {frame.shape[1]}x{frame.shape[0]} to {size[0]}x{size[1]}")
            #     frame = cv2.resize(frame, size)

            out.write(frame)

            # Print progress
            print(f"\rProgress: {i + 1}/{total_frames} frames written", end="")

        except Exception as e:
            print(f"\nError processing image {filename}: {e}")
            continue # Skip to the next image

    # Release the VideoWriter
    out.release()
    print(f"\n--- Timelapse Creation Finished ---")
    print(f"Video saved as: {output_file}")

# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a timelapse video from a sequence of images.")
    parser.add_argument("image_folder", help="Path to the folder containing the images.")
    parser.add_argument("-o", "--output", default="timelapse.mp4", help="Output video file name (e.g., timelapse.mp4). Default: timelapse.mp4")
    parser.add_argument("-fps", "--framerate", type=int, default=24, help="Frames per second for the output video. Default: 24")
    parser.add_argument("-ext", "--extension", default=".jpg", help="Image file extension (including the dot, e.g., .jpg, .png). Default: .jpg")

    args = parser.parse_args()

    create_timelapse(args.image_folder, args.output, args.framerate, args.extension)
