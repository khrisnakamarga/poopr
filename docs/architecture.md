# Architecture

Poopr is intentionally split into a mobile-first React client and a FastAPI backend so the API can later support native mobile clients without rewriting the core product.

## Core Domains

- Profiles: user-facing display data and timezone preferences.
- Poop logs: user-owned timestamped events with optional details.
- Reports: aggregate statistics derived from poop logs.
- Groups: invite-code communities with memberships and roles.
- Activity: group-visible events created from member poop logs.

## Privacy Model

Detailed logs belong to the user. Group dashboards expose aggregate statistics, rankings, and activity rows visible to group members. API handlers must always scope reads by the authenticated user or by groups where the user is a member.

## Production Auth

The development API uses `X-User-Email` to make local testing easy. Production uses the backend-owned `/auth/google/login` and `/auth/google/callback` routes, with Azure Container Apps built-in auth disabled on the public frontend. The frontend proxies `/.auth/login/google/callback` to the backend callback so the production redirect URI remains stable.

The callback exchanges the Google code server-side, validates the ID token audience, creates a signed `poopr_session` cookie, and redirects to `/`. API handlers accept that signed session cookie before falling back to Azure Easy Auth headers for compatibility.

