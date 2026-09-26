"""
Microsoft / Xbox Live profile login.

IMPORTANT / honest limitation: Bedrock Edition has no separate "Minecraft
account" system like Java Edition does -- it signs in with Xbox Live
directly, inside the game itself, and there is no public API for another
app to inject a session into it. So this module does NOT log you into
Minecraft. What it does is the same "Sign in with Xbox" flow lots of
fan-made stat trackers and companion apps use: standard Microsoft OAuth2
+ documented Xbox Live token exchange, ending in your public Xbox profile
(gamertag, XUID, gamerpic). It never touches game files, ownership, or
licensing -- it's read-only identity, same as "Sign in with Google" on any
other app.

You must supply your own Azure App registration (CLIENT_ID) -- a free,
required step for any custom Microsoft sign-in, same as the Java Edition
launcher needed. Register one at https://portal.azure.com (App
registrations -> New registration), add
"https://login.microsoftonline.com/common/oauth2/nativeclient" as a
"Mobile and desktop applications" redirect URI, and under
Authentication -> Advanced settings enable "Allow public client flows".
"""

import requests

REDIRECT_URL = "https://login.microsoftonline.com/common/oauth2/nativeclient"
OAUTH_AUTHORIZE_URL = "https://login.live.com/oauth20_authorize.srf"
OAUTH_TOKEN_URL = "https://login.live.com/oauth20_token.srf"
XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
PROFILE_URL = (
    "https://profile.xboxlive.com/users/me/profile/settings"
    "?settings=GameDisplayName,GameDisplayPicRaw,Gamertag,XboxOneRep"
)


class XboxLoginError(Exception):
    pass


class LoginSession:
    def __init__(self, client_id, redirect_url=REDIRECT_URL):
        self.client_id = client_id
        self.redirect_url = redirect_url

    def start(self):
        """Returns the URL to open in a browser for the user to sign in."""
        from urllib.parse import urlencode
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_url,
            "scope": "XboxLive.signin offline_access",
        }
        return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    def complete(self, redirected_url):
        """
        Call with the full URL the browser landed on after sign-in (the
        user copies it back into the app, same manual-paste step the Java
        Edition launcher's login flow already uses).
        """
        from urllib.parse import urlparse, parse_qs
        query = parse_qs(urlparse(redirected_url).query)
        if "error" in query:
            raise XboxLoginError(query.get("error_description", query["error"])[0])
        if "code" not in query:
            raise XboxLoginError("No authorization code found in that URL.")
        auth_code = query["code"][0]

        ms_token = self._exchange_code_for_token(auth_code)
        xbl_token, uhs = self._authenticate_xbl(ms_token)
        xsts_token, uhs = self._authorize_xsts(xbl_token)
        profile = self._fetch_profile(xsts_token, uhs)
        return profile

    def _exchange_code_for_token(self, auth_code):
        resp = requests.post(
            OAUTH_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_url,
                "scope": "XboxLive.signin offline_access",
            },
            timeout=15,
        )
        if not resp.ok:
            raise XboxLoginError(f"Microsoft token exchange failed: {resp.text[:200]}")
        return resp.json()["access_token"]

    def _authenticate_xbl(self, ms_access_token):
        resp = requests.post(
            XBL_AUTH_URL,
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": f"d={ms_access_token}",
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15,
        )
        if not resp.ok:
            raise XboxLoginError(f"Xbox Live authentication failed: {resp.text[:200]}")
        data = resp.json()
        return data["Token"], data["DisplayClaims"]["xui"][0]["uhs"]

    def _authorize_xsts(self, xbl_token):
        resp = requests.post(
            XSTS_AUTH_URL,
            json={
                "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                "RelyingParty": "http://xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            raise XboxLoginError(
                "This Microsoft account has no Xbox Live profile yet -- sign in "
                "at xbox.com once with it first, then try again."
            )
        if not resp.ok:
            raise XboxLoginError(f"XSTS authorization failed: {resp.text[:200]}")
        data = resp.json()
        return data["Token"], data["DisplayClaims"]["xui"][0]["uhs"]

    def _fetch_profile(self, xsts_token, uhs):
        resp = requests.get(
            PROFILE_URL,
            headers={
                "Authorization": f"XBL3.0 x={uhs};{xsts_token}",
                "x-xbl-contract-version": "3",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if not resp.ok:
            raise XboxLoginError(f"Fetching Xbox profile failed: {resp.text[:200]}")
        settings = {
            s["id"]: s["value"]
            for s in resp.json()["profileUsers"][0]["settings"]
        }
        return {
            "gamertag": settings.get("Gamertag", "?"),
            "display_name": settings.get("GameDisplayName", ""),
            "xuid": resp.json()["profileUsers"][0]["id"],
            "gamerpic_url": settings.get("GameDisplayPicRaw", ""),
        }
