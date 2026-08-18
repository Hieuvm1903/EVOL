import folium
import pandas as pd
import streamlit as st
from folium import MacroElement
from folium.plugins import (
    Draw, Fullscreen, MiniMap, MeasureControl, MousePosition,
    LocateControl, MarkerCluster, HeatMap,
)
from jinja2 import Template
from math import radians, sin, cos, sqrt, atan2
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

from config import PLACE_ICON_CHOICES, TIMEZONE
from services import places_service

_FA_TO_LABEL = {fa: label for label, fa in PLACE_ICON_CHOICES.items()}
_FLYTO_ZOOM = 17
_CENTER_ZOOM = 15
_PROXY_PARK_LATLNG = (89.9, 0.0)  # off-screen home for the right-click proxy marker
_DEFAULT_MARKER_COLOR = "#3388ff"  # fallback + default for new places

_MAP_STYLES = {
    "Light": ("CartoDB positron", None),
    "Streets": ("OpenStreetMap", None),
    "Dark": ("CartoDB dark_matter", None),
    "Satellite": (
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "Tiles &copy; Esri",
    ),
    "Terrain": (
        "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)",
    ),
}

_TOOL_OPTIONS = {
    "🖥️ Fullscreen": "fullscreen",
    "🗺️ Mini-map": "minimap",
    "📐 Measure distance": "measure",
    "📍 Cursor coordinates": "mouse_position",
    "🎯 Locate me (map button)": "locate_control",
    "🧲 Cluster markers": "cluster",
    "🔥 Heatmap overlay": "heatmap",
    "✏️ Draw / sketch": "draw",
}

_CURRENT_LOCATION_HTML = """
<style>
.evol-here-dot {
  width: 16px; height: 16px; border-radius: 50%;
  background: #4285F4; border: 3px solid #fff;
  box-shadow: 0 0 0 2px #4285F4;
  position: relative;
}
.evol-here-dot::after {
  content: ''; position: absolute; top: -8px; left: -8px;
  width: 32px; height: 32px; border-radius: 50%;
  background: rgba(66, 133, 244, 0.35);
  animation: evol-here-pulse 1.8s ease-out infinite;
}
@keyframes evol-here-pulse {
  0% { transform: scale(0.4); opacity: 1; }
  100% { transform: scale(1.6); opacity: 0; }
}
</style>
<div class="evol-here-dot"></div>
"""

_SELECTED_HALO_HTML = """
<style>
.evol-selected-halo {
  width: 46px; height: 46px; border-radius: 50%;
  border: 3px solid #FFD34D;
  box-shadow: 0 0 0 4px rgba(255, 211, 77, 0.35);
  animation: evol-selected-pulse 1.6s ease-in-out infinite;
}
@keyframes evol-selected-pulse {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.12); opacity: 0.55; }
}
</style>
<div class="evol-selected-halo"></div>
"""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _split_icon(icon_value) -> tuple[str, str]:
    if icon_value and "|" in str(icon_value):
        name, color = str(icon_value).split("|", 1)
        return name, color
    return "map-marker", "blue"


def _parse_tags(tags_value) -> list[str]:
    if tags_value is None or (isinstance(tags_value, float) and pd.isna(tags_value)):
        return []
    return [t.strip() for t in str(tags_value).split(",") if t.strip()]


def _icon_label_for_key(fa_name: str) -> str:
    return _FA_TO_LABEL.get(fa_name, f"📌 {fa_name}")


def _icon_emoji_for_key(fa_name: str) -> str:
    return _icon_label_for_key(fa_name).split(" ", 1)[0]


def _emoji_pin_html(emoji: str, color_hex: str, size: int = 34) -> str:
    font_size = int(size * 0.5)
    return f"""
    <div style="
        width:{size}px; height:{size}px; border-radius:50% 50% 50% 0;
        background:{color_hex}; transform:rotate(-45deg);
        display:flex; align-items:center; justify-content:center;
        box-shadow:0 2px 5px rgba(0,0,0,0.4); border:2px solid #fff;">
      <span style="transform:rotate(45deg); font-size:{font_size}px; line-height:1;">{emoji}</span>
    </div>
    """


