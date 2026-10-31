import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

# Load globally to avoid reloading on every request
print("Loading SentenceTransformer (all-MiniLM-L6-v2)...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def run_segmentation(transcript_segments, threshold=0.75):
    """
    Cluster short transcript segments into broader topics based on semantic similarity.
    Returns a list of grouped chunks (topics), where each chunk contains:
    - start: float
    - end: float
    - text: str
    """
    if not transcript_segments:
        return []
    
    texts = [seg['text'] for seg in transcript_segments]
    
    # Generate embeddings
    embeddings = embedder.encode(texts)
    
    # If we have very few segments, just group them all
    if len(texts) < 3:
        start_time = transcript_segments[0]['start']
        end_time = transcript_segments[-1]['end']
        combined_text = " ".join(texts)
        return [{"start": start_time, "end": end_time, "text": combined_text}]

    # Agglomerative clustering (no fixed number of clusters, bounded by distance threshold)
    clustering_model = AgglomerativeClustering(
        n_clusters=None, 
        distance_threshold=threshold, 
        linkage='ward'
    )
    
    clustering_model.fit(embeddings)
    cluster_labels = clustering_model.labels_

    # Since transcript is sequential, we enforce chronological chunks by merging 
    # contiguous segments that share the same topic cluster.
    
    grouped_topics = []
    current_cluster = cluster_labels[0]
    current_chunk = [transcript_segments[0]]
    
    for i in range(1, len(transcript_segments)):
        if cluster_labels[i] == current_cluster:
            # Same topic, append to current chunk
            current_chunk.append(transcript_segments[i])
        else:
            # Topic shifted
            grouped_topics.append({
                "start": current_chunk[0]['start'],
                "end": current_chunk[-1]['end'],
                "text": " ".join([c['text'] for c in current_chunk])
            })
            current_cluster = cluster_labels[i]
            current_chunk = [transcript_segments[i]]
            
    # Add the last chunk
    if current_chunk:
        grouped_topics.append({
            "start": current_chunk[0]['start'],
            "end": current_chunk[-1]['end'],
            "text": " ".join([c['text'] for c in current_chunk])
        })
        
    return grouped_topics
