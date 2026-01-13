🎙 Automated Podcast Transcription & Topic Segmentation
Infosys Springboard — AI Project (Milestone-1 Submission)
📌 Objective

Build an AI system that can:

Convert podcast audio to text using ASR (Speech-to-Text)

Segment transcripts into topical sections

Extract summaries & keywords

📁 Dataset Description

We used TED Talks Podcast Dataset consisting of:

Audio format: MP3 → WAV

Sampling rate: 44.1 kHz (original) → 16 kHz (converted)

Channels: Stereo → Mono

Duration: 2,681 podcast clips

🛠 Preprocessing Pipeline (Completed in Milestone-1)

✔ Convert MP3 → WAV
✔ Resample to 16 kHz
✔ Convert to Mono
✔ Apply Noise Reduction
✔ Normalize Loudness
✔ Trim Silence (optional applied)
✔ Organize dataset folder structure

##📂 Project Structure
├── data/
│   ├── raw/       (original MP3)
│   ├── wav/       (converted WAV)
│   ├── clean/     (audio after preprocessing)
│   └── chunks/    (to be used in Milestone-2)
├── scripts/
│   ├── convert_to_wav.py
│   ├── preprocess_audio.py
│   └── chunk_clean.py
├── outputs/
├── README.md
├── requirements.txt
└── .gitignore
```
🧩 Technologies & Libraries

Python 3.10

librosa

soundfile

noisereduce

numpy

pydub

openai-whisper (for speech-to-text in milestone-2)

tqdm
