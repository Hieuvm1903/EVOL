
import pyodbc 
import streamlit as st
from streamlit_option_menu import option_menu
import streamlit.components.v1 as html
import numpy as np
import pandas as pd
from image import *
from music import *
import music
from data import *

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
                         icons=['person-rolodex', 'lightbulb', 'menu-button', 'bell','door-open'],
                         menu_icon="app-indicator", default_index=0,
                         styles={
        "container": {"padding": "5!important", "background-color": "#0c0c0c"},
        "icon": {"color": "orange", "font-size": "25px"}, 
        "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#02ab21"},
    }
    )

if choose == "Home":
    """
    Từng đau khổ mới biết thế nào là đau khổ.\n
    Từng chấp trước mới có thể rũ bỏ được chấp trước.\n
    Từng vấn vương mới có thể không còn vấn vương!"""
    
elif choose == "About":
    print()
    
elif choose == "His-story":
    music = music.music
    for m in music:
        st_player(m)
elif choose == "Relax":  
    s  = st.text_area('Tâm sự vào đây (Ẩn danh 100%)', '''
        Dù sao cũng đã tới đây rồi tâm sự tí nhỉ
    
    ''')
    def onclick():
        write(s)
    
    st.button('Submit',key = 'submit',on_click= onclick)
    
