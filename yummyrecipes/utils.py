import openai
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from symspellpy import SymSpell

from .models import BlogHistory, post


def summarize_text(text):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=text,
            max_tokens=150,
            temperature=0.4,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error in text summarization: {e}")
        return text


def get_recommendations(recipe_id, num_recommendations=50):
    recipe = post.objects.get(id=recipe_id)

    recipes = list(post.objects.all())

    descriptions = [recipe.content for recipe in recipes]
    ingredients = [recipe.ingredients for recipe in recipes]

    combined_features = [f"{desc} {ingre}" for desc, ingre in zip(descriptions, ingredients)]

    tfidf_vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf_vectorizer.fit_transform(combined_features)

    cosine_similarities = cosine_similarity(tfidf_matrix, tfidf_matrix)

    recipe_index = recipes.index(recipe)

    similarity_scores = cosine_similarities[recipe_index]
    similar_indices = similarity_scores.argsort()[-(num_recommendations + 1) : -1][::-1]

    recommended_recipes = [recipes[int(index)] for index in similar_indices]

    return recommended_recipes


def hex_to_rgba(hex_color, alpha=0.2):
    hex_color = hex_color.strip().lstrip("#")

    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])

    if len(hex_color) != 6:
        return f"rgba(255,255,255,{alpha})"

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return f"rgba(255,255,255,{alpha})"

    return f"rgba({r},{g},{b},{alpha})"


def get_historys_pk(user):
    if not user.is_authenticated:
        return []
    return list(BlogHistory.objects.filter(user=user).values_list("blog_post__pk", flat=True).distinct())


def is_filtering_query(query):
    query = query.lower()

    filter_keywords = [
        "veg",
        "non-veg",
        "vegetarian",
        "nonvegetarian",
        "easy",
        "medium",
        "hard",
        "breakfast",
        "lunch",
        "dinner",
        "snack",
        "under",
        "minutes",
        "ready in",
        "indian",
        "italian",
        "american",
        "recipes",
        "recipe",
        "food",
    ]

    return any(word in query for word in filter_keywords)


sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)


def build_recipe_dictionary():
    for r in post.objects.all():
        text_fields = [
            r.title,
            r.ingredients,
            r.cuisine,
            r.category,
            r.type,
            r.difficulty,
        ]
        for field in text_fields:
            if field:
                for word in field.split():
                    sym_spell.create_dictionary_entry(word.lower(), 1)
    return sym_spell


def is_guest_mode(request):
    guest_user = request.session.get("guest_user")
    is_guest = bool(guest_user and not request.user.is_authenticated)
    return guest_user, is_guest


model = SentenceTransformer("all-MiniLM-L6-v2")


def rebuild_embeddings():
    for p in post.objects.all():
        text = f"{p.title} {p.category or ''} {p.cuisine or ''} {p.type or ''} {p.timing or ''} minutes {p.difficulty or ''}"
        p.embedding = model.encode(text).tolist()
        p.save(update_fields=["embedding"])
