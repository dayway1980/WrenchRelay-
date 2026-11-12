# WrenchRelay YouTube Uploader

This is a standalone, mobile-friendly browser app under tools/youtube-uploader. It does NOT modify or replace the WrenchRelay maintenance application. No client secret, API key, downloaded JSON file, or cloud billing is needed for this upload path.

## One-time Google setup
1. In project gen-lang-client-0498496877, enable YouTube Data API v3.
2. In Google Auth Platform, choose External audience and add the channel owner's Gmail as a test user if the app is in Testing.
3. In Clients, create an OAuth Client ID with Application type: Web application.
4. Under Authorized JavaScript origins, add the exact deployed HTTPS origin, with no trailing slash or path. The Google Identity Services token pop-up does not require a redirect URI.
5. Use the public Client ID ending in .apps.googleusercontent.com inside the uploader. Never share or enter the client secret or downloaded JSON.
6. Connect Google, grant the YouTube upload scope, select MP4, keep Unlisted if the contest permits, upload, and copy the video URL.

## Security and functionality
- Uses official Google Identity Services token model and the least-privilege youtube.upload scope.
- OAuth token stays in browser memory only. The public Client ID may be remembered in localStorage; there are no backend secrets.
- Direct, chunked resumable YouTube Data API upload; confirms success only when YouTube returns a video ID.
- Does not automatically post publicly: defaults to Unlisted.
- This prototype requires a live Google OAuth client and owner authorization; real-account authorization and an upload have not yet been tested.
- If sign-in or upload fails, use YouTube Studio to upload the MP4 without developer setup.
- The current version does not persist an interrupted upload session across page refreshes.

References:
https://developers.google.com/identity/oauth2/web/guides/use-token-model
https://developers.google.com/youtube/data/guides/implementation/videos
https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol
https://support.google.com/youtube/answer/57407?co=GENIE.Platform%3DAndroid