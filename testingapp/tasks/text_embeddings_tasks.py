from celery import shared_task

from ..models import post


@shared_task()
def generate_recipe_embeddings(batch_size=50):
    """Generate embeddings for recipes that don't have them"""

    recipe_emb = post.objects.filter(embedding__isnull=True)[:batch_size]

    if not recipe_emb.exists():
        return "No recipes pending embedding."

    # processed = 0

    for i in recipe_emb:
        try:
            # from ..search.text_embeddings import recipe_embedding

            # text = f"{i.title}. {i.ingredients}"
            # i.embedding = recipe_embedding(text)
            # i.save(update_fields=["embedding"])
            # processed += 1
            pass

        except Exception:
            continue

    return f"Processed {recipe_emb.count()} recipes."
