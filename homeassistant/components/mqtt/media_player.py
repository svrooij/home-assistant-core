"""Support for MQTT Media players."""
from __future__ import annotations

import functools
import json
import logging
import time

import voluptuous as vol

from homeassistant.components import media_player, media_source
from homeassistant.components.media_player import (  # DEVICE_CLASSES_SCHEMA,
    MediaPlayerDeviceClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
)
from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.components.media_player.const import (  # MEDIA_TYPE_MUSIC,; REPEAT_MODE_ONE,
    MEDIA_CLASS_APP,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_TYPE_TRACK,
    REPEAT_MODE_ALL,
    REPEAT_MODE_OFF,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.errors import BrowseError
from homeassistant.components.media_source.models import BrowseMediaSource
from homeassistant.components.sonos.media_browser import media_source_filter
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_PAUSED, STATE_PLAYING
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

from . import subscription
from .config import MQTT_RW_SCHEMA
from .const import CONF_COMMAND_TOPIC, CONF_ENCODING, CONF_QOS, CONF_STATE_TOPIC
from .debug_info import log_messages
from .mixins import (  # warn_for_legacy_schema,
    MQTT_ENTITY_COMMON_SCHEMA,
    MqttEntity,
    async_setup_entry_helper,
    async_setup_platform_discovery,
    async_setup_platform_helper,
)

# from .models import MqttValueTemplate
DEFAULT_NAME = "MQTT Media Player"
# DEFAULT_PAYLOAD_ON = "ON"
# DEFAULT_PAYLOAD_OFF = "OFF"
# DEFAULT_OPTIMISTIC = False
# CONF_STATE_ON = "state_on"
# CONF_STATE_OFF = "state_off"

PLATFORM_SCHEMA_MODERN = MQTT_RW_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        # vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
        # vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
        # vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
        # vol.Optional(CONF_STATE_OFF): cv.string,
        # vol.Optional(CONF_STATE_ON): cv.string,
        # vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
        # vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }
).extend(MQTT_ENTITY_COMMON_SCHEMA.schema)

# Configuring MQTT Switches under the switch platform key is deprecated in HA Core 2022.6
# PLATFORM_SCHEMA = vol.All(
#     cv.PLATFORM_SCHEMA.extend(PLATFORM_SCHEMA_MODERN.schema),
#     warn_for_legacy_schema(media_player.DOMAIN),
# )

