import { API_BASE_URL, SERVER_FORWARDED_HEADERS } from "@/lib/config";
import type {
  Ad,
  AdPlacement,
  AppNotification,
  AuthTokens,
  CmsPage,
  Comment,
  Conversation,
  DashboardOverview,
  LiveStream,
  LoginResult,
  Message,
  Movie,
  Paginated,
  PageType,
  Post,
  SearchResults,
  Subtitle,
  WatchlistItem,
  User,
  UserSearchResult,
  Video,
  WatchParty,
  WatchPartyChatMessage,
  WatchPartyMembership,
} from "@/lib/types";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

export function formatApiError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  const { detail } = err;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const obj = detail as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    const firstValue = Object.values(obj)[0];
    if (Array.isArray(firstValue) && typeof firstValue[0] === "string") return firstValue[0];
    if (typeof firstValue === "string") return firstValue;
  }
  return fallback;
}

async function request<T>(
  path: string,
  init?: RequestInit & { token?: string },
): Promise<T> {
  const headers = new Headers(init?.headers);
  for (const [name, value] of Object.entries(SERVER_FORWARDED_HEADERS)) {
    headers.set(name, value);
  }
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  if (init?.token) {
    headers.set("Authorization", `Bearer ${init.token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (res.status === 205 || res.status === 204) {
    return undefined as T;
  }

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    throw new ApiError(res.status, payload ?? res.statusText);
  }

  return payload as T;
}

// ---- Public catalog ----

export function getMovies(
  params: {
    q?: string;
    page?: number;
    type?: "movie" | "series" | "episode";
    genre?: string;
    ordering?: "imdb_rating" | "-imdb_rating" | "created_at" | "-created_at";
  } = {},
) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.page) search.set("page", String(params.page));
  if (params.type) search.set("type", params.type);
  if (params.genre) search.set("genre", params.genre);
  if (params.ordering) search.set("ordering", params.ordering);
  const qs = search.toString();
  return request<Paginated<Movie>>(`/api/v1/catalog/movies/${qs ? `?${qs}` : ""}`);
}

export function getMovie(id: string) {
  return request<Movie>(`/api/v1/catalog/movies/${id}/`);
}

export function getMovieRecommendations(id: string) {
  return request<Paginated<Movie>>(`/api/v1/catalog/movies/${id}/recommendations/`);
}

export function search(q: string) {
  return request<SearchResults>(`/api/v1/search/?q=${encodeURIComponent(q)}`);
}

// ---- Live ----

export function getLiveStreams() {
  return request<Paginated<LiveStream>>("/api/v1/live/streams/");
}

export function getLiveStream(id: string, token?: string) {
  return request<LiveStream>(`/api/v1/live/streams/${id}/`, { token });
}

// ---- Dashboard (admin) ----

export function getDashboardOverview(token: string) {
  return request<DashboardOverview>("/api/v1/dashboard/overview/", { token });
}

// ---- Communauté ----

export function getPosts(token: string, page?: number) {
  const qs = page ? `?page=${page}` : "";
  return request<Paginated<Post>>(`/api/v1/community/posts/${qs}`, { token });
}

export function getPost(id: string, token: string) {
  return request<Post>(`/api/v1/community/posts/${id}/`, { token });
}

// La création ne renvoie que id/content/image (PostCreateSerializer côté backend) —
// pas le Post complet (author, compteurs...) que renvoie la liste/le détail.
export type CreatedPost = Pick<Post, "id" | "content" | "image">;

export function createPost(payload: { content: string; image?: File }, token: string) {
  if (payload.image) {
    const form = new FormData();
    form.set("content", payload.content);
    form.set("image", payload.image);
    return request<CreatedPost>("/api/v1/community/posts/", { method: "POST", body: form, token });
  }
  return request<CreatedPost>("/api/v1/community/posts/", {
    method: "POST",
    body: JSON.stringify({ content: payload.content }),
    token,
  });
}

export function deletePost(id: string, token: string) {
  return request<void>(`/api/v1/community/posts/${id}/`, { method: "DELETE", token });
}

export function togglePostLike(id: string, token: string) {
  return request<{ liked: boolean; likes_count: number }>(`/api/v1/community/posts/${id}/like/`, {
    method: "POST",
    token,
  });
}

export function getComments(postId: string, token: string) {
  return request<Paginated<Comment>>(`/api/v1/community/posts/${postId}/comments/`, { token });
}

// La création ne renvoie que id/content (CommentCreateSerializer côté backend) — pas le
// Comment complet (auteur, date...) que renvoie la liste.
export type CreatedComment = Pick<Comment, "id" | "content">;

export function createComment(postId: string, content: string, token: string) {
  return request<CreatedComment>(`/api/v1/community/posts/${postId}/comments/`, {
    method: "POST",
    body: JSON.stringify({ content }),
    token,
  });
}

export function deleteComment(id: string, token: string) {
  return request<void>(`/api/v1/community/comments/${id}/`, { method: "DELETE", token });
}

// ---- Messagerie ----

export function getConversations(token: string) {
  return request<Paginated<Conversation>>("/api/v1/messaging/conversations/", { token });
}

export function createConversation(participantIds: string[], token: string) {
  return request<Conversation>("/api/v1/messaging/conversations/", {
    method: "POST",
    body: JSON.stringify({ participant_ids: participantIds }),
    token,
  });
}

export function getMessages(conversationId: string, token: string) {
  return request<Paginated<Message>>(`/api/v1/messaging/conversations/${conversationId}/messages/`, { token });
}

export function markConversationRead(conversationId: string, token: string) {
  return request<{ detail: string; marked_read: number }>(
    `/api/v1/messaging/conversations/${conversationId}/read/`,
    { method: "POST", token },
  );
}

// ---- Visionnage entre amis (watch parties) ----

export function getWatchPartySuggestions(token: string) {
  return request<Movie[]>("/api/v1/watchparty/suggestions/", { token });
}

export function getWatchParties(token: string) {
  return request<Paginated<WatchParty>>("/api/v1/watchparty/parties/", { token });
}

export function createWatchParty(payload: { video: string; title?: string; scheduled_at: string }, token: string) {
  return request<WatchParty>("/api/v1/watchparty/parties/", {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}

export function getWatchParty(id: string, token: string) {
  return request<WatchParty>(`/api/v1/watchparty/parties/${id}/`, { token });
}

export function joinWatchParty(id: string, token: string) {
  return request<WatchPartyMembership>(`/api/v1/watchparty/parties/${id}/join/`, { method: "POST", token });
}

export function getWatchPartyMembers(id: string, token: string) {
  return request<Paginated<WatchPartyMembership>>(`/api/v1/watchparty/parties/${id}/members/`, { token });
}

export function acceptWatchPartyMember(partyId: string, memberId: string, token: string) {
  return request<WatchPartyMembership>(
    `/api/v1/watchparty/parties/${partyId}/members/${memberId}/accept/`,
    { method: "POST", token },
  );
}

export function rejectWatchPartyMember(partyId: string, memberId: string, token: string) {
  return request<WatchPartyMembership>(
    `/api/v1/watchparty/parties/${partyId}/members/${memberId}/reject/`,
    { method: "POST", token },
  );
}

export function promoteWatchPartyMember(partyId: string, memberId: string, token: string) {
  return request<WatchPartyMembership>(
    `/api/v1/watchparty/parties/${partyId}/members/${memberId}/promote/`,
    { method: "POST", token },
  );
}

export function startWatchParty(id: string, token: string) {
  return request<WatchParty>(`/api/v1/watchparty/parties/${id}/start/`, { method: "POST", token });
}

export function endWatchParty(id: string, token: string) {
  return request<WatchParty>(`/api/v1/watchparty/parties/${id}/end/`, { method: "POST", token });
}

export function cancelWatchParty(id: string, token: string) {
  return request<WatchParty>(`/api/v1/watchparty/parties/${id}/cancel/`, { method: "POST", token });
}

export function getWatchPartyChatHistory(id: string, token: string) {
  return request<Paginated<WatchPartyChatMessage>>(`/api/v1/watchparty/parties/${id}/chat/`, { token });
}

// ---- Videos (require auth) ----

export function getVideosByMovie(movieId: string, token: string) {
  return request<Paginated<Video>>(`/api/v1/videos/?movie=${movieId}`, { token });
}

export function getVideo(id: string, token: string) {
  return request<Video>(`/api/v1/videos/${id}/`, { token });
}

export function uploadSubtitle(
  videoId: string,
  payload: { language: "fr" | "en"; file: File },
  token: string,
) {
  const form = new FormData();
  form.set("language", payload.language);
  form.set("file", payload.file);
  return request<Subtitle>(`/api/v1/videos/${videoId}/subtitles/`, { method: "POST", body: form, token });
}

export function deleteSubtitle(subtitleId: string, token: string) {
  return request<void>(`/api/v1/videos/subtitles/${subtitleId}/`, { method: "DELETE", token });
}

// ---- Ma liste & historique de visionnage ----

export function getWatchlist(token: string) {
  return request<Paginated<WatchlistItem>>("/api/v1/library/watchlist/", { token });
}

export function toggleWatchlist(movieId: string, token: string) {
  return request<{ in_watchlist: boolean }>("/api/v1/library/watchlist/toggle/", {
    method: "POST",
    body: JSON.stringify({ movie_id: movieId }),
    token,
  });
}

export function getWatchlistStatus(movieId: string, token: string) {
  return request<{ in_watchlist: boolean }>(`/api/v1/library/watchlist/status/${movieId}/`, { token });
}

export function updateWatchHistory(videoId: string, positionSeconds: number, token: string) {
  return request<{ position_seconds: number }>("/api/v1/library/history/", {
    method: "POST",
    body: JSON.stringify({ video: videoId, position_seconds: Math.floor(positionSeconds) }),
    token,
  });
}

export function getWatchHistory(videoId: string, token: string) {
  return request<{ position_seconds: number }>(`/api/v1/library/history/${videoId}/`, { token });
}

// ---- Auth ----

export function registerAccount(payload: {
  email: string;
  password: string;
  password_confirm: string;
  full_name?: string;
}) {
  return request<{ detail: string; user: User }>("/api/v1/accounts/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { email: string; password: string }) {
  return request<LoginResult>("/api/v1/accounts/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginTwoFactor(payload: {
  pre_auth_token: string;
  code: string;
  device_name?: string;
}) {
  return request<LoginResult>("/api/v1/accounts/login/2fa/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function refreshAccessToken(refresh: string) {
  return request<AuthTokens>("/api/v1/accounts/token/refresh/", {
    method: "POST",
    body: JSON.stringify({ refresh }),
  });
}

export function logout(refresh: string, accessToken: string) {
  return request<void>("/api/v1/accounts/logout/", {
    method: "POST",
    body: JSON.stringify({ refresh }),
    token: accessToken,
  });
}

export function getMe(accessToken: string) {
  return request<User>("/api/v1/accounts/me/", { token: accessToken });
}

export function searchUsers(q: string, token: string) {
  return request<Paginated<UserSearchResult>>(`/api/v1/accounts/search/?q=${encodeURIComponent(q)}`, { token });
}

// ---- Pages CMS ----

export function getPages(params: { type?: PageType } = {}) {
  const qs = params.type ? `?type=${params.type}` : "";
  return request<Paginated<CmsPage>>(`/api/v1/cms/pages/${qs}`);
}

export function getPage(slug: string) {
  return request<CmsPage>(`/api/v1/cms/pages/${slug}/`);
}

// ---- Notifications ----

export function getNotifications(token: string, unreadOnly = false) {
  const qs = unreadOnly ? "?unread=true" : "";
  return request<Paginated<AppNotification>>(`/api/v1/notifications/${qs}`, { token });
}

export function getUnreadNotificationCount(token: string) {
  return request<{ unread_count: number }>("/api/v1/notifications/unread-count/", { token });
}

export function markNotificationRead(id: string, token: string) {
  return request<AppNotification>(`/api/v1/notifications/${id}/read/`, { method: "POST", token });
}

export function markAllNotificationsRead(token: string) {
  return request<{ marked_read: number }>("/api/v1/notifications/read-all/", { method: "POST", token });
}

// ---- Publicités ----

export function getNextAd(placement: AdPlacement = "pre_roll") {
  return request<Ad | undefined>(`/api/v1/ads/next/?placement=${placement}`);
}
