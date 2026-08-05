import streamlit as st

from services import music_service
from ui.now_playing_widget import load_queue as _load_queue
from utils import ytmusic_search

_SORT_OPTIONS = ["Newest first", "Oldest first", "Name (A-Z)", "Name (Z-A)"]


def _current_user_id():
    user = st.session_state.get("user")
    return user["id"] if user else None


def _sort_playlists(df, sort_choice: str):
    if df.empty:
        return df
    if sort_choice == "Name (A-Z)":
        return df.sort_values("name", key=lambda s: s.str.lower())
    if sort_choice == "Name (Z-A)":
        return df.sort_values("name", key=lambda s: s.str.lower(), ascending=False)
    if sort_choice == "Oldest first":
        return df.sort_values("created_at", ascending=True)
    return df.sort_values("created_at", ascending=False)  # Newest first


# ---------------------------------------------------------------------------
# Playlist list view
# ---------------------------------------------------------------------------

@st.dialog("Create a new playlist")
def _new_playlist_dialog(user_id: int) -> None:
    name = st.text_input("Playlist name", key="new_playlist_dialog_name")
    if st.button("Create", type="primary", icon=":material/add:", use_container_width=True):
        if name.strip():
            music_service.create_playlist(user_id, name.strip())
            st.rerun()
        else:
            st.warning("Give it a name first.")


@st.dialog("Import a playlist")
def _import_playlist_dialog(user_id: int) -> None:
    st.caption(
        "Paste JSON exported from EVOL Space's Export button, or plain text "
        "with one \"Title - URL\" per line. Great for sharing a playlist "
        "between accounts."
    )
    raw = st.text_area("Playlist data", height=200, key="import_playlist_raw")
    if st.button("Import", type="primary", icon=":material/file_upload:", use_container_width=True):
        if not raw.strip():
            st.warning("Paste something first.")
        else:
            ok, message, _count = music_service.import_playlist(user_id, raw)
            (st.success if ok else st.error)(message)
            if ok:
                st.rerun()


def _play_from_list(playlist_id: int, mode: str) -> None:
    tracks = music_service.get_playlist_tracks(playlist_id)
    if tracks.empty:
        st.warning("This playlist is empty.")
    else:
        _load_queue(tracks, mode)
        st.rerun()


def _render_playlist_row(row, all_playlists) -> None:
    pid = int(row["id"])
    c_name, c_play, c_shuffle, c_repeat, c_menu = st.columns([4, 0.6, 0.6, 0.6, 0.6], vertical_alignment="center")

    c_name.markdown(f":material/music_note: **{row['name']}**")

    if c_play.button("", key=f"list_play_{pid}", icon=":material/play_arrow:", help="Play"):
        _play_from_list(pid, "Normal")
    if c_shuffle.button("", key=f"list_shuffle_{pid}", icon=":material/shuffle:", help="Shuffle"):
        _play_from_list(pid, "Shuffle")
    if c_repeat.button("", key=f"list_repeat_{pid}", icon=":material/repeat:", help="Repeat all"):
        _play_from_list(pid, "Repeat All")

    with c_menu:
        with st.popover("", icon=":material/more_vert:"):
            if st.button("Open", key=f"open_{pid}", icon=":material/folder_open:", use_container_width=True):
                st.session_state["music_view"] = "detail"
                st.session_state["music_selected_playlist_id"] = pid
                st.rerun()
            if st.button("Delete", key=f"delete_{pid}", icon=":material/delete:", use_container_width=True):
                music_service.delete_playlist(pid)
                st.rerun()

            st.divider()
            st.caption("Copy tracks from another playlist (duplicates skipped)")
            others = all_playlists[all_playlists["id"] != pid]
            if others.empty:
                st.caption("No other playlists yet.")
            else:
                opts = {r["name"]: int(r["id"]) for _, r in others.iterrows()}
                src_name = st.selectbox(
                    "Source", list(opts.keys()), key=f"copysrc_{pid}", label_visibility="collapsed"
                )
                if st.button("Copy tracks", key=f"copybtn_{pid}", icon=":material/content_copy:",
                             use_container_width=True):
                    added = music_service.copy_playlist_tracks(opts[src_name], pid)
                    st.success(f"Copied {added} new track(s).")
                    st.rerun()

            st.divider()
            st.caption("Export / share")
            _render_export_controls(pid, key_suffix=f"list_{pid}", code_height=160)


def _render_playlist_list(user_id: int) -> None:
    top1, top2, top3 = st.columns([1.2, 1, 2])
    with top1:
        if st.button("New playlist", icon=":material/add:", use_container_width=True):
            _new_playlist_dialog(user_id)
    with top2:
        if st.button("Import", icon=":material/file_upload:", use_container_width=True):
            _import_playlist_dialog(user_id)
    with top3:
        search = st.text_input(
            "Find by name", label_visibility="collapsed",
            placeholder="Find playlist by name...", icon=":material/search:",
        )

    playlists = music_service.get_playlists(user_id)
    if playlists.empty:
        st.info("No playlists yet — create one above.", icon=":material/info:")
        return

    filtered = playlists
    if search.strip():
        filtered = playlists[playlists["name"].str.contains(search.strip(), case=False, na=False)]
        if filtered.empty:
            st.caption(f'No playlists match "{search.strip()}".')

    sort_choice = st.segmented_control(
        "Sort by", _SORT_OPTIONS, default="Newest first", key="playlist_sort",
    ) or "Newest first"
    filtered = _sort_playlists(filtered, sort_choice)

    for _, row in filtered.iterrows():
        with st.container(border=True):
            _render_playlist_row(row, playlists)