DISCOVERY_SCHEMA = PLATFORM_SCHEMA_MODERN.extend({}, extra=vol.REMOVE_EXTRA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up MQTT media player configured under the fan platform key (deprecated)."""
    # Deprecated in HA Core 2022.6
    await async_setup_platform_helper(
        hass,
        media_player.DOMAIN,
        discovery_info or config,
        async_add_entities,
        _async_setup_entity,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MQTT switch through configuration.yaml and dynamically through MQTT discovery."""
    # load and initialize platform config from configuration.yaml
    config_entry.async_on_unload(
        await async_setup_platform_discovery(
            hass, media_player.DOMAIN, PLATFORM_SCHEMA_MODERN
        )
    )
    # setup for discovery
    setup = functools.partial(
        _async_setup_entity, hass, async_add_entities, config_entry=config_entry
    )
    await async_setup_entry_helper(hass, media_player.DOMAIN, setup, DISCOVERY_SCHEMA)


async def _async_setup_entity(
    hass, async_add_entities, config, config_entry=None, discovery_data=None
):
    """Set up the MQTT switch."""
    async_add_entities([MqttMediaPlayer(hass, config, config_entry, discovery_data)])


class MqttMediaPlayer(MqttEntity, MediaPlayerEntity, RestoreEntity):
    """Representation of a switch that can be toggled using MQTT."""

    _entity_id_format = media_player.ENTITY_ID_FORMAT
    _attr_media_content_type = MEDIA_TYPE_TRACK
    _attr_supported_features = (
        MediaPlayerEntityFeature.BROWSE_MEDIA
        # | MediaPlayerEntityFeature.CLEAR_PLAYLIST
        # | MediaPlayerEntityFeature.GROUPING
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.REPEAT_SET
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SHUFFLE_SET
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
    )
    _attr_device_class = MediaPlayerDeviceClass.RECEIVER

    def __init__(self, hass, config, config_entry, discovery_data):
        """Initialize the MQTT media player."""
        # self._state = None

        # self._state_on = None
        # self._state_off = None
        # self._optimistic = None

        MqttEntity.__init__(self, hass, config, config_entry, discovery_data)

    @staticmethod
    def config_schema():
        """Return the config schema."""
        return DISCOVERY_SCHEMA

    def _setup_from_config(self, config):
        """(Re)Setup the entity."""
        # state_on = config.get(CONF_STATE_ON)
        # self._state_on = state_on if state_on else config[CONF_PAYLOAD_ON]

        # state_off = config.get(CONF_STATE_OFF)
        # self._state_off = state_off if state_off else config[CONF_PAYLOAD_OFF]

        # self._optimistic = (
        #     config[CONF_OPTIMISTIC] or config.get(CONF_STATE_TOPIC) is None
        # )

        # self._value_template = MqttValueTemplate(
        #     self._config.get(CONF_VALUE_TEMPLATE), entity=self
        # ).async_render_with_possible_json_value

    def _prepare_subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        @log_messages(self.hass, self.entity_id)
        def state_message_received(msg):
            """Handle new MQTT state messages."""
            payload = json.loads(msg.payload)
            sonos_state = payload.get("transportState")
            if sonos_state in ("PAUSED_PLAYBACK", "STOPPED"):
                self._attr_state = STATE_PAUSED
            else:
                self._attr_state = STATE_PLAYING

            current_track = payload.get("currentTrack", {})
            self._attr_media_content_type = MEDIA_TYPE_TRACK
            self._attr_media_content_id = current_track.get("trackUri")
            self._attr_media_artist = current_track.get("artist")
            self._attr_media_title = current_track.get("title")
            self._attr_media_image_url = current_track.get("albumArtUri")
            self._attr_media_duration = time_string_to_seconds(
                current_track.get("duration")
            )

            members = payload.get("members")
            if members is not None:
                self._attr_group_members = []
                for member in members:
                    self._attr_group_members.append(member.get("name"))
            else:
                self._attr_group_members = None

            volume = payload.get("volume", {}).get("Master")
            if volume is not None:
                self._attr_volume_level = volume / 100

            self._attr_is_volume_muted = payload.get("mute", {}).get("Master")
            self._attr_shuffle = payload.get("shuffle")
            self._attr_media_playlist = payload.get("enqueuedMetadata", {}).get("title")
            self._attr_available = True

            position = payload.get("position")
            if position is not None:
                self._attr_media_position = time_string_to_seconds(
                    position.get("position")
                )
                update = position.get("lastUpdate")
                if update is not None:
                    self._attr_media_position_updated_at = update
                else:
                    # Not really sure about this fallback, maybe empty it? (suggestions?)
                    self._attr_media_position_updated_at = dt.utcnow()

            self.async_write_ha_state()

        self._sub_state = subscription.async_prepare_subscribe_topics(
            self.hass,
            self._sub_state,
            {
                CONF_STATE_TOPIC: {
                    "topic": self._config.get(CONF_STATE_TOPIC),
                    "msg_callback": state_message_received,
                    "qos": self._config[CONF_QOS],
                    "encoding": self._config[CONF_ENCODING] or None,
                }
            },
        )

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""
        await subscription.async_subscribe_topics(self.hass, self._sub_state)

    async def send_command(self, command, value=None):
        """Send a command, and optional payload to the mqtt server."""
        payload = json.dumps({"command": command, "input": value})
        await self.async_publish(
            self._config[CONF_COMMAND_TOPIC],
            payload,
        )

    async def async_media_play(self):
        """Send play command to mqtt."""
        await self.send_command("play")
        self._attr_state = STATE_PLAYING
        self.async_write_ha_state()

    async def async_media_pause(self):
        """Send pause command to mqtt."""
        await self.send_command("pause")
        self._attr_state = STATE_PAUSED
        self.async_write_ha_state()

    async def async_media_play_pause(self):
        """Send toggle command to mqtt."""
        await self.send_command("toggle")

    async def async_media_next_track(self):
        """Send next command to mqtt."""
        await self.send_command("next")

    async def async_media_previous_track(self):
        """Send previous command to mqtt."""
        await self.send_command("previous")

    async def async_mute_volume(self, mute):
        """Send mute command to mqtt."""
        await self.send_command("mute", mute)
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume):
        """Send volume and unmute command to mqtt."""
        await self.send_command("volume", volume * 100)
        self._attr_volume_level = volume
        if self._attr_is_volume_muted is True:
            await self.send_command("unmute")
            self._attr_is_volume_muted = False
        self.async_write_ha_state()

    async def async_media_seek(self, position):
        """Send seek command to mqtt."""
        await self.send_command("seek", seconds_to_time_string(position))
        self._attr_media_position = position
        self._attr_media_position_updated_at = dt.utcnow()
        self.async_write_ha_state()

    async def async_set_repeat(self, repeat):
        """Send repeat mode to mqtt."""
        if repeat == REPEAT_MODE_ALL:
            await self.send_command("repeat", True)
        elif repeat == REPEAT_MODE_OFF:
            await self.send_command("repeat", False)
        # how about 'one'?
        # await self.send_command("repeat", repeat)
        self._attr_repeat = repeat
        self.async_write_ha_state()

    async def async_set_shuffle(self, shuffle):
        """Send shuffle to mqtt."""
        await self.send_command("shuffle", shuffle)
        self._attr_shuffle = shuffle
        self.async_write_ha_state()

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia | BrowseMediaSource:
        """Implement the websocket media browsing helper."""

        if media_content_id is None:
            return await media_root_payload(self.hass)

        if media_source.is_media_source_id(media_content_id):
            return await media_source.async_browse_media(
                self.hass, media_content_id, content_filter=media_source_filter
            )
        raise BrowseError(f"Media not found: {media_content_type} / {media_content_id}")

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        announce: bool | None = None,
        **kwargs,
    ):
        """Play some media file."""
        # Use 'replace' as the default enqueue option
        _LOGGER.debug(
            'MQTT Media Player play media: "%s" enqueue: "%s" announce: "%s"',
            media_id,
            enqueue,
            announce,
        )
        if media_id == "sm://notification/ding":
            await self.send_command(
                "notify",
                {
                    "trackUri": "https://cdn.smartersoft-group.com/various/pull-bell-short.mp3",
                    "timeout": 4,
                },
            )
            return
        if media_source.is_media_source_id(media_id):
            info = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )

            if media_id.startswith("media-source://tts/") or announce is True:
                await self.send_command("notify", {"trackUri": info.url, "timeout": 10})
                return

            if media_id.startswith("media-source://radio_browser/"):
                await self.send_command("setavtransporturi", info.url)
                return

            await self.send_command("queue", info.url)
            return

        if media_id.startswith("spotify:"):
            await self.send_command("queue", info.url)
            return

        _LOGGER.error(
            'MQTT media player does not support a media type of "%s"', media_type
        )
        return None
        # return await super().async_play_media(media_type, media_id, **kwargs)


