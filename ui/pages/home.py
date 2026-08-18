import urllib.parse

import streamlit as st
import streamlit.components.v1 as components

FB_POST_URL = (
    "https://www.facebook.com/photo/?fbid=1423943031364508"
    "&set=a.167615383663952"
)

# These three describe the FULL, correctly-proportioned embed — the size
# at which the crop (no avatar/header, no like/comment/share bar) actually
# lines up. Don't shrink these to make the card smaller; use DISPLAY_SCALE
# instead, or the crop offset will drift again (see below).
FB_EMBED_WIDTH = 750
FB_EMBED_HEIGHT = 900
FB_VISIBLE_HEIGHT = 400

# Visual size knob — scales the whole embed down (image included) via CSS
# transform, so the crop stays exactly correct at any size. 0.65 -> ~488px
# wide card. Raise/lower this to make the card bigger/smaller.
DISPLAY_SCALE = 0.65


def _render_hero() -> None:
    st.markdown(
        """
        <div class="evol-hero">
            <div class="evol-hero-title">EVOL&nbsp;Space</div>
            <div class="evol-hero-quote">
                <p>Từng đau khổ mới biết thế nào là đau khổ.</p>
                <p>Từng chấp trước mới có thể rũ bỏ được chấp trước.</p>
                <p>Từng vấn vương mới có thể không còn vấn vương!</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_facebook_embed() -> None:
    href = urllib.parse.quote(FB_POST_URL, safe="")
    embed_src = (
        "https://www.facebook.com/plugins/post.php"
        f"?href={href}&width={FB_EMBED_WIDTH}&show_text=false"
        f"&height={FB_EMBED_HEIGHT}&appId"
    )

    display_width = FB_EMBED_WIDTH * DISPLAY_SCALE-10
    display_height = FB_VISIBLE_HEIGHT * DISPLAY_SCALE

    # Outer box is sized at the SCALED (small) dimensions and clips
    # anything outside it. Inner box is sized at the FULL (real) FB
    # dimensions and then shrunk visually with transform:scale — the crop
    # offset that already worked at full size stays correct, it's just
    # rendered smaller.
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