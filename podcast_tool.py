"""
TALK2TOPICS — Standalone Reusable CLI and Library Tool
Convenience entry point for running podcast transcription, segmentation,
summarization, and intelligence analysis from the root directory.
"""
import sys
import os

# Add Infosys_Springboard to path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pipeline.podcast_tool import PodcastProcessor, main

if __name__ == "__main__":
    main()
