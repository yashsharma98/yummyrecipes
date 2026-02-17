from django.urls import path

from .utils.helper_utils import email_template, export_user_data, newnavbarnavrail, post_chart, save_location
from .utils.home_utils import add_to_favorites
from .utils.notification_utils import clear_all_notifications, remove_notification
from .utils.pdf_utils import customer_render_pdf_view, shopping_list_pdf
from .utils.recipes_helper import translate_content
from .utils.summarizer import summarize_content
from .views.accounts import UpdatePassword, UpdateProfile, acc_settings, profile_view
from .views.appearance import appearance, default_color_palette1, dynamic_css, get_transparent_rgba_colors, reset_colors, reset_dark_theme
from .views.authentications import delete_account, guest_mode, login_view, logout_view, signup_view, topostlogin
from .views.credits_management import credits, delete_credit_history, delete_redeemed_history, delete_spent_history
from .views.custom_passwords import (
    CustomLoginView,
    CustomPasswordResetCompleteView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetDoneView,
    CustomPasswordResetView,
    CustomSocialSignupView,
)
from .views.home_views import HomeView, landingpg
from .views.kitchen_ai import generate_recipe_content, generate_recipe_with_ai_image
from .views.recipes_comparison import compare_recipes, compare_recipes_new, compare_view
from .views.recipes_display import cuisines, custom_cards, exploreRecipesView, postDetailView, refresh_recipes, trendingRecipesView
from .views.recipes_history import blog_history, bulk_delete_blogs, delete_all_blog_history, delete_entry
from .views.recipes_management import Updaterecipeview, deleteRecipes, dislike_view, like_view, post_post_view
from .views.search import searchresults, userchannel
from .views.user_activity import (
    disliked_recipes,
    favorite_list,
    feedback_view,
    follow_unfollow_user,
    followers_list,
    liked_recipes,
    total_views,
)
from .views.user_analytics import dashboard, timeline, year_recap

urlpatterns = [
    path("", landingpg, name="landingpg"),
    path("password_reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("newnavbar_navrail", newnavbarnavrail, name="newnavbarnavrail"),
    path("explore/", exploreRecipesView.as_view(), name="explore"),
    path("home/", HomeView.as_view(), name="home"),
    path("refresh-recipes/", refresh_recipes, name="refresh_recipes"),
    path("login/", login_view, name="login"),
    path("accounts/3rdparty/signup/", CustomSocialSignupView.as_view(), name="socialaccount_signup"),
    path("accounts/login/", CustomLoginView.as_view(), name="account_login"),
    path("login_required/<pk>/", topostlogin, name="topostlogin"),
    path("signup/", signup_view, name="signup"),
    path("logout/", logout_view, name="logout"),
    path("profile/", profile_view, name="profile"),
    path("newrecipe/", post_post_view, name="createpost"),
    path("searchresults/", searchresults, name="searchresults"),
    path("recipe/<pk>/", postDetailView.as_view(), name="viewpost"),
    path("post/comment", postDetailView.as_view(), name="comment"),
    path("translate-content/", translate_content, name="translate_content"),
    path("like-view/", like_view, name="like-view"),
    path("dislike/", dislike_view, name="dislike-view"),
    path("user_channel/<first> <last>/<pk>/", userchannel, name="userchannelpage"),
    path("user_channel/<first>/<pk>/", userchannel, name="userchannelpage"),
    path("dashboard/", dashboard, name="dashboard"),
    path("delete/<int:pk>/", deleteRecipes.as_view(), name="delete"),
    path("editrecipe/<title>/<pk>/", Updaterecipeview, name="updaterecipe"),
    path("updateprofile/", UpdateProfile, name="updateprofile"),
    path("updatepassword/", UpdatePassword, name="updatepassword"),
    path("account_settings/", acc_settings, name="account_settings"),
    path("liked_recipes/", liked_recipes, name="liked_recipes"),
    path("disliked_recipes/", disliked_recipes, name="disliked_recipes"),
    path("<feed>/<pk>/download pdf/", customer_render_pdf_view, name="customerrender"),
    path("trending/", trendingRecipesView.as_view(), name="trending"),
    path("timeline/", timeline, name="timeline"),
    path("history/", blog_history, name="blog_history"),
    path("delete_entry/<pk>/", delete_entry, name="delete_blog"),
    path("delete_entry/", bulk_delete_blogs, name="bulk_delete"),
    path("delete-all/", delete_all_blog_history, name="delete_all_blog_history"),
    path("delete_account/", delete_account, name="delete_account"),
    path("recap/", year_recap, name="year_recap"),
    path("appearance/", appearance, name="appearance"),
    path("reset_colors/", reset_colors, name="reset_colors"),
    path("reset_dark_theme/", reset_dark_theme, name="reset_dark"),
    path("new_color_palette/", default_color_palette1, name="dcp_1"),
    path("dynamic.css/", dynamic_css, name="dynamic_css"),
    path("get_transparent_rgba_colors/", get_transparent_rgba_colors, name="get_transparent_rgba_colors"),
    path("save_location/", save_location, name="save_location"),
    path("fav/<int:id>/", add_to_favorites, name="add_to_favorites"),
    path("favourites/", favorite_list, name="favourites"),
    path("post_chart/", post_chart, name="post_chart"),
    path("for you/<slug>/", custom_cards, name="custom_cards"),
    path("credits/", credits, name="credits"),
    path("cuisines/<slug>/", cuisines, name="cuisines"),
    path("summarize/", summarize_content, name="summarize_content"),
    path("kitchenai/", generate_recipe_with_ai_image, name="generate_recipe"),
    path("kitchenai/", generate_recipe_content, name="generaterecipe"),
    path("email_template/", email_template, name="email_template"),
    path("remove_notification/", remove_notification, name="remove_notification"),
    path("clear_all_notifications/", clear_all_notifications, name="clear_all_notifications"),
    path("total_views/", total_views, name="total_views"),
    path("comparing/<pk>/", compare_recipes, name="compare_recipes"),
    path("comparing/", compare_recipes_new, name="compare_recipes"),
    path("comparing/<recipe_id1>/with/<recipe_id2>/", compare_view, name="compare_view"),
    path("feedback/", feedback_view, name="feedback"),
    path("profile/<str:username>/follow_unfollow/", follow_unfollow_user, name="follow_unfollow_user"),
    path("network/<name>/<pk>/", followers_list, name="connections"),
    path("generate-audio/<int:pk>/", postDetailView.as_view(), name="generate_audio_file"),
    path("delete_credit_history/", delete_credit_history, name="delete_credit_history"),
    path("delete_redeemed_history/", delete_redeemed_history, name="delete_redeemed_history"),
    path("delete_spent_history/", delete_spent_history, name="delete_spent_history"),
    path("<title>/<pk>/shopping list/", shopping_list_pdf, name="shopping_list"),
    path("export-data/", export_user_data, name="export_data"),
    path("guest-mode/", guest_mode, name="guest_mode"),
]
