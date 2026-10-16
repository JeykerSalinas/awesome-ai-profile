# Deployment profiles

The same frontend source can be built twice. Set `VITE_PROFILE_ID=jeyker` (default) for the existing deployment, and `VITE_PROFILE_ID=sara` for Sara. Vite embeds this public value at **build time**; changing Azure runtime settings after building does not change the static bundle.

For local testing, run from `app/`:

```sh
VITE_PROFILE_ID=sara npm run dev
```

For each Azure Static Web Apps deployment, provide its own deployment token and build environment with `VITE_PROFILE_ID` and `VITE_API_BASE_URL`. Keep the existing deployment on the default profile. Add Sara's frontend origin to backend `CORS_ALLOW_ORIGINS` and the Container App ingress CORS policy if enabled. This PR prepares the application; it does not provision or publish a second Azure resource.

## Frontend

`app/src/config/profile.ts` owns assistant name, logo, avatars, and CSS custom-property overrides. Sara currently has a letter avatar and the existing palette, pending usable brand assets. Populate `logo`, `avatar`, `avatarDark`, and `colors` when available. Existing CSS tokens (including light/dark surface tokens) can be overridden via `colors`. No inferred palette or invented logo is included.

The selected profile is sent as `profile_id` in chat JSON and the initial voice message, and as a query parameter on PDF upload/delete. Notice, language, tour and voice-usage browser keys are separated by profile while retaining existing Jeyker keys.

## Backend

`services/profile_service.py` is the server-owned allowlist. Missing IDs retain Jeyker for existing clients; unknown IDs fail validation. Tools bind the profile outside model-controlled tool arguments. Voice uses the same identity, facts, tools and greeting.

Jeyker's existing knowledge remains in `backend/knowledge`. Sara's lives in `backend/profiles/sara/knowledge`. Sara's biography, experience, skills, projects and contact are deliberately empty until supplied. The assistant must say that verified information is unavailable; Jeyker's facts and photo are never used as a fallback.

Each profile has separate persistent Chroma and temporary upload collections, service instances and upload-expiration maps. Uploaded document IDs remain conversation capabilities within that profile. A profile ID is public routing configuration, **not authentication or authorization**; both professional portfolios are public.

## Validation

The profile CI workflow builds both frontend profiles, runs frontend tests and backend tests without production model credentials. Check its results before merging. No production deployment is required for these tests.
