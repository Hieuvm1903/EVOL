import streamlit as st
import streamlit.components.v1 as html
import pandas as pd
import pytz
from music import music as pop, anime, bendy
from streamlit_player import st_player
from data import write, getwrite, blog, getblog
from image import list_frames, merge_with_frame

timezone = pytz.timezone("Asia/Ho_Chi_Minh")


def render_home():
    st.markdown("""
    Từng đau khổ mới biết thế nào là đau khổ.
    
    Từng chấp trước mới có thể rũ bỏ được chấp trước.
    
    Từng vấn vương mới có thể không còn vấn vương!
    """)

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


def render_about():
    st.write("About page - add content here")


def render_history():
    tab1, tab2, tab3 = st.tabs(["Linh tinh", "Anime", "Bendy"])
    with tab1:
        for m in pop:
            st.write(m[0])
            st_player(m[1])
    with tab2:
        for m in anime:
            st.write(m[0])
            st_player(m[1])
    with tab3:
        for m in bendy:
            st.write(m[0])
            st_player(m[1])


def render_relax():
    s  = st.text_area('Tâm sự vào đây (Ẩn danh 100%)', '')
    def onclick():
        write("{"+s+"}")
        st.rerun()
    st.button('Submit',key = 'submit',on_click= onclick)
    content = getwrite()
    if  not content.empty:
        content['time'] = pd.to_datetime(content["time"])
        content['time'] = content.apply(lambda row: row['time'].astimezone(timezone), axis = 1)
        df = content.sort_values(by='time',ascending=False)
        # could render df here if desired


def render_secret():
    col1,col2 = st.columns([1,3])
    with col1:
        keys = st.text_input("Key???","/Evolut??n")
    with col2:
        s  = st.text_area('My thought', '')
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
        for row in df.iterrows():
            s = row[1]['time'].strftime("%m/%d/%Y, %H:%M:%S")+": "+row[1]['content']
            st.write(s)


def render_photobooth():
    """Photobooth: take a picture from the camera or upload one, pick a frame, preview and download."""
    st.header("Photobooth")

    source = st.radio("Source", options=["Camera", "Upload"], index=0, horizontal=True)

    image_file = None
    if source == "Camera":
        # Streamlit's camera input returns an UploadedFile-like object or None
        image_file = st.camera_input("Take a picture")
    else:
        image_file = st.file_uploader("Upload a photo", type=["png","jpg","jpeg"])

    frames = list_frames('frames')
    frame_choice = None
    if frames:
        # show friendly names
        import os
        names = [os.path.basename(f) for f in frames]
        idx = st.selectbox("Choose a frame", options=list(range(len(frames))), format_func=lambda i: names[i])
        frame_choice = frames[idx]
    else:
        st.info("No frames found in the `frames/` directory.")

    if image_file and frame_choice:
        from PIL import Image
        import io
        # `image_file` is an UploadedFile-like object (camera or upload), PIL can open it directly
        user_img = Image.open(image_file)
        merged = merge_with_frame(user_img, frame_choice)
        st.image(merged, use_container_width=True)

        buf = io.BytesIO()
        merged.convert('RGB').save(buf, format='PNG')
        buf.seek(0)
        st.download_button("Download result", data=buf, file_name="photobooth.png", mime="image/png")
