export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type MovieType = "movie" | "series" | "episode";

export interface Movie {
  id: string;
  imdb_id: string;
  title: string;
  year: string;
  type: MovieType;
  rated: string;
  runtime_minutes: number | null;
  genre: string;
  director: string;
  actors: string;
  plot: string;
  poster_url: string;
  imdb_rating: string | null;
  created_at: string;
  updated_at: string;
}

export type VideoStatus = "pending" | "processing" | "ready" | "failed";
export type VideoVisibility = "public" | "private";
export type SubtitleLanguage = "fr" | "en";

export interface Subtitle {
  id: string;
  language: SubtitleLanguage;
  label: string;
  url: string;
}

export interface Video {
  id: string;
  title: string;
  description: string;
  visibility: VideoVisibility;
  status: VideoStatus;
  owner_email: string;
  movie: string | null;
  thumbnail: string | null;
  duration_seconds: number | null;
  hls_master_playlist: string;
  renditions: Record<string, string>;
  subtitles: Subtitle[];
  error_message: string;
  created_at: string;
  updated_at: string;
}

export type LiveStatus = "scheduled" | "live" | "ended" | "canceled";
export type LiveVisibility = "public" | "private";

export interface LiveReplay {
  id: string;
  status: VideoStatus;
  thumbnail: string | null;
  duration_seconds: number | null;
  hls_master_playlist: string;
}

export interface LiveStream {
  id: string;
  title: string;
  description: string;
  visibility: LiveVisibility;
  status: LiveStatus;
  owner_email: string;
  scheduled_at: string | null;
  scheduled_duration_minutes: number;
  started_at: string | null;
  ended_at: string | null;
  hls_playback_url: string;
  replay: LiveReplay | null;
  created_at: string;
}

export type UserRole = "user" | "admin" | "moderator" | "creator" | "company";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone_number: string;
  avatar: string | null;
  role: UserRole;
  is_email_verified: boolean;
  two_factor_enabled: boolean;
  date_joined: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResult {
  user?: User;
  access?: string;
  refresh?: string;
  two_factor_required?: boolean;
  pre_auth_token?: string;
}

export interface Comment {
  id: string;
  author_email: string;
  content: string;
  created_at: string;
}

export interface Post {
  id: string;
  author_id: string;
  author_email: string;
  content: string;
  image: string | null;
  likes_count: number;
  comments_count: number;
  is_liked_by_me: boolean;
  created_at: string;
}

export interface Message {
  id: string;
  sender_email: string;
  content: string;
  attachment: string | null;
  is_read_by_me: boolean;
  created_at: string;
}

export interface UserSearchResult {
  id: string;
  email: string;
  full_name: string;
  avatar: string | null;
}

export interface Conversation {
  id: string;
  participant_emails: string[];
  last_message: Message | null;
  created_at: string;
  updated_at: string;
}

export type WatchPartyStatus = "scheduled" | "live" | "ended" | "canceled";
export type WatchPartyMyStatus = "host" | "moderator" | "member" | "pending" | "rejected" | null;

export interface WatchParty {
  id: string;
  host_email: string;
  display_title: string;
  title: string;
  video_title: string;
  video_thumbnail: string | null;
  scheduled_at: string;
  status: WatchPartyStatus;
  member_count: number;
  my_status: WatchPartyMyStatus;
  video: Video | null;
  current_position_seconds: number | null;
  is_playing: boolean;
  created_at: string;
}

export type WatchPartyMembershipRole = "member" | "moderator";
export type WatchPartyMembershipStatus = "pending" | "accepted" | "rejected";

export interface WatchPartyMembership {
  id: string;
  user_email: string;
  role: WatchPartyMembershipRole;
  status: WatchPartyMembershipStatus;
  created_at: string;
}

export interface WatchPartyChatMessage {
  id: string;
  user_email: string;
  message: string;
  created_at: string;
}

export type PageType = "landing" | "blog" | "faq" | "legal";

export interface CmsPage {
  id: string;
  title: string;
  slug: string;
  page_type: PageType;
  content: string;
  meta_title: string;
  meta_description: string;
  author_email: string;
  published_at: string | null;
  created_at: string;
}

export type NotificationCategory = "info" | "comment" | "live" | "message" | "system";

export interface AppNotification {
  id: string;
  category: NotificationCategory;
  title: string;
  body: string;
  link: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface DashboardOverview {
  users: {
    total: number;
    new_last_30_days: number;
    by_role: Record<string, number>;
  };
  videos: {
    total: number;
    ready: number;
    processing: number;
  };
  live: {
    total: number;
    currently_live: number;
  };
  community: {
    posts: number;
  };
  messaging: {
    messages: number;
  };
}

export interface WatchlistItem {
  id: string;
  movie: Movie;
  created_at: string;
}

export interface SearchResults {
  query: string;
  movies: Movie[];
  videos: Video[];
  live_streams: LiveStream[];
  posts: unknown[];
}

export type AdCreativeType = "video" | "image";
export type AdPlacement = "pre_roll";

export interface Ad {
  id: string;
  title: string;
  creative_type: AdCreativeType;
  placement: AdPlacement;
  video_file: string | null;
  image: string | null;
  duration_seconds: number | null;
  click_url: string;
}
