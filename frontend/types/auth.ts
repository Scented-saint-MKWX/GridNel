export type Role = "tracker" | "analyst";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface JwtPayload {
  sub: string;
  role: Role;
  exp: number;
}

export interface AuthState {
  token: string | null;
  payload: JwtPayload | null;
}