def _resolve_color_hex(value) -> str:
    """The stored place color is a raw hex string (from st.color_picker).
    Rows created before the switch to a free color picker may still have
    an old fixed-palette color *name* (e.g. "blue") — that's not valid
    hex, so just fall back to the default rather than mapping it; existing
    rows can be fixed directly in the database."""
    if isinstance(value, str) and len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value
        except ValueError:
            pass
    return _DEFAULT_MARKER_COLOR


def _place_marker_icon(icon_name: str, icon_color: str) -> folium.DivIcon:
    emoji = _icon_emoji_for_key(icon_name)
    color_hex = _resolve_color_hex(icon_color)
    return folium.DivIcon(html=_emoji_pin_html(emoji, color_hex), icon_size=(34, 34), icon_anchor=(17, 34))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def _try_parse_pair(text: str) -> tuple[float, float] | None:
    if "," not in text:
        return None
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 2:
        return None
    try:
        a, b = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if -90 <= a <= 90 and -180 <= b <= 180:
        return a, b
    return None


def _normalize_single_decimal(text: str) -> float | None:
    text = (text or "").strip()
    if not text:
        return None
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Geolocation
# ---------------------------------------------------------------------------

def _trigger_geolocation(flag_key: str) -> None:
    st.session_state[flag_key] = True


def _resolve_geolocation(flag_key: str, js_key: str):
    if not st.session_state.get(flag_key):
        return None
    loc = get_geolocation(js_key)  # positional component_key, not key=
    if loc is None:
        return None
    st.session_state.pop(flag_key, None)
    if "error" in loc:
        st.error(f"Couldn't get your location: {loc['error'].get('message', 'unknown error')}")
        return None
    coords = loc.get("coords", {})
    if "latitude" in coords and "longitude" in coords:
        fix = (coords["latitude"], coords["longitude"])
        st.session_state["map_my_location"] = fix
        return fix
    return None


# ---------------------------------------------------------------------------
# Icon & color pickers — small, same-size trigger buttons side by side.
#
# Icon: a plain button grid in a popover. Replaces the third-party
# streamlit-select-icons component, which rendered as oversized white cards
# with broken horizontal+vertical scrollbars against our dark theme.
#
# Color: a real st.color_picker (free-form hex, not a fixed palette) —
# its swatch button is resized via scoped CSS to match the icon trigger's
# footprint so the two line up.
# ---------------------------------------------------------------------------

_PICKER_TRIGGER_CSS = """
<style>
.st-key-{key} {{
    display: flex;
}}
.st-key-{key} div[data-testid="stColorPicker"],
.st-key-{key} div[data-testid="stColorPicker"] > div,
.st-key-{key} div[data-testid="stColorPickerBlock"] {{
    width: 42px !important;
}}
.st-key-{key} div[data-testid="stColorPicker"] > label {{
    display: none !important;
}}
.st-key-{key} div[data-testid="stPopover"] > button,
.st-key-{key} div[data-testid="stColorPicker"] button,
.st-key-{key} div[data-testid="stColorPicker"] input[type="color"] {{
    box-sizing: border-box !important;
    width: 42px !important;
    height: 38px !important;
    min-width: 42px !important;
    min-height: 38px !important;
    max-width: 42px !important;
    max-height: 38px !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 1px solid rgba(250, 250, 250, 0.2) !important;
    border-radius: 8px !important;
    font-size: 1.05rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    -webkit-appearance: none;
    appearance: none;
}}
</style>
"""


