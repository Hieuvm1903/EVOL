import streamlit as st


def render() -> None:
    st.markdown(
        "Từng đau khổ mới biết thế nào là đau khổ.  \n"
        "Từng chấp trước mới có thể rũ bỏ được chấp trước.  \n"
        "Từng vấn vương mới có thể không còn vấn vương!"
    )

    st.iframe(
        """
  <iframe src="https://www.facebook.com/plugins/post.php?href=https%3A%2F%2Fwww.facebook.com%2Fphoto%2F%3Ffbid%3D1423943031364508%26set%3Da.167615383663952&width=750&show_text=true&height=499&appId"
  width="700" height="400" style="border:none;overflow:hidden" scrolling="no" frameborder="0" allowfullscreen="true" allow="autoplay; clipboard-write;
  encrypted-media; picture-in-picture; web-share"></iframe>
""",
        height=400, width=700,
    )

#     st.iframe(
#         """
# <div id="fb-root"></div>
# <script async defer crossorigin="anonymous" src="https://connect.facebook.net/vi_VN/sdk.js#xfbml=1&version=v18.0" nonce="UhxLsFD4"></script>
# <div class="fb-comments" data-href="https://www.facebook.com/photo/?fbid=1423943031364508&amp;set=a.167615383663952https://www.facebook.com/photo/?fbid=1423943031364508&amp;set=a.167615383663952" data-width="750" data-numposts="5"></div>
# <div class="fb-comments" data-href="https://ev-l0-3.streamlit.app" data-width="750" data-numposts="5"></div>
# """,
#         height=300, width=900,
#     )
    st.markdown("---")
