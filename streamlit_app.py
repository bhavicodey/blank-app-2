import ee
import folium
import streamlit as st
import datetime
from streamlit_folium import st_folium
import geemap.foliumap as geemap
from io import StringIO


service_account = 'so2project@so2proj.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, './so2proj-afa9d673af99.json')
ee.Initialize(credentials)

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


# Function to retrieve location name (placeholder function for demonstration)
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
def visualize_data(Map, lat, lon, start_date, end_date):
    # Define the region based on selected coordinates
    region = ee.Geometry.Point([lon, lat]).buffer(100000)  # Buffer by 100 km (100000 meters)

    # Get Sentinel-5P SO2 data
    s5p_collection = get_sentinel5p_so2(start_date, end_date, region)
    s5p_image = s5p_collection.median()

    # Clip the image to the 100 km buffer region
    s5p_clipped_image = s5p_image.clip(region)

    # Visualization parameters for Sentinel-5P SO2
    vis_params = {
        'min': 0,
        'max': 0.0003,
        'palette': ['blue', 'green', 'yellow', 'orange', 'red']
    }

    # Center the map on the selected marker location and add SO2 data
    Map.setCenter(lon, lat, 8)
    Map.addLayer(s5p_clipped_image, vis_params, 'Sentinel-5P SO2')

    # Add a marker with a popup for the selected location
    marker_popup = get_location_name(lat, lon)
    folium.Marker(
        location=[lat, lon],
        popup=marker_popup,
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(Map)

    # Display the map
    st_folium(Map, height=600, width=700)

    # Check if SO2 levels are high
    if check_high_so2(s5p_image, region):
        st.warning("High SO2 levels detected at this location!")


# Main code to run the app
st.title("SO2 Data Visualization")

# Sidebar for user inputs
st.sidebar.header("User Navigation")
st.sidebar.write(
    """
    This application allows you to visualize Sentinel-5P SO2 data over a specified date range and location.
    Use the date picker to select the start and end dates for the SO2 data. Click on the map to select a location
    for which you want to view the SO2 concentration. After selecting a location and date range, click on the
    "Visualize SO2 Data" button to display the SO2 data on the map.
    """
)

# Date selection UI
st.sidebar.subheader("Date Selection")
start_date = st.sidebar.date_input('Start date', datetime.date(2020, 1, 1))
end_date = st.sidebar.date_input('End date', datetime.date(2020, 1, 15))

# Ensure start date is before end date
if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")

# Initialize map and starting coordinates if not already stored
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 0, 0  # Default coordinates

if 'visualize' not in st.session_state:
    st.session_state.visualize = False

# Create a folium map using geemap
Map = geemap.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=2)

# Show the folium map and let the user select a location by clicking on it
st.subheader("Click on the map to select a place")
map_data = st_folium(Map, width=700, height=500)

# Check for user clicks on the map
if map_data and 'last_clicked' in map_data:
    marker_location = map_data['last_clicked']
    if marker_location:
        st.session_state.lat, st.session_state.lon = marker_location['lat'], marker_location['lng']
        st.sidebar.success(f"Marker location updated to Latitude: {st.session_state.lat}, Longitude = {st.session_state.lon}")

# Display the selected location (latitude and longitude) on the UI
st.write(f"Selected Place: Latitude = {st.session_state.lat}, Longitude = {st.session_state.lon}")

# Button to visualize data after location and dates are set
if st.sidebar.button('Visualize S2 Data'):
    st.session_state.visualize = True  # Update session state to persist visualization

# Display the legend and map visualization
if st.session_state.visualize:
    visualize_data(Map, st.session_state.lat, st.session_state.lon, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

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
