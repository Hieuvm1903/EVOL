import random

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
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    name = c1.text_input("Playlist name", key="new_playlist_dialog_name")
    if c2.button(
        "Create", type="primary", icon=":material/add:", use_container_width=True
    ):
        if name.strip():
            music_service.create_playlist(user_id, name.strip())
            st.rerun()
        else:
            st.warning("Give it a name first.")


@st.dialog("Import a playlist")
def _import_playlist_dialog(user_id: int) -> None:
    st.caption(
        "Paste JSON exported from EVOL Space's Export button, or plain text "
        'with one "Title - URL" per line. Great for sharing a playlist '
        "between accounts."
    )
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    raw = c1.text_area("Playlist data", height=160, key="import_playlist_raw")
    if c2.button(
        "Import",
        type="primary",
        icon=":material/file_upload:",
        use_container_width=True,
    ):
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
    # Keyed container -> gives this row's markup a stable "st-key-pl_row_*"
    # class, which the CSS in ui/styles.py uses to force the columns
    # below to stay on ONE row (nowrap) no matter how narrow the screen
    # is, instead of Streamlit's default of stacking columns vertically.
    with st.container(key=f"pl_row_{pid}"):
        c_name, c_play, c_shuffle, c_repeat, c_menu = st.columns(
            [5, 1, 1, 1, 1], vertical_alignment="center", gap="small"
        )

        if c_name.button(
            f":material/music_note: **{row['name']}**",
            key=f"open_row_{pid}",
            use_container_width=True,
        ):
            st.session_state["music_view"] = "detail"
            st.session_state["music_selected_playlist_id"] = pid
            st.rerun()

        if c_play.button(
            "",
            key=f"list_play_{pid}",
            icon=":material/play_arrow:",
            help="Play",
            use_container_width=True,
        ):
            _play_from_list(pid, "Normal")

        if c_shuffle.button(
            "",
            key=f"list_shuffle_{pid}",
            icon=":material/shuffle:",
            help="Shuffle play",
            use_container_width=True,
        ):
            _play_from_list(pid, "Shuffle")

        if c_repeat.button(
            "",
            key=f"list_repeat_{pid}",
            icon=":material/repeat:",
            help="Repeat all",
            use_container_width=True,
        ):
            _play_from_list(pid, "Repeat All")

        with c_menu:
            with st.popover("", icon=":material/more_vert:", width = 1000):
                st.caption("Copy tracks from another playlist")
                others = all_playlists[all_playlists["id"] != pid]
                if others.empty:
                    st.caption("No other playlists yet.")
                else:
                    opts = {r["name"]: int(r["id"]) for _, r in others.iterrows()}
                    src_name = st.selectbox(
                        "Source",
                        list(opts.keys()),
                        key=f"copysrc_{pid}",
                        label_visibility="collapsed",
                    )
                    if st.button(
                        "Copy tracks",
                        key=f"copybtn_{pid}",
                        icon=":material/content_copy:",
                        use_container_width=True,
                    ):
                        added = music_service.copy_playlist_tracks(opts[src_name], pid)
                        st.success(f"Copied {added} new track(s).")
                        st.rerun()

                st.divider()
                st.caption("Export / share")
                _render_export_controls(pid, key_suffix=f"list_{pid}", code_height=200)

                st.divider()
                if st.button(
                    "Delete playlist",
                    key=f"delete_{pid}",
                    icon=":material/delete:",
                    use_container_width=True,
                ):
                    music_service.delete_playlist(pid)
                    st.rerun()


