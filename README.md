# Instagram Reel Downloader and Combiner

A Python application that downloads Instagram reels and combines them into a single video, with support for adding an intro video and maintaining a 59-second limit.

## Features

- Download multiple Instagram reels from a text file
- Add an intro video to the start of the combined video
- Automatically trim videos to 59 seconds if needed
- Beautiful terminal UI with color-coded messages
- Progress tracking for downloads
- Session management for Instagram login

## Requirements

- Python 3.8 or higher
- FFmpeg installed on your system
- Instagram account

## Installation

1. Clone or download this repository
2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Make sure FFmpeg is installed on your system:
   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

## Usage

1. Create a text file containing Instagram reel URLs (one per line)
2. Place your intro video (if any) as `intro.mp4` in the same directory as the script
3. Run the script:
   ```
   python main.py
   ```
4. Follow the prompts to:
   - Log in to Instagram
   - Enter the name of your text file containing reel URLs
   - Choose whether to join the videos

## Notes

- The program will create a `downloads` folder for storing downloaded videos
- The final combined video will be saved as `combined_video.mp4` in the downloads folder
- Rate limiting may occur if downloading too many videos at once

## Troubleshooting

- If you get login errors, delete the `instagram_session` file and try again
- Make sure FFmpeg is properly installed and accessible from the command line
- Check that your text file contains valid Instagram reel URLs
- Ensure you have sufficient disk space for the downloads 