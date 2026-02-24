export interface User {
  id: number;
  username: string | null;
  full_name: string;
  is_admin: boolean;
  points: number;
  visit_count: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  full_name: string;
  username: string | null;
  points: number;
  visit_count: number;
  bath_count: number;
}

export interface Bath {
  id: number;
  name: string;
  aliases: string[];
  country_id: number | null;
  region_id: number | null;
  city: string | null;
  lat: number | null;
  lng: number | null;
  description: string | null;
  url: string | null;
  is_archived: boolean;
  canonical_id: number | null;
  created_at: string;
}

export interface PointLog {
  user_id: number;
  points: number;
  reason: string;
}

export interface VisitParticipant {
  id: number;
  full_name: string;
  username: string | null;
}

export interface Visit {
  id: number;
  status: string;
  visited_at: string;
  created_at: string;
  flag_long: boolean;
  flag_ultraunique: boolean;
  bath: Pick<Bath, "id" | "name" | "city" | "country_id" | "region_id"> | null;
  participants: VisitParticipant[];
  point_logs: PointLog[];
  total_points: number;
}

export interface Country {
  id: number;
  name: string;
  code: string | null;
}

export interface Region {
  id: number;
  name: string;
  country_id: number | null;
}

export interface PointConfig {
  [key: string]: { value: number; description: string };
}

export type Period = "year" | "month" | "week" | "all";