def _render_playlist_list(user_id: int) -> None:
    top1, top2, top3 = st.columns([1, 1, 2], gap="small")
    with top1:
        if st.button("New", icon=":material/add:", use_container_width=True):
            _new_playlist_dialog(user_id)
    with top2:
        if st.button("Import", icon=":material/file_upload:", use_container_width=True):
            _import_playlist_dialog(user_id)
    with top3:
        search = st.text_input(
            "Find by name",
            label_visibility="collapsed",
            placeholder="Search playlists...",
            icon=":material/search:",
        )

    playlists = music_service.get_playlists(user_id)
    if playlists.empty:
        st.info("No playlists yet — create one above.", icon=":material/info:")
        return

    filtered = playlists
    if search.strip():
        filtered = playlists[
            playlists["name"].str.contains(search.strip(), case=False, na=False)
        ]
        if filtered.empty:
            st.caption(f'No playlists match "{search.strip()}".')

    sort_choice = (
        st.segmented_control(
            "Sort by",
            _SORT_OPTIONS,
            default="Newest first",
            key="playlist_sort",
        )
        or "Newest first"
    )
    filtered = _sort_playlists(filtered, sort_choice)

    for _, row in filtered.iterrows():
        with st.container(border=True):
            _render_playlist_row(row, playlists)


# ---------------------------------------------------------------------------
# Playlist detail view
# ---------------------------------------------------------------------------


def _render_play_controls(tracks, key_prefix: str) -> None:
    c1, c2, c3 = st.columns(3, gap="small")
    if c1.button(
        "Play",
        key=f"{key_prefix}_play",
        icon=":material/play_arrow:",
        use_container_width=True,
    ):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Normal")
            st.rerun()
    if c2.button(
        "Shuffle",
        key=f"{key_prefix}_shuffle",
        icon=":material/shuffle:",
        use_container_width=True,
    ):
        if tracks.empty:
            st.warning("This playlist is empty.")
        else:
            _load_queue(tracks, "Shuffle")
            st.rerun()
    if c3.button(
        "Repeat all",
        key=f"{key_prefix}_repeat",
        icon=":material/repeat:",
        use_container_width=True,
    ):
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
    current_mode = (
        st.session_state.get("music_mode", "Normal")
        if st.session_state.get("music_queue")
        else "Normal"
    )
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
    # Same "keep this row on one line" trick as playlist rows.
    with st.container(key=f"trk_row_{playlist_id}_{tid}"):
        tc_title, tc_play, tc_menu = st.columns(
            [6, 1, 1], vertical_alignment="center", gap="small"
        )

        if t.get("artist"):
            tc_title.markdown(f"{t['title']}  \n:gray[{t['artist']}]")
        else:
            tc_title.write(t["title"])

        if tc_play.button(
            "",
            key=f"trackplay_{playlist_id}_{tid}",
            icon=":material/play_arrow:",
            help="Play from here",
            use_container_width=True,
        ):
            _play_track_from_here(tracks_df, tid)

        with tc_menu:
            with st.popover("", icon=":material/more_vert:", use_container_width=True):
                # if st.button(
                #     "Play next",
                #     key=f"tracknext_{playlist_id}_{tid}",
                #     icon=":material/queue_play_next:",
                #     use_container_width=True,
                # ):
                #     _play_track_next(t)

                st.divider()
                st.caption("Artist / lyrics (library-wide)")
                new_artist = st.text_input(
                    "Artist",
                    value=t.get("artist", "") or "",
                    key=f"artist_{playlist_id}_{tid}",
                )
                lc1, lc2 = st.columns([3, 1], vertical_alignment="bottom")
                new_lyrics = lc1.text_input(
                    "Lyrics URL",
                    value=t.get("lyrics_url", "") or "",
                    key=f"lyrics_{playlist_id}_{tid}",
                    placeholder="https://...",
                )
                if lc2.button(
                    "",
                    key=f"trackinfo_save_{playlist_id}_{tid}",
                    icon=":material/save:",
                    help="Save artist & lyrics URL",
                    use_container_width=True,
                ):
                    music_service.update_track_details(
                        tid, artist=new_artist, lyrics_url=new_lyrics
                    )
                    st.rerun()
                if t.get("lyrics_url"):
                    st.link_button(
                        "Open lyrics",
                        f"https://lrclib.net/api/get/" + str(t["lyrics_url"]),
                        icon=":material/lyrics:",
                        use_container_width=True,
                    )

                st.divider()
                is_renamed = t["title"] != t["original_title"]
                st.caption(f"Rename in this playlist (library: {t['original_title']})")
                if is_renamed:
                    rc1, rc2, rc3 = st.columns([3, 1, 1], vertical_alignment="bottom")
                else:
                    rc1, rc2 = st.columns([3, 1], vertical_alignment="bottom")
                    rc3 = None
                new_title = rc1.text_input(
                    "New name",
                    value=t["title"],
                    key=f"renametrack_{playlist_id}_{tid}",
                    label_visibility="collapsed",
                )
                if rc2.button(
                    "",
                    key=f"renametracksave_{playlist_id}_{tid}",
                    icon=":material/save:",
                    help="Save",
                    use_container_width=True,
                ):
                    music_service.rename_track_in_playlist(playlist_id, tid, new_title)
                    st.rerun()
                if is_renamed and rc3.button(
                    "",
                    key=f"renametrackreset_{playlist_id}_{tid}",
                    icon=":material/restart_alt:",
                    help="Reset to library title",
                    use_container_width=True,
                ):
                    music_service.reset_track_title_in_playlist(playlist_id, tid)
                    st.rerun()

                st.divider()
                if st.button(
                    "Remove from playlist",
                    key=f"rm_{playlist_id}_{tid}",
                    icon=":material/delete:",
                    use_container_width=True,
                ):
                    music_service.remove_track_from_playlist(playlist_id, tid)
                    st.rerun()


