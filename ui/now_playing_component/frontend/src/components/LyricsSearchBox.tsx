import React from "react";
import { Button, Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";

interface Props {
  title: string; onTitleChange: (v: string) => void;
  artist: string; onArtistChange: (v: string) => void;
  searching: boolean;
  onSearch: () => void;
}

export default function LyricsSearchBox({ title, onTitleChange, artist, onArtistChange, searching, onSearch }: Props) {
  return (
    <div className="lyrics-search-row">
      <Input size="small" placeholder="Song name" value={title} onChange={(e) => onTitleChange(e.target.value)} onPressEnter={onSearch} />
      <Input size="small" placeholder="Artist (optional)" value={artist} onChange={(e) => onArtistChange(e.target.value)} onPressEnter={onSearch} />
      <Button size="small" icon={<SearchOutlined />} loading={searching} onClick={onSearch} disabled={!title.trim()} />
    </div>
  );
}