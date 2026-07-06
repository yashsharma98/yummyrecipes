from django.core.cache import cache

CACHE_TTL = 60 * 60 * 6  # 6 hours


def cached_query_embedding(query):
    key = f"query_embedding:{query.lower().strip()}"
    embedding = cache.get(key)

    if embedding is None:
        from .text_embeddings import recipe_embedding

        embedding = recipe_embedding(query)
        cache.set(key, embedding, CACHE_TTL)

    return embedding