def _render_icon_grid_popover(panel_key: str, icon_state_key: str) -> None:
    chosen = st.session_state[icon_state_key]
    items = list(PLACE_ICON_CHOICES.items())  # [(label, fa_name), ...]
    cols_per_row = 4
    trigger_key = f"icon_trigger_{panel_key}"

    # st.markdown(_PICKER_TRIGGER_CSS.format(key=trigger_key), unsafe_allow_html=True)

    with st.container(key=trigger_key):
        with st.popover(_icon_emoji_for_key(chosen), help=_icon_label_for_key(chosen)):
            st.caption("Choose an icon")
            for i in range(0, len(items), cols_per_row):
                row_items = items[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, (label, fa_name) in zip(cols, row_items):
                    emoji = label.split(" ", 1)[0]
                    is_selected = fa_name == chosen
                    with col:
                        if st.button(
                            emoji, key=f"iconbtn_{panel_key}_{fa_name}",
                            help=fa_name, use_container_width=True,
                            type="primary" if is_selected else "secondary",
                        ):
                            st.session_state[icon_state_key] = fa_name
                            st.rerun()


def _render_color_picker(panel_key: str, default_hex: str) -> str:
    trigger_key = f"color_trigger_{panel_key}"
    #st.markdown(_PICKER_TRIGGER_CSS.format(key=trigger_key), unsafe_allow_html=True)

    with st.container(key=trigger_key):
        return st.color_picker(
            "Color", value=default_hex, key=f"color_{panel_key}", label_visibility="collapsed"
        )


# ---------------------------------------------------------------------------
# Map macros
# ---------------------------------------------------------------------------

class _MarkerDblClickZoom(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
        {% for line in this.lines %}{{ line|safe }}
        {% endfor %}
        {% endmacro %}
    """)

    def __init__(self, lines: list[str]):
        super().__init__()
        self._name = "MarkerDblClickZoom"
        self.lines = lines


class _RightClickAddPlace(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
        {{ this._parent.get_name() }}.on('contextmenu', function(e) {
            var lat = e.latlng.lat.toFixed(6);
            var lng = e.latlng.lng.toFixed(6);
            var content = '<div style="text-align:center;">' +
                '<b>New place here?</b><br>' + lat + ', ' + lng + '<br>' +
                '<button id="evol-add-here-btn" style="margin-top:6px;background:#02ab21;' +
                'color:#fff;border:none;border-radius:6px;padding:4px 12px;cursor:pointer;' +
                'font-weight:600;">➕ Add place here</button></div>';
            L.popup().setLatLng(e.latlng).setContent(content).openOn({{ this._parent.get_name() }});
            setTimeout(function() {
                var btn = document.getElementById('evol-add-here-btn');
                if (btn) {
                    btn.onclick = function() {
                        {{ this.proxy_var }}.setLatLng(e.latlng);
                        {{ this.proxy_var }}.fire('click', {latlng: e.latlng});
                        {{ this._parent.get_name() }}.closePopup();
                    };
                }
            }, 0);
        });
        {% endmacro %}
    """)

    def __init__(self, proxy_var: str):
        super().__init__()
        self._name = "RightClickAddPlace"
        self.proxy_var = proxy_var


# ---------------------------------------------------------------------------
# Shared add/edit form
# ---------------------------------------------------------------------------

def _render_place_form(user_id: int, prefill: tuple[float, float] | None, edit_place: pd.Series | None) -> None:
    is_edit = edit_place is not None
    panel_key = f"edit_{int(edit_place['id'])}" if is_edit else "new"
    lat_key, lon_key = f"lat_{panel_key}", f"lon_{panel_key}"

    default_name = edit_place["name"] if is_edit else ""
    if is_edit:
        default_lat, default_lon = float(edit_place["lat"]), float(edit_place["lon"])
    elif prefill:
        default_lat, default_lon = prefill
    else:
        default_lat, default_lon = 20.834955, 106.718237
    default_desc = edit_place["description"] if is_edit else ""
    if is_edit:
        default_icon_key, default_color_raw = _split_icon(edit_place["icon"])
    else:
        default_icon_key, default_color_raw = "map-marker", _DEFAULT_MARKER_COLOR
    default_color = _resolve_color_hex(default_color_raw)
    default_tags = _parse_tags(edit_place.get("tags", "")) if is_edit else []

    st.markdown(f"#### {'Edit place' if is_edit else '➕ Add new place'}")

    if lat_key not in st.session_state:
        st.session_state[lat_key] = f"{default_lat:.6f}"
    if lon_key not in st.session_state:
        st.session_state[lon_key] = f"{default_lon:.6f}"

    geoloc_flag = f"geoloc_active_{panel_key}"
    fix = _resolve_geolocation(geoloc_flag, js_key=f"geoloc_{panel_key}")
    if fix:
        st.session_state[lat_key] = f"{fix[0]:.6f}"
        st.session_state[lon_key] = f"{fix[1]:.6f}"

    pair = _try_parse_pair(st.session_state[lat_key]) or _try_parse_pair(st.session_state[lon_key])
    if pair:
        st.session_state[lat_key] = f"{pair[0]:.6f}"
        st.session_state[lon_key] = f"{pair[1]:.6f}"

    # Name / icon / color all sit on one row, top-aligned. Icon and color
    # triggers are both fixed at the same small size (see _PICKER_TRIGGER_CSS)
    # so they line up with each other under matching captions.
    name_col, icon_col, color_col = st.columns([4, 1, 1])
    with name_col:
        st.caption("Place name")
        name = st.text_input(
            "Place name", value=default_name, placeholder="e.g. Hồ Gươm",
            key=f"name_{panel_key}", label_visibility="collapsed",
        )
    with icon_col:
        st.caption("Icon")
        icon_state_key = f"chosen_icon_{panel_key}"
        if icon_state_key not in st.session_state:
            st.session_state[icon_state_key] = default_icon_key
        _render_icon_grid_popover(panel_key, icon_state_key)
        chosen_icon_key = st.session_state[icon_state_key]
    with color_col:
        st.caption("Color")
        color = _render_color_picker(panel_key, default_color)

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        lat_raw = st.text_input(
            "Latitude", key=lat_key,
            help="Paste 'lat, lon' here (or in Longitude) to fill both fields at once",
        )
    with col2:
        lon_raw = st.text_input(
            "Longitude", key=lon_key,
            help="Paste 'lat, lon' here (or in Latitude) to fill both fields at once",
        )
    with col3:
        st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
        if st.button("", icon=":material/my_location:", key=f"geoloc_btn_{panel_key}",
                      help="Fill in my current location", use_container_width=True):
            _trigger_geolocation(geoloc_flag)
            st.rerun()

    # Live map preview: reflect the name/icon/color/position currently in
    # the form immediately, even before Save is pressed. render() reads
    # this to temporarily override (edit) or append (add) a marker when
    # drawing the map alongside this panel.
    preview_lat = _normalize_single_decimal(lat_raw)
    preview_lon = _normalize_single_decimal(lon_raw)
    st.session_state["map_live_preview"] = {
        "id": int(edit_place["id"]) if is_edit else None,
        "name": name.strip() or "Untitled place",
        "lat": preview_lat if preview_lat is not None else (default_lat if is_edit else None),
        "lon": preview_lon if preview_lon is not None else (default_lon if is_edit else None),
        "icon_value": f"{chosen_icon_key}|{color}",
    }

    existing_tags = places_service.get_all_tags(user_id)
    tags_str = st.text_input(
        "Tags (comma separated)", value=", ".join(default_tags),
        placeholder="date, food, memory...", key=f"tags_{panel_key}",
    )
    if existing_tags:
        st.caption("Existing tags: " + ", ".join(f"`{t}`" for t in existing_tags))

    description = st.text_area(
        "Description", value=default_desc, placeholder="Why this place matters...",
        key=f"desc_{panel_key}",
    )

    save_col, cancel_col = st.columns(2)
    if save_col.button("Save", type="primary", icon=":material/save:",
                        use_container_width=True, key=f"save_{panel_key}"):
        final_lat = _normalize_single_decimal(lat_raw)
        final_lon = _normalize_single_decimal(lon_raw)
        if final_lat is None or final_lon is None:
            st.error("Couldn't parse latitude/longitude — please check the values.")
            return
        if not (-90 <= final_lat <= 90 and -180 <= final_lon <= 180):
            st.error("Latitude must be -90..90 and longitude -180..180.")
            return

        icon_value = f"{chosen_icon_key}|{color}"
        tags_value = ",".join(t.strip() for t in tags_str.split(",") if t.strip())
        final_name = name.strip() or "Untitled place"

        if is_edit:
            places_service.update_place(
                int(edit_place["id"]), final_name, final_lat, final_lon,
                description.strip(), icon_value, tags_value,
            )
        else:
            places_service.add_place(
                user_id, final_name, final_lat, final_lon,
                description.strip(), icon_value, tags_value,
            )
        st.session_state["map_panel_mode"] = None
        st.session_state["map_edit_place_id"] = None
        st.session_state.pop("map_prefill_coords", None)
        st.session_state.pop("map_live_preview", None)
        st.rerun()

    if cancel_col.button("Cancel", use_container_width=True, key=f"cancel_{panel_key}"):
        st.session_state["map_panel_mode"] = None
        st.session_state["map_edit_place_id"] = None
        st.session_state.pop("map_prefill_coords", None)
        st.session_state.pop("map_live_preview", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Search panel — filters + results, also returns a (lat, lon, radius_km)
# circle spec when a distance filter is active.
# ---------------------------------------------------------------------------

def _render_search_panel(places_df: pd.DataFrame, user_id: int):
    st.markdown("#### 🔍 Search places")

    col1, col2, col3 = st.columns(3)
    with col1:
        name_q = st.text_input(
            "Search by name", key="places_filter_name",
            placeholder="Search by name...", icon=":material/search:",
        )
    with col2:
        all_tags = sorted({
            t for v in places_df.get("tags", pd.Series(dtype=str)).fillna("") for t in _parse_tags(v)
        }) if not places_df.empty else []
        tag_sel = st.multiselect("Filter by tags", all_tags, key="places_filter_tags")
    with col3:
        all_icon_labels = sorted({
            _icon_label_for_key(_split_icon(v)[0]) for v in places_df["icon"].dropna()
        }) if not places_df.empty else []
        icon_sel = st.multiselect("Filter by icon", all_icon_labels, key="places_filter_icon")

    fix = _resolve_geolocation("dist_geoloc_active", js_key="dist_geoloc")
    if fix:
        st.session_state["places_filter_dist_center"] = f"{fix[0]:.6f}, {fix[1]:.6f}"

    dcol1, dcol2, dcol3 = st.columns([2.2, 0.5, 1.3])
    with dcol1:
        loc_str = st.text_input(
            "Center location (lat, lon)", key="places_filter_dist_center",
            placeholder="21.0285, 105.8542",
        )
    with dcol2:
        st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
        if st.button("", icon=":material/my_location:", key="dist_geoloc_btn",
                      help="Use my current location", use_container_width=True):
            _trigger_geolocation("dist_geoloc_active")
            st.rerun()
    with dcol3:
        radius_km = st.number_input(
            "Radius (km)", min_value=0.0, value=0.0, step=1.0,
            key="places_filter_radius",
        )

    filtered_df = _apply_filters(places_df, name_q, tag_sel, icon_sel, loc_str, radius_km)

    radius_circle = None
    if loc_str.strip() and radius_km and radius_km > 0:
        center = _try_parse_pair(loc_str)
        if center:
            radius_circle = (center[0], center[1], radius_km)

    with st.container(height=340):
        _render_result_rows(filtered_df, user_id)

    return filtered_df, radius_circle


def _apply_filters(
    df: pd.DataFrame, name_q: str, tag_sel: list[str], icon_sel: list[str],
    loc_str: str, radius_km: float,
) -> pd.DataFrame:
    if df.empty:
        return df
    filtered = df
    if name_q.strip():
        filtered = filtered[filtered["name"].str.contains(name_q.strip(), case=False, na=False)]
    if tag_sel:
        wanted = set(tag_sel)
        filtered = filtered[filtered["tags"].fillna("").apply(lambda v: bool(wanted & set(_parse_tags(v))))]
    if icon_sel:
        wanted_icons = set(icon_sel)
        filtered = filtered[
            filtered["icon"].fillna("").apply(lambda v: _icon_label_for_key(_split_icon(v)[0]) in wanted_icons)
        ]
    if loc_str.strip() and radius_km and radius_km > 0:
        center = _try_parse_pair(loc_str)
        if center:
            center_lat, center_lon = center
            filtered = filtered[filtered.apply(
                lambda r: _haversine_km(center_lat, center_lon, r["lat"], r["lon"]) <= radius_km, axis=1,
            )]
    return filtered


def _render_result_rows(places_df: pd.DataFrame, user_id: int) -> None:
    selected_id = st.session_state.get("map_selected_place_id")

    if places_df.empty:
        st.info("No places match your filters.")
        return

    df = places_df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df["time"] = df.apply(lambda row: row["time"].astimezone(TIMEZONE), axis=1)

    for _, row in df.sort_values("time", ascending=False).iterrows():
        pid = int(row["id"])
        is_selected = pid == selected_id

        label = _icon_label_for_key(_split_icon(row["icon"])[0])
        tags = _parse_tags(row.get("tags", ""))
        tag_line = (" · " + ", ".join(f"#{t}" for t in tags)) if tags else ""
        header = f"{label} {row['name']}"

        row_col, del_col = st.columns([6, 1])
        with row_col:
            if st.button(header, key=f"selrow_{pid}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                st.session_state["map_selected_place_id"] = pid
                st.session_state["map_center_override"] = (float(row["lat"]), float(row["lon"]))
                st.rerun()
            st.caption(f"{row['time'].strftime('%m/%d/%Y %H:%M')}{tag_line}")
        with del_col:
            if st.button("", key=f"del_{pid}", icon=":material/delete:", help="Delete this place",
                         use_container_width=True):
                places_service.delete_place(pid, user_id)
                if selected_id == pid:
                    st.session_state["map_selected_place_id"] = None
                st.rerun()


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

def _render_map(
    map_df: pd.DataFrame,
    center_override: tuple[float, float] | None,
    my_location: tuple[float, float] | None,
    selected_place_id: int | None,
    tile_mode: str,
    radius_circle: tuple[float, float, float] | None = None,
    enabled_tools: frozenset = frozenset(),
):
    tiles, attr = _MAP_STYLES.get(tile_mode, _MAP_STYLES["Light"])
    map_kwargs = {"tiles": tiles}
    if attr:
        map_kwargs["attr"] = attr

    if center_override:
        m = folium.Map(location=list(center_override), zoom_start=_CENTER_ZOOM, **map_kwargs)
    else:
        m = folium.Map(location=[16.0, 106.0], zoom_start=5, **map_kwargs)

    if radius_circle:
        c_lat, c_lon, c_km = radius_circle
        folium.Circle(
            location=[c_lat, c_lon], radius=c_km * 1000,
            color="#02ab21", weight=2, fill=True, fill_color="#02ab21", fill_opacity=0.08,
        ).add_to(m)

    places_group = MarkerCluster(name="Places") if "cluster" in enabled_tools else folium.FeatureGroup(
        name="Places", show=True
    )

    dblclick_lines: list[str] = []
    if not map_df.empty:
        for _, row in map_df.iterrows():
            pid = int(row["id"])
            icon_name, icon_color = _split_icon(row["icon"])
            tags = _parse_tags(row.get("tags", ""))
            tag_line = f"<br><i>{', '.join(tags)}</i>" if tags else ""
            directions_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
            popup_html = (
                f"<b>{row['name']}</b><br>{row['description'] or ''}{tag_line}"
                f'<br><a href="{directions_url}" target="_blank" rel="noopener" '
                f'style="color:#02ab21;font-weight:600;">🧭 Directions</a>'
            )

            if pid == selected_place_id:
                folium.Marker(
                    location=[row["lat"], row["lon"]],
                    icon=folium.DivIcon(html=_SELECTED_HALO_HTML, icon_size=(46, 46), icon_anchor=(23, 23)),
                ).add_to(m)

            marker = folium.Marker(
                location=[row["lat"], row["lon"]],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row["name"],
                icon=_place_marker_icon(icon_name, icon_color),
            ).add_to(places_group)
            dblclick_lines.append(
                f"{marker.get_name()}.on('dblclick', function(e){{ "
                f"{m.get_name()}.flyTo([{row['lat']}, {row['lon']}], {_FLYTO_ZOOM}); "
                f"L.DomEvent.stopPropagation(e); }});"
            )
        if not center_override:
            bounds = map_df[["lat", "lon"]].agg(["min", "max"])
            m.fit_bounds([[float(bounds["lat"]["min"]), float(bounds["lon"]["min"])],
                          [float(bounds["lat"]["max"]), float(bounds["lon"]["max"])]])

    places_group.add_to(m)

    if "heatmap" in enabled_tools and not map_df.empty:
        heat_layer = folium.FeatureGroup(name="Heatmap", show=True)
        HeatMap(data=map_df[["lat", "lon"]].values.tolist(), radius=18, blur=22).add_to(heat_layer)
        heat_layer.add_to(m)

    if "draw" in enabled_tools:
        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": True, "polygon": True, "rectangle": True,
                "circle": True, "marker": True, "circlemarker": False,
            },
            edit_options={"edit": True, "remove": True},
        ).add_to(m)

    if "fullscreen" in enabled_tools:
        Fullscreen(position="topright").add_to(m)

    if "minimap" in enabled_tools:
        MiniMap(toggle_display=True, position="bottomleft").add_to(m)

    if "measure" in enabled_tools:
        MeasureControl(primary_length_unit="kilometers", position="topleft").add_to(m)

    if "mouse_position" in enabled_tools:
        MousePosition().add_to(m)

    if "locate_control" in enabled_tools:
        LocateControl(position="topleft").add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)

    if my_location:
        folium.Marker(
            location=list(my_location),
            icon=folium.DivIcon(html=_CURRENT_LOCATION_HTML, icon_size=(16, 16), icon_anchor=(8, 8)),
            tooltip="You are here",
        ).add_to(m)

    proxy_marker = folium.Marker(
        location=list(_PROXY_PARK_LATLNG),
        icon=folium.DivIcon(html="", icon_size=(0, 0)),
    ).add_to(m)

    m.add_child(_RightClickAddPlace(proxy_marker.get_name()))
    if dblclick_lines:
        m.add_child(_MarkerDblClickZoom(dblclick_lines))

    return st_folium(
        m, width=None, height=520, key="places_map",
        returned_objects=["last_clicked", "last_object_clicked"],
    )


