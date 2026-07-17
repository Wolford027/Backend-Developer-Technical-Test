export interface Link {
  code: string;
  short_url: string;
  long_url: string;
  click_count: number;
  created_at: string;
  expires_at: string | null;
}

export interface LinkInput {
  url: string;
  expires_in_days?: number | null;
}