# ---------------------------------------------------------------------------
# Playlist detail view
# ---------------------------------------------------------------------------

def _render_play_controls(tracks, key_prefix: str) -> None:
    c1, c2, c3 = st.columns(3)
    if c1.button("Play", key=f"{key_prefix}_play", icon=":material/play_arrow:", use_container_width=True):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Normal")
            st.rerun()
    if c2.button("Shuffle", key=f"{key_prefix}_shuffle", icon=":material/shuffle:", use_container_width=True):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Shuffle")
            st.rerun()
    if c3.button("Repeat all", key=f"{key_prefix}_repeat", icon=":material/repeat:", use_container_width=True):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Repeat All")
            st.rerun()


def _play_track_from_here(tracks_df, track_id: int) -> None:
    matches = tracks_df.index[tracks_df["id"] == track_id]
    if len(matches) == 0:
        return
    pos = tracks_df.index.get_loc(matches[0])
    subset = tracks_df.iloc[pos:]
    current_mode = st.session_state.get("music_mode", "Normal") if st.session_state.get("music_queue") else "Normal"
    _load_queue(subset, current_mode)
    st.rerun()


def _play_track_next(track_row) -> None:
    """Queues this track right after the first item of whatever's currently
    loaded. Note: since the player tracks playback position entirely in the
    browser (see the player docstring below), this can't know exactly which
    track is *actually* playing right now if you're deep into a long queue —
    it inserts after the queue's first track and restarts playback from
    there. For precise "resume where I am, just add this next," use Play
    From Here instead."""
    track_dict = {"title": track_row["title"], "video_id": track_row["video_id"]}
    existing = st.session_state.get("music_queue")
    if not existing:
        st.session_state["music_queue"] = [track_dict]
        st.session_state["music_mode"] = "Normal"
    else:
        filtered = [t for t in existing if t.get("video_id") != track_dict["video_id"]]
        filtered.insert(1 if filtered else 0, track_dict)
        st.session_state["music_queue"] = filtered
    st.rerun()


def _render_track_row(playlist_id: int, tracks_df, t) -> None:
    tid = int(t["id"])
    tc_title, tc_play, tc_next, tc_rename, tc_remove = st.columns(
        [4, 0.6, 0.6, 0.6, 0.6], vertical_alignment="center"
    )
    tc_title.write(t["title"])

    if tc_play.button("", key=f"trackplay_{playlist_id}_{tid}", icon=":material/play_arrow:",
                       help="Play from here"):
        _play_track_from_here(tracks_df, tid)
    if tc_next.button("", key=f"tracknext_{playlist_id}_{tid}", icon=":material/queue_play_next:",
                       help="Play next"):
        _play_track_next(t)

    with tc_rename:
        with st.popover("", icon=":material/edit:", help="Rename track"):
            new_title = st.text_input(
                "New title", value=t["title"], key=f"renametrack_{playlist_id}_{tid}",
                label_visibility="collapsed",
            )
            st.caption("Renames this track everywhere it's used, not just here.")
            if st.button("Save", key=f"renametracksave_{playlist_id}_{tid}",
                         icon=":material/save:", use_container_width=True):
                music_service.rename_track(tid, new_title)
                st.rerun()

    if tc_remove.button("", key=f"rm_{playlist_id}_{tid}", icon=":material/delete:",
                         help="Remove from playlist"):
        music_service.remove_track_from_playlist(playlist_id, tid)
        st.rerun()


