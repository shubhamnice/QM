import streamlit as st
from PIL import Image
import requests
import matplotlib.pyplot as plt
from audio_recorder_streamlit import audio_recorder
from streamlit_extras.bottom_container import bottom
# from utils import speech_to_text
import pandas as pd
import io 
import logging
import plotly.graph_objects as go
import speech_recognition as sr

logging.getLogger("streamlit").setLevel(logging.ERROR)
api_url = 'http://172.10.1.176:5001'
 
logo = r'Picturenoname.png'
logos = Image.open(logo)
st.set_page_config(page_title="QueryMate", page_icon=logos, initial_sidebar_state="expanded")
 
# Initialize images
image_path1 = r'Picturenoname.png'
image_path2 = r'Nice-Logo_edit-version.png'
botimage = Image.open(image_path1)
logoimage = Image.open(image_path2)
 
# Layout for header and sidebar
col1, col2 = st.columns([1, 6.75])
with col1:
    st.image(botimage, width=90)
with col2:
    st.title("QueryMate")
    st.caption('_Powered by :green[OpenAI]_')
 
st.subheader('Ask Question related to the data')
st.markdown("<hr style='border: 1px solid rainbow;'>", unsafe_allow_html=True)
 
# Clear chat history
def clear_chat_history():
    st.session_state.messages = []
 
# File uploader
uploaded_file = st.file_uploader("Upload a file", type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg", "csv"], on_change=clear_chat_history)
 
import json
# Send request to API
def send_prompt_to_api(prompt, uploaded_file=None):
    files = {}
    if uploaded_file is not None:
        files['file'] = uploaded_file.getvalue()
 
    # Create a list of just the message contents for `message_history`
    message_history = [{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.messages]
 
    # Convert the list of dictionaries to a JSON string
    data = {'prompt': prompt, 'message_history': json.dumps(message_history)}
    try:
        response = requests.post(f"{api_url}/process", data=data, files=files)
        print('Hit to API for response')
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Request failed: {e}")
        return None
 
# Create a container for messages
message_container = st.container()

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'df' not in st.session_state:
    st.session_state.df = None
if 'plot_code' not in st.session_state:
    st.session_state.plot_code = None

# Define a global variable for the figure
fig = None
index=0

# Display chat messages
with message_container:
    for msg in st.session_state.messages:
        index+=1

        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])

        elif msg["role"] == "assistant":
            if "SELECT" in msg["content"] or "Dataset :" in msg["content"] or "Graph :" in msg["content"]:

                with st.chat_message("assistant"):
                    if "SELECT" in msg["content"]:
                        sql_query = msg["content"].replace("SQL Query: ", "")
                        st.code(sql_query, language='sql')
                    # Check if a dataset has been generated
                    if "Dataset :" in msg["content"]:
                        if st.session_state.df is not None:
                            st.dataframe(st.session_state.df)

                            # Provide chart options for the user
                            chart_type = st.selectbox(
                                "Choose a chart type",
                                ["Pie Chart", "Bar Chart", "Scatter Plot", "Histogram"],
                                key=f"chart_selectbox_{index}"
                            )

                            # Generate and display the chart based on the selected type
                            if chart_type == "Pie Chart":
                                # Assuming the dataset has two columns: 'Category' and 'Value'
                                fig = go.Figure(
                                    data=[go.Pie(labels=st.session_state.df.iloc[:, 0], values=st.session_state.df.iloc[:, 1])]
                                )
                                st.plotly_chart(fig, use_container_width=True, key=f"pie_chart_{index}")

                            elif chart_type == "Bar Chart":
                                fig = go.Figure(
                                    data=[go.Bar(x=st.session_state.df.iloc[:, 0], y=st.session_state.df.iloc[:, 1])]
                                )
                                st.plotly_chart(fig, use_container_width=True, key=f"bar_chart_{index}")

                            elif chart_type == "Scatter Plot":
                                fig = go.Figure(
                                    data=[go.Scatter(x=st.session_state.df.iloc[:, 0], y=st.session_state.df.iloc[:, 1], mode='markers')]
                                )
                                st.plotly_chart(fig, use_container_width=True, key=f"scatter_plot_{index}")

                            elif chart_type == "Histogram":
                                fig = go.Figure(
                                    data=[go.Histogram(x=st.session_state.df.iloc[:, 1])]
                                )
                                st.plotly_chart(fig, use_container_width=True, key=f"histogram_{index}")

            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

