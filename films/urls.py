from django.urls import path
from . import views

app_name = "films"

urlpatterns = [

    # ======= HOME / FILMS =======
    path('', views.film_list, name='home'),

    path('films/', views.film_list, name='film_list'),
    path('films/create/', views.film_create, name='film_create'),
    path('films/<int:id>/', views.film_detail, name='film_detail'),
    path('films/<int:id>/update/', views.film_update, name='film_update'),
    path('films/<int:id>/delete/', views.film_delete, name='film_delete'),

    # ======= COUNTRIES =======
    path('countries/', views.country_list, name='country_list'),
    path('countries/create/', views.country_create, name='country_create'),
    path('countries/<int:id>/', views.country_detail, name='country_detail'),
    path('countries/<int:id>/update/', views.country_update, name='country_update'),
    path('countries/<int:id>/delete/', views.country_delete, name='country_delete'),

    path('countries/autocomplete/',
         views.CountryAutocomplete.as_view(),
         name='country_autocomplete'),

    # ======= GENRES =======
    path('genres/', views.genre_list, name='genre_list'),
    path('genres/create/', views.genre_create, name='genre_create'),
    path('genres/<int:id>/', views.genre_detail, name='genre_detail'),
    path('genres/<int:id>/update/', views.genre_update, name='genre_update'),
    path('genres/<int:id>/delete/', views.genre_delete, name='genre_delete'),

    # ======= PEOPLE =======
    path('people/', views.person_list, name='person_list'),
    path('people/create/', views.person_create, name='person_create'),
    path('people/<int:id>/', views.person_detail, name='person_detail'),
    path('people/<int:id>/update/', views.person_update, name='person_update'),
    path('people/<int:id>/delete/', views.person_delete, name='person_delete'),

    path('people/autocomplete/',
         views.PersonAutocomplete.as_view(),
         name='person_autocomplete'),

    # ======= SUBTITLES =======
    path(
        'films/<int:film_id>/subtitles/<str:language>.vtt',
        views.get_subtitles,
        name='get_subtitles',
    ),

    path(
        'films/<int:film_id>/subtitles/edit/',
        views.subtitle_editor_view,
        name='subtitle_editor_view',
    ),

    path(
        'films/<int:film_id>/subtitles/save/lines/<str:language>/',
        views.save_subtitle,
        name='save_subtitle_lines',
    ),

    path(
        'films/<int:film_id>/subtitles/save/styles/<str:language>/',
        views.save_speaker_colors,
        name='save_speaker_colors',
    ),

    path(
        'films/<int:film_id>/subtitles/delete/<str:language>/',
        views.delete_subtitles,
        name='delete_subtitles',
    ),
]