def _render_add_track(playlist_id: int, user_id: int, existing_ids: set) -> None:
    with st.expander("Add track", icon=":material/add:", expanded=False):
        tab_search, tab_link = st.tabs(
            [":material/search: Search", ":material/link: Paste link"]
        )

        with tab_search:
            with st.form(key=f"search_form_{playlist_id}"):
                sc1, sc2 = st.columns([3, 1], vertical_alignment="bottom")
                query = sc1.text_input(
                    "Search songs",
                    key=f"search_q_{playlist_id}",
                    placeholder="song title or artist...",
                    icon=":material/search:",
                )
                search_clicked = sc2.form_submit_button(
                    "Search", icon=":material/search:", use_container_width=True
                )
            if search_clicked and query.strip():
                with st.spinner("Searching..."):
                    st.session_state[f"search_results_{playlist_id}"] = (
                        ytmusic_search.search_songs(query.strip())
                    )

            results = st.session_state.get(f"search_results_{playlist_id}", [])
            for r in results:
                rc1, rc2, rc3 = st.columns(
                    [1, 4, 1], vertical_alignment="center", gap="small"
                )
                if r["thumbnail_url"]:
                    rc1.image(r["thumbnail_url"], width=56)
                rc2.markdown(f"**{r['title']}**  \n{r['artist']} · {r['duration']}")
                if rc3.button(
                    "",
                    key=f"searchadd_{playlist_id}_{r['video_id']}",
                    icon=":material/add:",
                ):
                    url = f"https://www.youtube.com/watch?v={r['video_id']}"
                    ok, msg, _ = music_service.add_track_and_attach(
                        playlist_id,
                        url,
                        user_id,
                        known_title=r["title"],
                        known_thumbnail=r["thumbnail_url"],
                        known_artist=r["artist"],
                    )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

        with tab_link:
            url = st.text_input(
                "YouTube link",
                key=f"add_url_{playlist_id}",
                placeholder="https://www.youtube.com/watch?v=...",
                icon=":material/link:",
            )
            tc1, tc2 = st.columns([3, 1], vertical_alignment="bottom")
            title_override = tc1.text_input(
                "Title (optional)", key=f"add_title_{playlist_id}"
            )
            if tc2.button(
                "Fetch & add",
                key=f"add_btn_{playlist_id}",
                icon=":material/add:",
                use_container_width=True,
            ):
                if not url.strip():
                    st.warning("Paste a YouTube link first.")
                else:
                    ok, msg, _ = music_service.add_track_and_attach(
                        playlist_id,
                        url.strip(),
                        user_id,
                        known_title=title_override.strip() or None,
                    )
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

        library = music_service.get_all_tracks()
        addable = (
            library[~library["id"].isin(existing_ids)] if not library.empty else library
        )
        if addable is not None and not addable.empty:
            opts = {r["title"]: r["id"] for _, r in addable.iterrows()}
            pc1, pc2 = st.columns([3, 1], vertical_alignment="bottom")
            pick = pc1.selectbox(
                "Or add from your library",
                ["—"] + list(opts.keys()),
                key=f"pick_{playlist_id}",
            )
            if pick != "—" and pc2.button(
                "Add selected",
                key=f"add_lib_{playlist_id}",
                icon=":material/add:",
                use_container_width=True,
            ):
                music_service.add_track_to_playlist(playlist_id, opts[pick])
                st.rerun()