def time_string_to_seconds(time_string: str | None) -> int | None:
    """Convert a time string like 1:02:01 to 3721 seconds."""
    if time_string is None or time_string == "NOT_IMPLEMENTED":
        return None
    return sum(
        x * int(t) for x, t in zip([1, 60, 3600], reversed(time_string.split(":")))
    )


def seconds_to_time_string(seconds: int | None) -> str | None:
    """Convert seconds to time string HH:MM:SS."""
    # Skip values higher then 1 day
    if seconds is None or seconds >= 86400:
        return None

    return time.strftime("%H:%M:%S", time.gmtime(seconds))


async def media_root_payload(
    hass: HomeAssistant,
) -> BrowseMedia | BrowseMediaSource:
    """Create root media browser."""
    children: list[BrowseMedia] = []

    # if "spotify" in hass.config.components:
    #     result = await spotify.async_browse_media(hass, None, None)
    #     children.extend(result.children)

    try:
        item = await media_source.async_browse_media(
            hass, None, content_filter=media_source_filter
        )

        # If domain is None, it's overview of available sources
        if item.domain is None and item.children is not None:
            children.extend(item.children)
        else:
            children.append(item)
    except media_source.BrowseError:
        pass

    children.append(
        BrowseMedia(
            title="Ding",
            media_content_type="notification",
            media_class=MEDIA_CLASS_APP,
            media_content_id="sm://notification/ding",
            thumbnail="https://brands.home-assistant.io/_/sonos/logo.png",
            can_expand=False,
            can_play=True,
        )
    )

    return BrowseMedia(
        title="Sonos",
        media_class=MEDIA_CLASS_DIRECTORY,
        media_content_id="",
        media_content_type="root",
        can_play=False,
        can_expand=True,
        children=children,
    )
