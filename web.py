
import pyodbc 
import streamlit as st
from streamlit_option_menu import option_menu
import streamlit.components.v1 as html
from  PIL import Image
import numpy as np
import pandas as pd
import plotly.express as px
import folium
import supabase as sb
from supabase import create_client, Client
from streamlit_folium import st_folium, folium_static
title = """Từng đau khổ mới biết thế nào là đau khổ.\n
 Từng chấp trước mới có thể rũ bỏ được chấp trước.\n
   Từng vấn vương mới có thể không còn vấn vương!"""
st.write(title)
hide_streamlit_style = """
            <style>
            header {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            footer:after {
	content:'Made by EVOL'; 
	visibility: visible;
	display: block;
	position: relative;
	#background-color: red;
	padding: 5px;
	top: 2px;
}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
with st.sidebar:
    choose = option_menu("EVOL Space", ["Home", "About", "His-story", "Relax", "???"],
                         icons=['house', 'lightbulb', 'menu-button', 'bell','door-open'],
                         menu_icon="app-indicator", default_index=0,
                         styles={
        "container": {"padding": "5!important", "background-color": "#0c0c0c"},
        "icon": {"color": "orange", "font-size": "25px"}, 
        "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#02ab21"},
    }
    )

if choose == "Home":
    col1, col2 = st.columns( [0.5, 0.5])
  
elif choose == "About":
    Lights = pd.DataFrame([[21.0043061,105.8373198],[21.0004175,105.839110],[20.9975346,105.844127]], columns= ['lat','lon'])
    
elif choose == "His-story":
    choose
elif choose == "Relax":    
    choose