def _handle_map_click(result, places_df: pd.DataFrame) -> None:
    if not result:
        return

    clicked_marker = result.get("last_object_clicked")
    if clicked_marker and clicked_marker.get("lat") is not None:
        click_key = f"obj:{clicked_marker['lat']:.6f},{clicked_marker['lng']:.6f}"
        if click_key != st.session_state.get("map_last_click"):
            st.session_state["map_last_click"] = click_key
            match = (
                places_df[
                    (places_df["lat"].round(6) == round(clicked_marker["lat"], 6)) &
                    (places_df["lon"].round(6) == round(clicked_marker["lng"], 6))
                ]
                if not places_df.empty else places_df
            )
            if match is not None and not match.empty:
                st.session_state["map_selected_place_id"] = int(match.iloc[0]["id"])
            else:
                st.session_state["map_prefill_coords"] = (clicked_marker["lat"], clicked_marker["lng"])
                st.session_state["map_edit_place_id"] = None
                st.session_state["map_panel_mode"] = "add"
                st.session_state["map_selected_place_id"] = None
            st.rerun()
        return

    plain_click = result.get("last_clicked")
    if plain_click and plain_click.get("lat") is not None:
        click_key = f"blank:{plain_click['lat']:.6f},{plain_click['lng']:.6f}"
        if click_key != st.session_state.get("map_last_click") and st.session_state.get("map_selected_place_id"):
            st.session_state["map_last_click"] = click_key
            st.session_state["map_selected_place_id"] = None
            st.rerun()


