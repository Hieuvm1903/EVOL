import time
import urllib.parse

import streamlit as st
import streamlit.components.v1 as components

FB_POST_URL = (
    "https://www.facebook.com/photo/?fbid=1423943031364508"
    "&set=a.167615383663952"
)
FB_EMBED_WIDTH = 750
FB_EMBED_HEIGHT = 900
FB_VISIBLE_HEIGHT = 400
DISPLAY_SCALE = 0.65

_QUOTE_LINES = [
    "Từng đau khổ mới biết thế nào là đau khổ.",
    "Từng chấp trước mới có thể rũ bỏ được chấp trước.",
    "**Từng vấn vương mới có thể không còn vấn vương!**",
]
_QUOTE_TEXT = "  \n".join(_QUOTE_LINES)
_WORD_DELAY = 0.045


def _quote_stream():
    for i, line in enumerate(_QUOTE_LINES):
        words = line.split(" ")
        for j, word in enumerate(words):
            yield word + (" " if j < len(words) - 1 else "")
            time.sleep(_WORD_DELAY)
        if i < len(_QUOTE_LINES) - 1:
            yield "  \n"


def _render_hero() -> None:
    st.markdown(
        '<div class="evol-hero-title">EVOL&nbsp;Space</div>',
        unsafe_allow_html=True,
    )


    st.markdown('<div class="evol-quote-card">', unsafe_allow_html=True)
    st.markdown('<div class="evol-quote-mark evol-quote-mark-open">“</div>', unsafe_allow_html=True)

    with st.container(key="evol_hero_quote_typing"):
        st.write_stream(_quote_stream())

    st.markdown('<div class="evol-quote-mark evol-quote-mark-close">”</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def _render_facebook_embed() -> None:
    href = urllib.parse.quote(FB_POST_URL, safe="")
    embed_src = (
        "https://www.facebook.com/plugins/post.php"
        f"?href={href}&width={FB_EMBED_WIDTH}&show_text=false"
        f"&height={FB_EMBED_HEIGHT}&appId"
    )
    display_width = FB_EMBED_WIDTH * DISPLAY_SCALE-10
    display_height = FB_VISIBLE_HEIGHT * DISPLAY_SCALE

    html = f"""
    <div style="display:flex; justify-content:center;">
      <div style="
          width:{display_width}px;
          height:{display_height}px;
          overflow:hidden;
          border-radius:14px;
          border:1px solid #2a2a2a;
          background:#161616;
          box-shadow:0 2px 10px rgba(0,0,0,0.25);
          position:relative;
      ">
        <div style="
            width:{FB_EMBED_WIDTH}px;
            height:{FB_EMBED_HEIGHT}px;
            transform:scale({DISPLAY_SCALE});
            transform-origin:top left;
            position:absolute;
            top:0; left:0;
        ">
          <iframe
              src="{embed_src}"
              width="{FB_EMBED_WIDTH}"
              height="{FB_EMBED_HEIGHT}"
              style="border:none;position:absolute;top:0;left:0;"
              scrolling="no"
              frameborder="0"
              allowfullscreen="true"
              allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
          ></iframe>
        </div>
      </div>
    </div>
    """
    components.html(html, height=int(display_height) + 8, scrolling=False)


def render() -> None:
    _render_hero()
    _render_facebook_embed()
    st.markdown("---")