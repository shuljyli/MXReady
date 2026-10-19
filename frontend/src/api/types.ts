export type * from "./generated";

// Minimal shape of GET /api/rules; the frontend only uses the rule count.
export type RuleCatalog = {
  version: string;
  rules: { id: string }[];
};

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    details: Record<string, string>;
  };
};
