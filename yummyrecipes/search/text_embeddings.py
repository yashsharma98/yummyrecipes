import threading

model = None
model_lock = threading.Lock()


def load_model():
    global model
    
    if model is None:
        with model_lock:
            if model is None:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


def recipe_embedding(text):
    model = load_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()