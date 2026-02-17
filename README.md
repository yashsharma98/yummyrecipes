# Yummy Recipes

Yummy Recipes is a full-stack Django web application where users can upload, explore, and interact with recipes. A simple recipe sharing platform gradually evolved into a feature rich system with machine learning, semantic search, and AI-based recipe generation.

<br>

**Live Link**  
https://yummy-recipes-ht6h.onrender.com/

<br>

**Project Screenshot**

  ![Screenshot (336)](https://github.com/user-attachments/assets/89290d89-a0ae-469a-8e5f-46aa36b9f121)

  <img width="1919" height="1031" alt="image" src="https://github.com/user-attachments/assets/263b9623-6f9c-4521-9191-8ea4479397c1" />


<br>  

## About The Project

This project goes beyond a simple recipe management application, focusing not only on core features but also on improving search accuracy, integrating machine learning models, and handling deployment.

The application is deployed on **Render**, uses **PostgreSQL** as the database, and stores media and static files on **AWS S3**.

<br>

## Main Features

### Recipe Management
- Upload, edit, and delete recipes  
- Display detailed ingredients, instructions, and nutritional information  
- Download, share, and generate QR codes for recipes  
- Compare any two recipes side by side 

<br>

### Search System
- Search recipes with advanced filters:
  - Category (Breakfast, Lunch, Snacks, Dinner)
  - Cuisine
  - Type (Veg/Non-Veg)
  - Servings
  - Timing
  - Difficulty  
- Semantic search using vector embeddings
- Ability to search and follow other users
- Fallback mechanism

<br>

### Cooking Time Prediction
- Trained an **XGBoost** model to predict preparation and cooking time  
- Uses ingredients and instructions as input  
- Integrated directly into the Django application  

<br>

### Recipe Recommendations
- Personalized suggestions based on:
  - User preferences  
  - Previous history

<br>

### Social Engagement
- Like / Dislike recipes
- Comments
- Follow / Unfollow users  
- Notification panel  
- Author profile pages  

<br>

### Recipe Summarization & AI Generation
- Generate recipes using Gemini API
- Recipe summarization & translation

<br>

### User Dashboard
- Track uploads and views  
- View likes/dislikes received  
- Manage favorites  
- Credit system
- Activity timeline


<br>

## Technologies Used

### Backend
- Django  
- PostgreSQL  
- XGBoost  
- NLP & Vector Embeddings  
- Gemini API  

### Frontend
- HTML  
- CSS  
- Bootstrap  

### Deployment & Services
- Render  
- AWS S3  
- Google OAuth  
- Email Integration  