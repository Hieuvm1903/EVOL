export type Track = {
  id?: number;
  title: string;
  video_id: string;
  thumbnail_url?: string;
  artist?: string | null;
  lyrics_url?: string | null;
};export type Mode = "normal" | "shuffle" | "repeatTrack" | "repeatAll";
export type View = "video" | "lyrics";