def _render_selected_place_actions(places_df: pd.DataFrame, user_id: int) -> None:
    selected_id = st.session_state.get("map_selected_place_id")
    if selected_id is None or places_df.empty:
        return
    match = places_df[places_df["id"] == selected_id]
    if match.empty:
        st.session_state["map_selected_place_id"] = None
        return
    place = match.iloc[0]

    icon_label = _icon_label_for_key(_split_icon(place["icon"])[0])
    directions_url = f"https://www.google.com/maps/dir/?api=1&destination={place['lat']},{place['lon']}"

    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
    c1.markdown(f"**{icon_label.split(' ')[0]} Selected: {place['name']}**")
    if c2.button("Edit", icon=":material/edit:", use_container_width=True, key="sel_edit"):
        st.session_state["map_edit_place_id"] = int(place["id"])
        st.session_state.pop("map_prefill_coords", None)
        st.session_state["map_panel_mode"] = "edit"
        st.rerun()
    if c3.button("Delete", icon=":material/delete:", use_container_width=True, key="sel_delete"):
        places_service.delete_place(int(place["id"]), user_id)
        st.session_state["map_selected_place_id"] = None
        st.rerun()
    c4.link_button("🧭", directions_url, use_container_width=True, help="Directions")
    if c5.button("", icon=":material/close:", use_container_width=True,
                 help="Cancel selection", key="sel_cancel"):
        st.session_state["map_selected_place_id"] = None
        st.rerun()


