from celery import shared_task

from ..models import post


@shared_task()
def generate_recipe_embeddings(batch_size=50):
    """Generate embeddings for recipes that are missing them or fails when recipe was saved"""

    recipe_emb = list(post.objects.filter(embedding__isnull=True)[:batch_size])

    if not recipe_emb:
        return "No recipes pending embedding."

    processed = 0

    from ..search.text_embeddings import recipe_embedding

    # embed the recipes which are null
    for i in recipe_emb:
        try:
            text = f"{i.title}. {i.ingredients}"

            i.embedding = recipe_embedding(text)

            i.save(update_fields=["embedding"])
            processed += 1

        except Exception:
            continue

    return f"Processed {processed} recipes."
