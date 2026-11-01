export type * from "./generated";

export type ServiceHealth = { status: string; version: string };

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, string>;
  };
};