# ---------------------------------------------------------------------------
# Live preview — while the add/edit panel is open, reflect its current
# name/icon/color/position on the map immediately, without requiring Save.
# ---------------------------------------------------------------------------

def _apply_live_preview(places_df: pd.DataFrame) -> pd.DataFrame:
    preview = st.session_state.get("map_live_preview")
    if not preview:
        return places_df

    df = places_df.copy()

    if preview["id"] is not None:
        # Editing an existing place: overlay the live values onto its row.
        mask = df["id"] == preview["id"]
        if mask.any():
            df.loc[mask, "name"] = preview["name"]
            df.loc[mask, "icon"] = preview["icon_value"]
            if preview["lat"] is not None:
                df.loc[mask, "lat"] = preview["lat"]
            if preview["lon"] is not None:
                df.loc[mask, "lon"] = preview["lon"]
        return df

    # Adding a new place: show it as a temporary extra marker, not yet saved.
    if preview["lat"] is None or preview["lon"] is None:
        return df
    new_row = pd.DataFrame([{
        "id": -1, "user_id": None, "name": preview["name"],
        "lat": preview["lat"], "lon": preview["lon"],
        "description": "", "icon": preview["icon_value"], "tags": "", "time": "",
    }])
    return pd.concat([df, new_row], ignore_index=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    st.markdown("## :material/location_on: Places")

    user = st.session_state.get("user")
    if not user:
        st.warning(
            "Log in first (see the Login tab) — your places are personal to your account.",
            icon=":material/lock:",
        )
        return

    st.caption(
        "Right-click the map to add a place there. Hover a marker to see its name, "
        "click it for details, double-click to zoom in, click elsewhere to deselect."
    )

    panel_mode = st.session_state.get("map_panel_mode")  # None | "add" | "edit" | "search"

    style_names = list(_MAP_STYLES.keys())
    tile_mode = st.session_state.get("map_tile_mode", style_names[0])

    # Add / Search / Map style are kept narrow so the map-tools multiselect
    # (which needs room to show several selected chips) gets most of the row.
    btn1, btn2, btn3, tools_col = st.columns([1, 1, 1, 5])
    with btn1:
        if st.button("➕ Add", use_container_width=True, icon=":material/add_location:",
                      help="Add new place"):
            st.session_state["map_edit_place_id"] = None
            st.session_state.pop("map_prefill_coords", None)
            st.session_state["map_panel_mode"] = "add"
            st.rerun()
    with btn2:
        search_label = "✖️ Close" if panel_mode == "search" else "🔍 Search"
        if st.button(search_label, use_container_width=True, help="Search places"):
            st.session_state["map_panel_mode"] = None if panel_mode == "search" else "search"
            st.rerun()
    with btn3:
        st.selectbox("Map style", style_names, index=style_names.index(tile_mode),
                     key="map_tile_mode", label_visibility="collapsed")
    with tools_col:
        tools_selected = st.multiselect(
            "Map tools", list(_TOOL_OPTIONS.keys()), key="map_tools_selected",
            placeholder="🧩 Map tools (fullscreen, measure, heatmap...)",
            label_visibility="collapsed",
        )

    enabled_tools = frozenset(_TOOL_OPTIONS[label] for label in tools_selected)
    if "draw" in enabled_tools:
        st.caption("✏️ Draw mode is on — sketch with the map's toolbar. Nothing drawn here is saved.")

    tile_mode = st.session_state["map_tile_mode"]

    places_df = places_service.get_places(user["id"])
    panel_mode = st.session_state.get("map_panel_mode")

    my_location = st.session_state.get("map_my_location")
    selected_id = st.session_state.get("map_selected_place_id")
    center_override = st.session_state.get("map_center_override")

    if panel_mode in ("add", "edit"):
        panel_col, map_col = st.columns([1.1, 2])
        with panel_col:
            edit_id = st.session_state.get("map_edit_place_id")
            edit_place = None
            if edit_id is not None and not places_df.empty:
                match = places_df[places_df["id"] == edit_id]
                edit_place = match.iloc[0] if not match.empty else None
            _render_place_form(
                user["id"],
                prefill=st.session_state.get("map_prefill_coords"),
                edit_place=edit_place,
            )
        with map_col:
            preview_df = _apply_live_preview(places_df)
            result = _render_map(preview_df, center_override, my_location, selected_id, tile_mode,
                                  enabled_tools=enabled_tools)

    elif panel_mode == "search":
        panel_col, map_col = st.columns([1.1, 2])
        with panel_col:
            filtered_df, radius_circle = _render_search_panel(places_df, user["id"])
        with map_col:
            result = _render_map(filtered_df, center_override, my_location, selected_id,
                                  tile_mode, radius_circle=radius_circle, enabled_tools=enabled_tools)

    else:
        result = _render_map(places_df, center_override, my_location, selected_id, tile_mode,
                              enabled_tools=enabled_tools)

    _handle_map_click(result, places_df)
    _render_selected_place_actions(places_df, user["id"])