
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
import pytz
st.set_page_config(page_icon="random",
    layout="wide",
    initial_sidebar_state="expanded",
    )  
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
timezone = pytz.timezone("Asia/Ho_Chi_Minh")  # Replace with your desired timezone

with st.sidebar:
    choose = option_menu("EVOL Space", ["Home", "About", "His-tory", "Relax", "???"],
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
    html.html(
    """
  <iframe src="https://www.facebook.com/plugins/post.php?href=https%3A%2F%2Fwww.facebook.com%2Fphoto%2F%3Ffbid%3D1423943031364508%26set%3Da.167615383663952&width=750&show_text=true&height=499&appId" 
  width="700" height="400" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowfullscreen="true" allow="autoplay; clipboard-write; 
  encrypted-media; picture-in-picture; web-share"></iframe>


""",
    height=400,width=700
)

    html.html("""
          
<div id="fb-root"></div>
<script async defer crossorigin="anonymous" src="https://connect.facebook.net/vi_VN/sdk.js#xfbml=1&version=v18.0" nonce="UhxLsFD4"></script><div class="fb-comments" data-href="https://www.facebook.com/photo/?fbid=1423943031364508&amp;set=a.167615383663952https://www.facebook.com/photo/?fbid=1423943031364508&amp;set=a.167615383663952" data-width="750" data-numposts="5"></div>
<div class="fb-comments" data-href="https://ev-l0-3.streamlit.app" data-width="750" data-numposts="5"></div>""",
    height=300,width=900,scrolling= True)
elif choose == "About":
    facebook_page_url = 'https://www.facebook.com/evbinl/'

# Define the HTML code to embed the Facebook page



    
elif choose == "His-story":
    music = music.music
    for m in music:
        st.write(m[0])
        st_player(m[1])
elif choose == "Relax":  
    s  = st.text_area('Tâm sự vào đây (Ẩn danh 100%)', '''
        Dù sao cũng đã tới đây rồi tâm sự tí nhỉ    
    ''')
    def onclick():
        write("{"+s+"}")
        st.rerun()
    st.button('Submit',key = 'submit',on_click= onclick)
    content = getwrite()
    if  not content.empty:
        content['time'] = pd.to_datetime(content["time"])
        content['time'] = content.apply(lambda row: row['time'].astimezone(timezone), axis = 1)
        df = content.sort_values(by='time',ascending=False)
        st.write(df)
elif choose == "???":
    col1,col2 = st.columns([1,3])
    with col1:

        keys = st.text_input("Key???","/Evolut??n")
    with col2:
        s  = st.text_area('My thought', '''      
    ''')  
    btn = st.button('Submit',key = 'submit')
    if btn:
        if "/Evolut!0n" in keys:    
            blog(s.strip())
            st.success("Posted!!!")
            st.rerun()
        else:
            st.warning("Don't ya remember it, EVOL?")
    content = getblog()
    if  not content.empty:
        content['time'] = pd.to_datetime(content["time"])
        content['time'] = content.apply(lambda row: row['time'].astimezone(timezone), axis = 1)

        df = content.sort_values(by='time',ascending=False)
        st.write(df)
