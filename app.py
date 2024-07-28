import streamlit as st
import pickle
import pandas as pd
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from tenacity import retry, wait_fixed, stop_after_attempt, RetryError
import logging

# API_KEY = 'fce438244d329decc2ff4b233cd72da0'
API_KEY = '109bff269b11bdcdf95fe98457b27435'
BASE_URL = 'https://api.themoviedb.org/3'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def fetch_movie_details(movie_id):
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get_details():
        logging.debug(f"Fetching details for movie_id: {movie_id}")
        response = requests.get(
            f'{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&append_to_response=credits,reviews,videos'
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        logging.debug(f"API response: {data}")

        poster_path = "https://image.tmdb.org/t/p/w185/" + data.get('poster_path', "via.placeholder.com/185")
        rating = data.get('vote_average', 'N/A')
        cast = [member['name'] for member in data.get('credits', {}).get('cast', [])[:5]]  # get top 5 cast members
        director = [member['name'] for member in data.get('credits', {}).get('crew', []) if member['job'] == 'Director']
        producer = [member['name'] for member in data.get('credits', {}).get('crew', []) if member['job'] == 'Producer']
        reviews = [review['content'] for review in data.get('reviews', {}).get('results', [])[:2]]  # get top 2 reviews
        youtube_key = data.get('videos', {}).get('results', [{}])[0].get('key')

        movie_details = {
            'poster_path': poster_path,
            'rating': rating,
            'cast': cast,
            'director': director,
            'producer': producer,
            'reviews': reviews,
            'youtube_key': youtube_key
        }
        return movie_details

    try:
        return get_details()
    except RetryError as e:
        st.error(f"Failed to fetch movie details after multiple attempts: {e}")
    except (ConnectionError, Timeout) as e:
        st.error(f"Network error: {e}")
    except RequestException as e:
        st.error(f"Request failed: {e}")
    except TypeError as e:
        st.error(f"TypeError encountered: {e}")
    except Exception as e:
        st.error(f"Unexpected error encountered: {e}")
    return None


def recommend(movie):
    movie_index = movies[movies['title'] == movie].index[0]
    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies = []
    recommended_movies_details = []
    for i in movies_list:
        movie_id = movies.iloc[i[0]].movie_id
        recommended_movies.append(movies.iloc[i[0]].title)
        movie_details = fetch_movie_details(movie_id)
        if movie_details:
            recommended_movies_details.append(movie_details)
        else:
            recommended_movies_details.append({
                'poster_path': "https://via.placeholder.com/185",
                'rating': 'N/A',
                'cast': [],
                'director': [],
                'producer': [],
                'reviews': [],
                'youtube_key': None
            })  # Append default values if data is not available
    return recommended_movies, recommended_movies_details


# Load movies data and similarity matrix
movies_dict = pickle.load(open('movie_dict.pkl', 'rb'))
movies = pd.DataFrame(movies_dict)
similarity = pickle.load(open('similarity.pkl', 'rb'))

# Streamlit UI
st.title('Movie Recommender System')

# Movie selection box
selected_movie_name = st.selectbox('Select a movie:', movies['title'].values)

# Recommend button
if st.button('Recommend'):
    names, details = recommend(selected_movie_name)

    # Dynamically create columns for the recommended movies
    cols = st.columns(5)
    for i in range(min(5, len(names))):
        with cols[i]:
            st.text(names[i])
            st.image(details[i]['poster_path'], use_column_width=True)  # Poster
            st.text(f"Rating: {details[i]['rating']}")
            st.text("Cast: " + ", ".join(details[i]['cast']))
            st.text("Director: " + ", ".join(details[i]['director']))
            st.text("Producer: " + ", ".join(details[i]['producer']))
            st.text("Reviews: ")
            for review in details[i]['reviews']:
                st.text(f"- {review[:100]}...")  # Display first 100 characters of each review
            if details[i]['youtube_key']:
                st.balloons()
                st.markdown(f"[Watch on YouTube](https://www.youtube.com/watch?v={details[i]['youtube_key']})")

            # Show star rating when hovering over the poster
            st.write(
                f'<span style="font-size: 24px; color: gold;">{"★" * int(details[i]["rating"])}</span>',
                unsafe_allow_html=True
            )

            # Open detailed view in new tab when clicking on the poster
            st.markdown(f'<a href="http://localhost:8501" target="_blank">More Details</a>', unsafe_allow_html=True)

