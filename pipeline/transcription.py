import whisper

# Load the model globally so it stays in memory across requests
# Using 'base' as requested for performance/portfolio balance
print("Loading Whisper model (base)...")
model = whisper.load_model("base")

def run_transcription(audio_path):
    """
    Transcribe the given audio file using Whisper.
    Returns a list of dicts with 'start', 'end', and 'text'.
    """
    print(f"Transcribing {audio_path}...")
    result = model.transcribe(audio_path, language="en", verbose=False)
    
    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip()
        })
    
    return segments
