# 🎙️ Automated Podcast Transcription & Topic Segmentation

### _Infosys Springboard — Speech + NLP Internship Project_

---

## ⭐ **Project Introduction**

Podcasts and long speech recordings need:
✔ Automatic Speech Recognition (ASR)  
✔ Topic Segmentation  
✔ Keyword Extraction  
✔ Navigation Interface

However, raw speech audio is **not directly usable** because of:

- Background noise
- Variable loudness
- Stereo channels
- Wrong sampling rates
- Very long duration

So, **Milestone-1 focuses on Dataset Preprocessing** which is essential before Whisper ASR and NLP tasks.

---

## 🎧 **Dataset Source (Audio Used for Milestone-1)**

For Milestone-1, we used **TED Talk audio files** as podcast-style speech data.

### **📌 Source Platform**

**Kaggle**

### **📌 Dataset Name**

**TED-LIUM Release 3 (TED Talk Speech Audio)**

### **📌 Why This Dataset Was Chosen**

TED speech matches podcast characteristics because:
✔ Natural spoken English  
✔ Long-form talk format (3–30+ mins)  
✔ Clear audio quality  
✔ Suitable for ASR training

### **📌 Dataset Format**

The dataset contains:

- `.sph` or `.wav` audio
- Long speech duration (similar to podcasts)

### **📌 Dataset Size**

Approx:

- **2600+ audio files**
- **~35GB raw + converted files**

### **📌 Podcast Equivalence Note**

While TED Talks are not Spotify podcasts, they are ideal for:

- Transcription
- Noise removal
- Segmentation
- Keyword extraction

So they satisfy mentor requirement for **speech-based dataset**.

---

## 🎯 **Milestone-1 Objective**

> **Prepare speech audio data for ASR using preprocessing pipeline.**

Our Milestone-1 tasks include:

1. Audio Conversion
2. Resampling
3. Mono Channel Conversion
4. Noise Reduction
5. Loudness Normalization
6. Silence Trimming
7. Chunking into 20–30 sec segments (optional)

---

## ⚙️ **Audio Preprocessing Pipeline Implemented**

| Stage | Task                   | Status         |
| ----- | ---------------------- | -------------- |
| 1     | Convert MP3 → WAV      | ✔ Completed    |
| 2     | Resample → 16 KHz      | ✔ Completed    |
| 3     | Stereo → Mono          | ✔ Completed    |
| 4     | Noise Reduction        | ✔ Completed    |
| 5     | Loudness Normalization | ✔ Completed    |
| 6     | Silence Trimming       | ✔ Completed    |
| 7     | Chunking (20–30s)      | 🔁 In Progress |

---

## 📂 **Organized Dataset Structure**

After preprocessing, the project tree looks like:

```
INFOSYS_SPRINGBOARD/
│
├── data/
│   ├── raw/        ➜ Original downloaded audio
│   ├── wav/        ➜ Converted WAV format
│   ├── clean/      ➜ Noise reduced + normalized audio
│   └── chunks/     ➜ 20–30s segmented audio
│
├── scripts/
│   ├── convert_to_wav.py
│   ├── preprocess_audio.py
│   └── chunk_clean.py
│
├── outputs/        ➜ transcripts (future)
├── requirements.txt
├── .gitignore
└── README.md
```

This structure shows **clarity, reproducibility, and future scalability**.

---

## 🧪 **Script Descriptions**

### `convert_to_wav.py`

✔ Converts MP3 to WAV
✔ Saves to `data/wav/`

### `preprocess_audio.py`

Performs:
✔ Resample to 16 KHz  
✔ Mono conversion  
✔ Noise reduction  
✔ Normalization  
✔ Silence trimming

Outputs to `data/clean/`

### `chunk_clean.py` (Upcoming)

✔ Splits long clean audio into 20–30 sec segments  
Outputs to `data/chunks/`

---

## 📦 **Installation & Usage Instructions**

### **Install Dependencies**

```bash
pip install -r requirements.txt
```

### **Convert Audio**

```bash
python scripts/convert_to_wav.py
```

### **Preprocess Audio**

```bash
python scripts/preprocess_audio.py
```

### **Chunking (Optional for M1)**

```bash
python scripts/chunk_clean.py
```

---

## 🧾 **Milestone-1 Deliverables**

✔ TED Podcast-Style Dataset Selected  
✔ Audio Converted to WAV  
✔ Resampled to 16 KHz  
✔ Converted to Mono  
✔ Noise Reduced  
✔ Normalized  
✔ Silence Trimmed  
✔ Dataset Structured  
🔁 Chunking (optional but planned)

---

## 🚀 **Future Milestones**

### 🟩 **Milestone-2**

- Whisper ASR Transcription
- Timestamp alignment
- Text cleaning

### 🟦 **Milestone-3**

- Topic segmentation
- Keyword extraction (RAKE/YAKE/KeyBERT)
- UI Navigation (Streamlit/Flask)

---

## 📚 **Tech Stack & Libraries**

- Python
- Librosa
- NumPy
- SoundFile
- Noisereduce
- Pydub
- Whisper (planned)
- Streamlit (planned)

---
