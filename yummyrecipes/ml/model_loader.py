import os

import joblib
from django.conf import settings

BASE_DIR = settings.BASE_DIR

PREP_MODEL_PATH = os.path.join(BASE_DIR, "yummyrecipes/ml/prep_time_model.pkl")
COOK_MODEL_PATH = os.path.join(BASE_DIR, "yummyrecipes/ml/cook_time_model.pkl")

prep_pipeline = None
cook_pipeline = None


def load_models():
    global prep_pipeline, cook_pipeline

    if prep_pipeline is None:
        prep_pipeline = joblib.load(PREP_MODEL_PATH)

    if cook_pipeline is None:
        cook_pipeline = joblib.load(COOK_MODEL_PATH)

    return prep_pipeline, cook_pipeline
