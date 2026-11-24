"""A notification on Android (through pyjnius): a tap opens the app.

Used when the app runs in the background and has something to ask (you seem to be driving: switch the
tracker on?). Android 13 and newer want the "notifications" permission, asked for while the app is on
screen. Anywhere else this does nothing.
"""

from __future__ import annotations

import logging
import os

_LOGGER = logging.getLogger(__name__)

CHANNEL = "aprs_kiss_ask"
NOTIFICATION_ID = 4242
PERMISSION = "android.permission.POST_NOTIFICATIONS"
SMALL_ICON = "ic_stat_aprs"  # src/android_res/drawable: white on clear, as the status bar wants it
GEOLOCATOR_NOTIFICATION_ID = 75415  # geolocator_android's foreground service ("Running: …")


def _activity():
    import jnius  # noqa: PLC0415 - only on Android

    host = os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
    if not host:
        raise OSError("no Android activity")
    return jnius, jnius.autoclass(host).mActivity


def _sdk() -> int:
    import jnius  # noqa: PLC0415

    return jnius.autoclass("android.os.Build$VERSION").SDK_INT


def ask_permission() -> None:
    """Android 13+: ask for notifications once (the app must be on screen)."""
    try:
        jnius, activity = _activity()
        if _sdk() < 33:
            return
        granted = jnius.autoclass("android.content.pm.PackageManager").PERMISSION_GRANTED
        if activity.checkSelfPermission(PERMISSION) != granted:
            activity.requestPermissions([PERMISSION], 4243)
    except Exception as err:  # noqa: BLE001 - not Android, or no permission dialog: no notification then
        _LOGGER.debug("Notification permission: %s", err)


def _small_icon(activity) -> int:
    """Our monochrome icon; the app icon (a white square in the status bar) only when it is missing."""
    found = activity.getResources().getIdentifier(SMALL_ICON, "drawable", activity.getPackageName())
    return found or activity.getApplicationInfo().icon


def restyle_service_notification() -> bool:
    """Give the background service's notification our icon: geolocator_android always shows the app's
    launcher icon there, which Android draws as a white square. The notification is posted again with
    the same id, everything else kept (Android 7+). True once done."""
    try:
        jnius, activity = _activity()
        if _sdk() < 24:
            return True
        manager = activity.getSystemService(jnius.autoclass("android.content.Context").NOTIFICATION_SERVICE)
        icon = _small_icon(activity)
        for active in manager.getActiveNotifications():
            if active.getId() != GEOLOCATOR_NOTIFICATION_ID:
                continue
            notification = active.getNotification()
            try:
                if notification.getSmallIcon().getResId() == icon:
                    return True  # already ours
            except Exception:  # noqa: BLE001 - getResId is Android 9+: post it again anyway
                pass
            Builder = jnius.autoclass("android.app.Notification$Builder")
            builder = Builder.recoverBuilder(activity, notification)
            builder.setSmallIcon(icon)
            manager.notify(GEOLOCATOR_NOTIFICATION_ID, builder.build())
            return True
    except Exception as err:  # noqa: BLE001 - not Android: nothing to do
        _LOGGER.debug("Service notification icon: %s", err)
        return True
    return False  # not posted yet


def notify(title: str, text: str, channel_name: str) -> bool:
    """Show a notification that opens the app when tapped; False when it could not."""
    try:
        jnius, activity = _activity()
        Context = jnius.autoclass("android.content.Context")
        manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)
        sdk = _sdk()
        if sdk >= 26:
            NotificationChannel = jnius.autoclass("android.app.NotificationChannel")
            NotificationManager = jnius.autoclass("android.app.NotificationManager")
            manager.createNotificationChannel(NotificationChannel(CHANNEL, channel_name,
                                                                  NotificationManager.IMPORTANCE_HIGH))
            builder = jnius.autoclass("android.app.Notification$Builder")(activity, CHANNEL)
        else:
            builder = jnius.autoclass("android.app.Notification$Builder")(activity)
        PendingIntent = jnius.autoclass("android.app.PendingIntent")
        intent = activity.getPackageManager().getLaunchIntentForPackage(activity.getPackageName())
        flags = PendingIntent.FLAG_UPDATE_CURRENT | (PendingIntent.FLAG_IMMUTABLE if sdk >= 23 else 0)
        pending = PendingIntent.getActivity(activity, 0, intent, flags)
        builder.setSmallIcon(_small_icon(activity))
        builder.setContentTitle(title)
        builder.setContentText(text)
        builder.setAutoCancel(True)
        builder.setContentIntent(pending)
        manager.notify(NOTIFICATION_ID, builder.build())
        return True
    except Exception as err:  # noqa: BLE001 - not Android or not allowed
        _LOGGER.info("Notification not shown: %s", err)
        return False


def cancel() -> None:
    try:
        jnius, activity = _activity()
        manager = activity.getSystemService(jnius.autoclass("android.content.Context").NOTIFICATION_SERVICE)
        manager.cancel(NOTIFICATION_ID)
    except Exception:  # noqa: BLE001
        pass