def _render_add_track(playlist_id: int, user_id: int, existing_ids: set) -> None:
    with st.expander("Add track", icon=":material/add:", expanded=False):
        tab_search, tab_link = st.tabs([":material/search: Search", ":material/link: Paste link"])

        with tab_search:
            query = st.text_input("Search songs", key=f"search_q_{playlist_id}",
                                   placeholder="song title or artist...", icon=":material/search:")
            if st.button("Search", key=f"search_btn_{playlist_id}", icon=":material/search:") and query.strip():
                with st.spinner("Searching..."):
                    st.session_state[f"search_results_{playlist_id}"] = ytmusic_search.search_songs(query.strip())

            results = st.session_state.get(f"search_results_{playlist_id}", [])
            for r in results:
                rc1, rc2, rc3 = st.columns([1, 4, 1], vertical_alignment="center")
                if r["thumbnail_url"]:
                    rc1.image(r["thumbnail_url"], width=56)
                rc2.markdown(f"**{r['title']}**  \n{r['artist']} · {r['duration']}")
                if rc3.button("", key=f"searchadd_{playlist_id}_{r['video_id']}", icon=":material/add:"):
                    url = f"https://www.youtube.com/watch?v={r['video_id']}"
                    ok, msg, _ = music_service.add_track_and_attach(
                        playlist_id, url, user_id,
                        known_title=r["title"], known_thumbnail=r["thumbnail_url"],
                    )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

        with tab_link:
            url = st.text_input("YouTube link", key=f"add_url_{playlist_id}",
                                 placeholder="https://www.youtube.com/watch?v=...", icon=":material/link:")
            title_override = st.text_input("Title (optional)", key=f"add_title_{playlist_id}")
            if st.button("Fetch & add", key=f"add_btn_{playlist_id}", icon=":material/add:"):
                if not url.strip():
                    st.warning("Paste a YouTube link first.")
                else:
                    ok, msg, _ = music_service.add_track_and_attach(
                        playlist_id, url.strip(), user_id, known_title=title_override.strip() or None,
                    )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

        library = music_service.get_all_tracks()
        addable = library[~library["id"].isin(existing_ids)] if not library.empty else library
        if addable is not None and not addable.empty:
            opts = {r["title"]: r["id"] for _, r in addable.iterrows()}
            pick = st.selectbox("Or add from your library", ["—"] + list(opts.keys()), key=f"pick_{playlist_id}")
            if pick != "—" and st.button("Add selected", key=f"add_lib_{playlist_id}", icon=":material/add:"):
                music_service.add_track_to_playlist(playlist_id, opts[pick])
                st.rerun()


def _render_export_controls(playlist_id: int, key_suffix: str, code_height: int | None = None) -> None:
    fmt = st.segmented_control(
        "Format", ["JSON", "Plain text"], default="JSON", key=f"export_fmt_{key_suffix}",
    ) or "JSON"
    content = (music_service.export_playlist_json(playlist_id) if fmt == "JSON"
               else music_service.export_playlist_text(playlist_id))
    st.code(content, language=("json" if fmt == "JSON" else None), wrap_lines=True, height=code_height)
    st.download_button(
        "Download", data=content,
        file_name=f"playlist.{'json' if fmt == 'JSON' else 'txt'}",
        mime="application/json" if fmt == "JSON" else "text/plain",
        icon=":material/download:", key=f"export_dl_{key_suffix}",
    )
    st.caption("Paste this into **Import** on another account to share it.")


def _render_export(playlist_id: int) -> None:
    with st.expander("Export / share this playlist", icon=":material/ios_share:", expanded=False):
        _render_export_controls(playlist_id, key_suffix=f"detail_{playlist_id}")


def _render_playlist_detail(user_id: int, playlist_id: int) -> None:
    if st.button("Back to playlists", icon=":material/arrow_back:"):
        st.session_state["music_view"] = "list"
        st.rerun()

    playlists = music_service.get_playlists(user_id)
    match = playlists[playlists["id"] == playlist_id]
    if match.empty:
        st.warning("Playlist not found.")
        st.session_state["music_view"] = "list"
        return
    current_name = match.iloc[0]["name"]

    name_col, save_col = st.columns([4, 1], vertical_alignment="bottom")
    new_name = name_col.text_input(
        "Playlist name", value=current_name, key=f"rename_input_{playlist_id}",
        icon=":material/edit:",
    )
    if save_col.button("Save", key=f"rename_save_{playlist_id}", icon=":material/save:",
                        use_container_width=True):
        if new_name.strip() and new_name.strip() != current_name:
            music_service.rename_playlist(playlist_id, new_name.strip())
            st.rerun()

    tracks = music_service.get_playlist_tracks(playlist_id)
    existing_ids = set(tracks["id"]) if not tracks.empty else set()

    _render_add_track(playlist_id, user_id, existing_ids)
    _render_export(playlist_id)

    _render_play_controls(tracks, key_prefix=f"detail_{playlist_id}")

    if tracks.empty:
        st.caption("No tracks yet — add some above.")
        return

    track_search = st.text_input(
        "Find track by name", key=f"track_search_{playlist_id}",
        placeholder="Find a track by name...", icon=":material/search:",
        label_visibility="collapsed",
    )
    display_tracks = tracks
    if track_search.strip():
        display_tracks = tracks[tracks["title"].str.contains(track_search.strip(), case=False, na=False)]

    if display_tracks.empty:
        st.caption(f'No tracks match "{track_search.strip()}".')
    else:
        with st.container(height=420):
            for _, t in display_tracks.iterrows():
                _render_track_row(playlist_id, tracks, t)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    st.markdown("## :material/library_music: Music")

    user_id = _current_user_id()
    if not user_id:
        st.warning("Log in first (see the Login tab) to build playlists and listen to music.",
                    icon=":material/lock:")
        return



    view = st.session_state.get("music_view", "list")
    if view == "detail" and st.session_state.get("music_selected_playlist_id"):
        _render_playlist_detail(user_id, st.session_state["music_selected_playlist_id"])
    else:
        _render_playlist_list(user_id)
