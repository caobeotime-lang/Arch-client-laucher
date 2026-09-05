"""
Microsoft/Minecraft account login, reusing minecraft_launcher_lib the same
way the PC version already depends on it for this exact purpose.

IMPORTANT / honest limitation: PLAY NOW in this app hands off to
PojavLauncher to actually run the game, and Pojav has its own separate,
self-contained Microsoft login inside it -- there is no public API for
another app to inject a token into Pojav. So this module gets you a real,
valid Minecraft account (verifies ownership, fetches name/uuid/token) for
display and for any future direct-launch feature, but it does NOT log you
into Pojav automatically today. You still log in once inside Pojav itself
to actually play online.

You must supply your own Azure App registration (CLIENT_ID) -- this is a
Microsoft requirement for every custom launcher, the PC version needed one
too. Register one for free at https://portal.azure.com (App registrations),
add "https://login.microsoftonline.com/common/oauth2/nativeclient" as a
redirect URI, and enable "public client / native" flows.
"""

import minecraft_launcher_lib

DEFAULT_REDIRECT_URL = "https://login.microsoftonline.com/common/oauth2/nativeclient"


class LoginSession:
    def __init__(self, client_id, redirect_url=DEFAULT_REDIRECT_URL):
        self.client_id = client_id
        self.redirect_url = redirect_url
        self._state = None
        self._code_verifier = None

    def start(self):
        """Returns the URL to open in a browser for the user to sign in."""
        login_url, state, code_verifier = minecraft_launcher_lib.microsoft_account.get_secure_login_data(
            self.client_id, self.redirect_url
        )
        self._state = state
        self._code_verifier = code_verifier
        return login_url

    def complete(self, redirected_url):
        """
        Call with the full URL the browser landed on after sign-in (the
        user copies it back into the app -- same manual-paste step the PC
        version's login flow uses).
        """
        auth_code = minecraft_launcher_lib.microsoft_account.parse_auth_code_url(
            redirected_url, self._state
        )
        login_data = minecraft_launcher_lib.microsoft_account.complete_login(
            self.client_id, None, self.redirect_url, auth_code, self._code_verifier
        )
        return {
            "name": login_data["name"],
            "uuid": login_data["id"],
            "access_token": login_data["access_token"],
        }
