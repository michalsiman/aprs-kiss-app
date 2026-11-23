"""Where this copy of the app comes from; the release workflow writes "play" into the Google Play build.

Google Play does not allow an app to update itself from elsewhere, so that build has no new-version
check and no download of the .apk: Google Play updates it.
"""

CHANNEL = "github"


def store_updates() -> bool:
    """True when a store (Google Play) installs the updates, not the app itself."""
    return CHANNEL == "play"
