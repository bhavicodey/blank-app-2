import ee
import folium
import streamlit as st
import datetime
from streamlit_folium import st_folium
import geemap.foliumap as geemap
from io import StringIO
from twilio.rest import Client  # Import Twilio client
import requests  # For fetching YouTube videos

# Initialize Earth Engine
service_account = 'so2project@so2proj.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, './so2proj-afa9d673af99.json')
ee.Initialize(credentials)

# Twilio configuration
TWILIO_SID = 'AC021a22ec70e8fcdde8f6756a64427f03'
TWILIO_AUTH_TOKEN = '0dd11c7a236d6c255f04f971771e1822'
TWILIO_PHONE_NUMBER = '+12679910016'

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# YouTube API configuration
YOUTUBE_API_KEY = 'AIzaSyAN1f3e5PObP78oBeHk8_qJHK6hZz381BQ'
YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3/search'

# Function to send SMS
def send_sms(to, message):
    client.messages.create(
        to=to,
        from_=TWILIO_PHONE_NUMBER,
        body=message
    )

# Function to get Sentinel-5P SO2 data
def get_sentinel5p_so2(start_date, end_date, region):
    start_date = ee.Date(start_date)
    end_date = ee.Date(end_date)
    collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_SO2') \
                .filterDate(start_date, end_date) \
                .select('SO2_column_number_density') \
                .filterBounds(region)
    return collection

# Function to retrieve location name
def get_location_name(lat, lon):
    return f"Location ({lat:.2f}, {lon:.2f})"

# Function to check if SO2 levels are high
def check_high_so2(image, region, threshold=0.0003):
    stats = image.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=region,
        scale=1000,
        bestEffort=True
    )
    max_so2 = stats.get('SO2_column_number_density').getInfo()
    return max_so2 is not None and max_so2 > threshold

# Function to visualize the data with clipping
def visualize_data(Map, lat, lon, start_date, end_date, phone_number=None):
    region = ee.Geometry.Point([lon, lat]).buffer(100000)  # Buffer by 100 km (100000 meters)

    # Get Sentinel-5P SO2 data
    s5p_collection = get_sentinel5p_so2(start_date, end_date, region)
    s5p_image = s5p_collection.median()
    s5p_clipped_image = s5p_image.clip(region)

    vis_params = {
        'min': 0,
        'max': 0.0003,
        'palette': ['blue', 'green', 'yellow', 'orange', 'red']
    }

    Map.setCenter(lon, lat, 8)
    Map.addLayer(s5p_clipped_image, vis_params, 'Sentinel-5P SO2')

    marker_popup = get_location_name(lat, lon)
    folium.Marker(
        location=[lat, lon],
        popup=marker_popup,
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(Map)

    st_folium(Map, height=600, width=700)

    if check_high_so2(s5p_image, region):
        st.warning("""
            ### High SO2 Levels Detected!
            **Precautions:**
            - Stay indoors if possible.
            - Use air purifiers if available.
            - Avoid outdoor exercise and strenuous activities.
            - Consult a healthcare provider if you experience any respiratory issues.
        """)
        if phone_number:
            send_sms(phone_number, f"Alert! High SO2 levels detected at {marker_popup}. Please take precautions.")

# Function to fetch YouTube videos
def fetch_youtube_videos(query):
    params = {
        'part': 'snippet',
        'q': query,
        'key': YOUTUBE_API_KEY,
        'maxResults': 5,
        'type': 'video'
    }
    response = requests.get(YOUTUBE_API_URL, params=params)
    return response.json().get('items', [])

# Main code to run the app
st.title("SO2 Data Visualization")

st.sidebar.header("User Navigation")
st.sidebar.write(
    """
    This application allows you to visualize Sentinel-5P SO2 data over a specified date range and location.
    Use the date picker to select the start and end dates for the SO2 data. Click on the map to select a location
    for which you want to view the SO2 concentration. After selecting a location and date range, click on the
    "Visualize SO2 Data" button to display the SO2 data on the map.
    """
)

phone_number = st.sidebar.text_input("Enter your phone number (for alerts):", "")
start_date = st.sidebar.date_input('Start date', datetime.date(2020, 1, 1))
end_date = st.sidebar.date_input('End date', datetime.date(2020, 1, 15))

if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")

if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 0, 0

if 'visualize' not in st.session_state:
    st.session_state.visualize = False

Map = geemap.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=2)

st.subheader("Click on the map to select a place")
map_data = st_folium(Map, width=700, height=500)

if map_data and 'last_clicked' in map_data:
    marker_location = map_data['last_clicked']
    if marker_location:
        st.session_state.lat, st.session_state.lon = marker_location['lat'], marker_location['lng']
        st.sidebar.success(f"Marker location updated to Latitude: {st.session_state.lat}, Longitude = {st.session_state.lon}")

st.write(f"Selected Place: Latitude = {st.session_state.lat}, Longitude = {st.session_state.lon}")

if st.sidebar.button('Visualize SO2 Data'):
    st.session_state.visualize = True

if st.session_state.visualize:
    visualize_data(Map, st.session_state.lat, st.session_state.lon, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), phone_number)

    # Fetch and display YouTube videos
    st.subheader("Related YouTube Videos")
    videos = fetch_youtube_videos("SO2")
    
    for video in videos:
        video_title = video['snippet']['title']
        video_id = video['id']['videoId']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Fancy display for YouTube videos
        st.markdown(f"""
            <div style="border: 1px solid #ccc; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                <h5>{video_title}</h5>
                <a href="{video_url}" target="_blank">Watch Video</a>
            </div>
        """, unsafe_allow_html=True)

    # Add legend to the sidebar after visualization
    legend_html = '''
    <div style="width: 200px; height: 200px;
    background-color: black; color: white; border:2px solid grey; font-size:14px; opacity: 0.8;">
    &nbsp; <b>SO2 Concentration</b><br>
    &nbsp; <i>mol/m<sup>2</sup></i><br>
    &nbsp; <i style="background:blue; width:20px;height:20px;display:inline-block;"></i>&nbsp; 0.0000 - 0.0001<br>
    &nbsp; <i style="background:green; width:20px;height:20px;display:inline-block;"></i>&nbsp; 0.0001 - 0.0002<br>
    &nbsp; <i style="background:yellow; width:20px;height:20px;display:inline-block;"></i>&nbsp; 0.0002 - 0.00025<br>
    &nbsp; <i style="background:orange; width:20px;height:20px;display:inline-block;"></i>&nbsp; 0.00025 - 0.0003<br>
    &nbsp; <i style="background:red; width:20px;height:20px;display:inline-block;"></i>&nbsp; > 0.0003<br>
    </div>
    '''
    st.sidebar.markdown(legend_html, unsafe_allow_html=True)