def _render_export_controls(
    playlist_id: int, key_suffix: str, code_height: int | None = None
) -> None:
    fc1, fc2 = st.columns([3, 1], vertical_alignment="bottom")
    fmt = (
        fc1.segmented_control(
            "Format",
            ["JSON", "Plain text"],
            default="JSON",
            key=f"export_fmt_{key_suffix}",
        )
        or "JSON"
    )
    content = (
        music_service.export_playlist_json(playlist_id)
        if fmt == "JSON"
        else music_service.export_playlist_text(playlist_id)
    )
    with fc2:
        st.download_button(
            "",
            data=content,
            file_name=f"playlist.{'json' if fmt == 'JSON' else 'txt'}",
            mime="application/json" if fmt == "JSON" else "text/plain",
            icon=":material/download:",
            key=f"export_dl_{key_suffix}",
            width="content"
        )
    st.code(
        content,
        language=("json" if fmt == "JSON" else None),
        wrap_lines=True,
        height=code_height,
        width=500
    )


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

    name_col, save_col = st.columns([4, 1], vertical_alignment="bottom", gap="small")
    new_name = name_col.text_input(
        "Playlist name",
        value=current_name,
        key=f"rename_input_{playlist_id}",
        icon=":material/edit:",
    )
    if save_col.button(
        "Save",
        key=f"rename_save_{playlist_id}",
        icon=":material/save:",
        use_container_width=True,
    ):
        if new_name.strip() and new_name.strip() != current_name:
            music_service.rename_playlist(playlist_id, new_name.strip())
            st.rerun()

    tracks = music_service.get_playlist_tracks(playlist_id)
    existing_ids = set(tracks["id"]) if not tracks.empty else set()

    _render_play_controls(tracks, key_prefix=f"detail_{playlist_id}")

    add_col, export_col = st.columns(2, gap="small")
    with add_col:
        _render_add_track(playlist_id, user_id, existing_ids)
    with export_col:
        with st.expander("Export / share", icon=":material/ios_share:", expanded=False):
            _render_export_controls(playlist_id, key_suffix=f"detail_{playlist_id}")

    if tracks.empty:
        st.caption("No tracks yet — add some above.")
        return

    track_search = st.text_input(
        "Find track by name",
        key=f"track_search_{playlist_id}",
        placeholder="Find a track by name...",
        icon=":material/search:",
        label_visibility="collapsed",
    )
    display_tracks = tracks
    if track_search.strip():
        display_tracks = tracks[
            tracks["title"].str.contains(track_search.strip(), case=False, na=False)
        ]

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
        st.warning(
            "Log in first (see the Login tab) to build playlists and listen to music.",
            icon=":material/lock:",
        )
        return

    view = st.session_state.get("music_view", "list")
    if view == "detail" and st.session_state.get("music_selected_playlist_id"):
        _render_playlist_detail(user_id, st.session_state["music_selected_playlist_id"])
    else:
        _render_playlist_list(user_id)