# Process user input and display results
def handle_input(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Send prompt to the API
    response = send_prompt_to_api(prompt)

    if response:
        assistant_message = response.get("message")
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})

        if "sql" in response:
            st.session_state.messages.append({"role": "assistant", "content": f"SQL Query: {response['sql']}"})
        
        if "results" in response:
            df_string = response['results']
            df = pd.read_csv(io.StringIO(df_string))  
            st.session_state.df = df  
            st.session_state.messages.append({"role": "assistant", "content": "Dataset :"})
    
    st.rerun()
# Create a placeholder for the text input
input_placeholder = st.empty()
with st.container():
    with bottom():
        input_col1, input_col2 = st.columns([10, 1])
        with input_col1:
            prompt = st.chat_input("What's up?")
        with input_col2:
            audio_bytes = audio_recorder(text="", icon_size="2x")
 
        if prompt:
            handle_input(prompt)

        elif audio_bytes and "audio_processed" not in st.session_state:
            try: 
                with st.spinner("Transcribing..."):
                    webm_file_path = "temp_audio.mp3"
                    with open(webm_file_path, "wb") as f:
                        f.write(audio_bytes)
                    recognizer = sr.Recognizer()

                    with sr.AudioFile(webm_file_path) as source:
                        audio_data = recognizer.record(source)
                    try:
                        prompt = recognizer.recognize_google(audio_data)
                        print(prompt)
                        # Set flag to indicate audio has been processed
                        st.session_state.audio_processed = True
                        handle_input(prompt)
                    except sr.UnknownValueError:
                        st.write("Google Speech Recognition could not understand the audio.")
                    except sr.RequestError as e:
                        st.write(f"Could not request results from Google Speech Recognition service; {e}")

            except Exception as e:
                print(f"Error Processing input: {e}")
                st.write("Please Try Again")

# Sidebar content
with st.sidebar:
    st.sidebar.image(logoimage, width=130)
    st.sidebar.subheader('_Powered by :green[OpenAI]_')
    st.sidebar.markdown("<hr style='border: 1px solid rainbow;'>", unsafe_allow_html=True)
    st.write("Tables and columns info can go here")
   
    st.session_state.tables = {'Suppliers','Shippers','Employees','OrderDetails','Orders','Customers','Products','Categories'}
    st.session_state.columns = {"Suppliers":"Holds data on the Suppliers of the products, Columns : Suppliername, Country, Address, Contactname, City, Postalcode, Phone, SupplierID",
                                "Shippers": "Contains details of Shippers, Columns : Phone, Shippername, ShipperID",
                                "Employees": "Stores information about employees, Columns : Photo, Birthdate, Firstname, Notes, EmployeeID, Lastname",
                                "OrderDetails": "Describes individual line items for each sales order, Columns :ProductID, OrderID, OrderdetailID, Quantity",
                                "Orders": "Details each sales order placed by customers, Columns : CustomerID, OrderID, ShipperID, EmployeeID, Orderdate",
                                "Customers": "CustomerID, Customername, City, Contactname, Postalcode, Country, Address",
                                "Products": "Contains details of each product, Columns :Unit, Productname, Price, ProductID, CategoryID, SupplierID",
                                "Categories": "Stores information about the different Categories of products , Columns :Categoryname, Description, CategoryID"
                            }
    st.write(f"Ask queries based on these tables:")
    for table in st.session_state.tables:
        st.write("**" + table + "**")
        if table in st.session_state.columns:
            column_names = "".join(st.session_state.columns[table])
            st.write(f"{column_names}")
    st.sidebar.write("**" + "Data Model:" + "**")
    data_model = {
            "Categories": "(CategoryID)",
            "Customers": "(CustomerID)",
            "Employees": "(EmployeeID)",
            "OrderDetails": "(OrderID, ProductID)",
            "Orders": "(OrderID, CustomerID, EmployeeID, ShipperID)",
            "Products": "(ProductID, CategoryID, SupplierID)",
            "Shippers": "(ShipperID)",
            "Suppliers": "(SupplierID)"
        }
    for table, attributes in data_model.items():
        st.sidebar.write(f"- {table} {attributes}")  
