import instaloader
import os
from pathlib import Path
import getpass
import time
import shutil
import ffmpeg
from datetime import datetime
import subprocess
import sys
from colorama import init, Fore, Style
import tqdm

# Initialize colorama
init()

def print_header():
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.CYAN}Instagram Reel Downloader and Combiner")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")

def print_success(message):
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.BLUE}{message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

def clean_downloads_folder():
    download_dir = Path("downloads")
    if download_dir.exists():
        print_info("Cleaning downloads folder...")
        for item in download_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print_success("Downloads folder cleaned.")
    else:
        download_dir.mkdir()
        print_success("Created downloads folder.")

def login_to_instagram():
    L = instaloader.Instaloader()
    session_file = Path("instagram_session")
    
    try:
        # Try to load session from file
        if session_file.exists():
            L.load_session_from_file("instagram_session")
            print_success("Successfully loaded existing session.")
            return L
    except Exception as e:
        print_warning("Session file invalid or expired. Please log in again.")
    
    print_info("Please log in to Instagram.")
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            username = input(f"{Fore.CYAN}Enter your Instagram username: {Style.RESET_ALL}")
            password = getpass.getpass(f"{Fore.CYAN}Enter your Instagram password: {Style.RESET_ALL}")
            
            # Add a small delay before login attempt
            time.sleep(1)
            
            L.login(username, password)
            # Save session for future use
            L.save_session_to_file("instagram_session")
            print_success("Successfully logged in and saved session.")
            return L
        except instaloader.exceptions.InstaloaderException as e:
            print_error(f"Login attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_attempts - 1:
                print_info("Please try again...")
                time.sleep(2)  # Wait before next attempt
            else:
                print_error("Maximum login attempts reached. Please check your credentials and try again later.")
                return None
        except Exception as e:
            print_error(f"Unexpected error during login: {str(e)}")
            return None
    
    return None

def download_reel(L, reel_url, index, total):
    try:
        # Extract the shortcode from the URL
        shortcode = reel_url.split("/")[-2]
        
        # Get the post
        time.sleep(2)  # Add delay before post fetch
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Create a downloads directory if it doesn't exist
        download_dir = Path("downloads")
        download_dir.mkdir(exist_ok=True)
        
        # Create a temporary directory for the download
        temp_dir = Path("temp_download")
        temp_dir.mkdir(exist_ok=True)
        
        # Download the post to temporary directory
        L.download_post(post, target=temp_dir)
        
        # Find the MP4 file in the temporary directory
        mp4_files = list(temp_dir.glob("*.mp4"))
        if mp4_files:
            # Get the first MP4 file (there should only be one)
            mp4_file = mp4_files[0]
            # Create a filename based on the index
            new_filename = f"{index}.mp4"
            # Move the MP4 file to the downloads directory
            shutil.move(str(mp4_file), str(download_dir / new_filename))
            print_success(f"Downloaded reel {index}/{total} to {download_dir / new_filename}")
            
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
            return True
        else:
            print_error("No MP4 file found in the downloaded content")
            return False
            
    except instaloader.exceptions.InstaloaderException as e:
        if "rate limit" in str(e).lower() or "wait a few minutes" in str(e).lower():
            print_warning("Rate limit reached. Please wait a few minutes before trying again.")
        else:
            print_error(f"Error downloading reel: {str(e)}")
        # Clean up temporary directory if it exists
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False
    except Exception as e:
        print_error(f"Error downloading reel: {str(e)}")
        # Clean up temporary directory if it exists
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return False

def trim_video_if_needed(input_file, max_duration=59):
    try:
        # Get video duration using ffprobe
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"Error getting video duration: {result.stderr}")
            return False
            
        duration = float(result.stdout.strip())
        
        if duration <= max_duration:
            print_info(f"Video duration ({duration:.2f}s) is within limit. No trimming needed.")
            return True
            
        print_warning(f"Video duration ({duration:.2f}s) exceeds {max_duration}s limit. Trimming...")
        
        # Create temporary file for trimmed video
        temp_file = input_file.parent / "temp_trimmed.mp4"
        
        # Trim video using ffmpeg
        cmd = [
            "ffmpeg",
            "-i", str(input_file),
            "-t", str(max_duration),
            "-c", "copy",
            str(temp_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"Error trimming video: {result.stderr}")
            return False
            
        # Replace original file with trimmed version
        input_file.unlink()
        temp_file.rename(input_file)
        
        print_success(f"Successfully trimmed video to {max_duration} seconds.")
        return True
        
    except Exception as e:
        print_error(f"Error in trim_video_if_needed: {str(e)}")
        return False

def join_videos():
    try:
        download_dir = Path("downloads")
        if not download_dir.exists():
            print_error("No downloads directory found.")
            return False
            
        # Get all MP4 files from the downloads directory
        mp4_files = sorted(list(download_dir.glob("*.mp4")))
        if not mp4_files:
            print_error("No MP4 files found in downloads directory.")
            return False
            
        # Check for intro video
        intro_file = Path("intro.mp4")
        if not intro_file.exists():
            print_warning("intro.mp4 not found. Proceeding without intro.")
            intro_files = []
        else:
            print_info("Found intro video. Will add it to the start.")
            intro_files = [intro_file]
            
        print_info(f"Found {len(mp4_files)} videos to join.")
        
        # Use fixed name for combined video
        output_file = download_dir / "combined_video.mp4"
        
        # Build the ffmpeg command
        cmd = ["ffmpeg"]
        
        # Add intro file first if it exists
        for intro in intro_files:
            cmd.extend(["-i", str(intro)])
            
        # Add all other input files
        for mp4_file in mp4_files:
            cmd.extend(["-i", str(mp4_file)])
        
        # Build filter complex string
        filter_complex = []
        
        # Process intro video if it exists
        if intro_files:
            filter_complex.append(f"[0:v:0]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];")
            filter_complex.append(f"[0:a:0]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];")
            
        # Process other videos
        for i in range(len(mp4_files)):
            input_index = i + (1 if intro_files else 0)  # Adjust index if intro exists
            filter_complex.append(f"[{input_index}:v:0]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[v{input_index}];")
            filter_complex.append(f"[{input_index}:a:0]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{input_index}];")
        
        # Add concatenation
        total_videos = len(mp4_files) + (1 if intro_files else 0)
        filter_complex.append("".join([f"[v{i}][a{i}]" for i in range(total_videos)]))
        filter_complex.append(f"concat=n={total_videos}:v=1:a=1[outv][outa]")
        
        # Add filter complex and output settings
        cmd.extend([
            "-filter_complex", "".join(filter_complex),
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(output_file)
        ])
        
        print_info("\nJoining videos...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print_error(f"Error during video joining: {result.stderr}")
            return False
            
        print_success(f"\nSuccessfully created combined video: {output_file}")
        
        # Check and trim if needed
        if not trim_video_if_needed(output_file):
            print_error("Failed to trim video if needed.")
            return False
            
        return True
        
    except Exception as e:
        print_error(f"Error joining videos: {str(e)}")
        return False

def read_links_from_file(filename):
    try:
        with open(filename, 'r') as file:
            # Read all lines and strip whitespace
            links = [line.strip() for line in file if line.strip()]
        return links
    except FileNotFoundError:
        print_error(f"Error: File '{filename}' not found.")
        return []
    except Exception as e:
        print_error(f"Error reading file: {str(e)}")
        return []

def main():
    print_header()
    
    # Clean downloads folder at startup
    clean_downloads_folder()
    
    # Login to Instagram first
    L = login_to_instagram()
    if not L:
        print_error("Failed to authenticate with Instagram. Exiting...")
        return
    
    # Get the input file name from user
    input_file = input(f"{Fore.CYAN}Enter the name of the text file containing reel links: {Style.RESET_ALL}").strip()
    
    # Read links from file
    links = read_links_from_file(input_file)
    
    if not links:
        print_error("No valid links found in the file.")
        return
    
    print_info(f"\nFound {len(links)} links to process.")
    
    # Process each link
    successful_downloads = 0
    for i, link in enumerate(links, 1):
        print_info(f"\nProcessing link {i}/{len(links)}")
        if download_reel(L, link, i, len(links)):
            successful_downloads += 1
        time.sleep(5)  # Add delay between downloads
    
    print_info(f"\nDownload complete! Successfully downloaded {successful_downloads} out of {len(links)} reels.")
    
    # Ask if user wants to join the videos
    if successful_downloads > 0:
        join_choice = input(f"\n{Fore.CYAN}Would you like to join all downloaded videos into one? (y/n): {Style.RESET_ALL}").lower()
        if join_choice == 'y':
            join_videos()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print_error(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)
