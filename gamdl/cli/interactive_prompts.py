import click
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
import m3u8
from ..interface import ArtistMediaType


class InteractivePrompts:
    def __init__(
        self,
        artist_auto_select: ArtistMediaType | None = None,
    ):
        self.artist_auto_select = artist_auto_select

    @staticmethod
    def millis_to_min_sec(millis) -> str:
        minutes, seconds = divmod(millis // 1000, 60)
        return f"{minutes:02}:{seconds:02}"

    @staticmethod
    async def ask_song_codec(
        playlists: list[dict],
    ) -> dict:
        choices = [
            Choice(
                name=playlist["stream_info"]["audio"],
                value=playlist,
            )
            for playlist in playlists
        ]

        return await inquirer.select(
            message="Select which codec to download:",
            choices=choices,
        ).execute_async()

    @staticmethod
    async def ask_music_video_video_codec_function(
        playlists: list[m3u8.Playlist],
    ) -> dict:
        choices = [
            Choice(
                name=" | ".join(
                    [
                        playlist.stream_info.codecs[:4],
                        "x".join(str(v) for v in playlist.stream_info.resolution),
                        str(playlist.stream_info.bandwidth),
                    ]
                ),
                value=playlist,
            )
            for playlist in playlists
        ]

        return await inquirer.select(
            message="Select which video codec to download: (Codec | Resolution | Bitrate)",
            choices=choices,
        ).execute_async()

    @staticmethod
    async def ask_music_video_audio_codec_function(
        playlists: list[dict],
    ) -> dict:
        choices = [
            Choice(
                name=playlist["group_id"],
                value=playlist,
            )
            for playlist in playlists
        ]

        selected = await inquirer.select(
            message="Select which audio codec to download:",
            choices=choices,
        ).execute_async()

        return selected

    @staticmethod
    async def ask_uploaded_video_quality_function(
        available_qualities: dict[str, str],
    ) -> str:
        qualities = list(available_qualities.keys())
        choices = [
            Choice(
                name=quality,
                value=quality,
            )
            for quality in qualities
        ]
        selected = await inquirer.select(
            message="Select which quality to download:",
            choices=choices,
        ).execute_async()

        return available_qualities[selected]

    async def ask_artist_media_type(
        self,
        media_types: list[ArtistMediaType],
        artist_metadata: dict,
    ) -> ArtistMediaType:
        if self.artist_auto_select:
            return self.artist_auto_select

        available_choices = []
        for media_types in media_types:
            available_choices.append(
                Choice(
                    name=str(media_types),
                    value=(media_types,),
                ),
            )

        (media_type,) = await inquirer.select(
            message=f'Select which type to download for artist "{artist_metadata["attributes"]["name"]}":',
            choices=available_choices,
            validate=lambda result: artist_metadata.get(result[0].path_key[0], {})
            .get(result[0].path_key[1], {})
            .get("data"),
        ).execute_async()

        return media_type

    async def ask_artist_select_items(
        self,
        media_type: ArtistMediaType,
        items: list[dict],
    ) -> list[dict]:
        if media_type in {
            ArtistMediaType.MAIN_ALBUMS,
            ArtistMediaType.COMPILATION_ALBUMS,
            ArtistMediaType.LIVE_ALBUMS,
            ArtistMediaType.SINGLES_EPS,
            ArtistMediaType.ALL_ALBUMS,
        }:
            return await self._ask_artist_select_albums(items)
        elif media_type == ArtistMediaType.TOP_SONGS:
            return await self._ask_artist_select_songs(
                items,
            )
        elif media_type == ArtistMediaType.MUSIC_VIDEOS:
            return await self._ask_artist_select_music_videos(items)

    async def _ask_artist_select_albums(
        self,
        albums: list[dict],
    ) -> list[dict]:
        if self.artist_auto_select:
            return albums

        choices = [
            Choice(
                name=" | ".join(
                    [
                        f'{album["attributes"]["trackCount"]:03d}',
                        f'{album["attributes"]["releaseDate"]:<10}',
                        f'{album["attributes"].get("contentRating", "None").title():<8}',
                        f'{album["attributes"]["name"]}',
                    ]
                ),
                value=album,
            )
            for album in albums
            if album.get("attributes")
        ]
        selected = await inquirer.select(
            message="Select which albums to download: (Track Count | Release Date | Rating | Title)",
            choices=choices,
            multiselect=True,
        ).execute_async()

        return selected

    async def _ask_artist_select_songs(
        self,
        songs: list[dict],
    ) -> list[dict]:
        if self.artist_auto_select:
            return songs

        choices = [
            Choice(
                name=" | ".join(
                    [
                        self.millis_to_min_sec(song["attributes"]["durationInMillis"]),
                        f'{song["attributes"].get("contentRating", "None").title():<8}',
                        song["attributes"]["name"],
                    ],
                ),
                value=song,
            )
            for song in songs
            if song.get("attributes")
        ]
        selected = await inquirer.select(
            message="Select which songs to download: (Duration | Rating | Title)",
            choices=choices,
            multiselect=True,
        ).execute_async()

        return selected

    async def _ask_artist_select_music_videos(
        self,
        music_videos: list[dict],
    ) -> list[dict]:
        if self.artist_auto_select:
            return music_videos

        choices = [
            Choice(
                name=" | ".join(
                    [
                        self.millis_to_min_sec(
                            music_video["attributes"]["durationInMillis"]
                        ),
                        f'{music_video["attributes"].get("contentRating", "None").title():<8}',
                        music_video["attributes"]["name"],
                    ],
                ),
                value=music_video,
            )
            for music_video in music_videos
            if music_video.get("attributes")
        ]
        selected = await inquirer.select(
            message="Select which music videos to download: (Duration | Rating | Title)",
            choices=choices,
            multiselect=True,
        ).execute_async()

        return selected

    @staticmethod
    def _format_search_result_name(item: dict) -> str:
        attributes = item.get("attributes", {})
        title = attributes.get("name", "Unknown")

        if item.get("type") == "artists":
            genre_names = attributes.get("genreNames", [])
            if genre_names:
                return f'{title} | {", ".join(genre_names[:2])}'
            return title

        parts = [title]
        for key in ("artistName", "releaseDate", "trackCount"):
            value = attributes.get(key)
            if value:
                parts.append(str(value))

        return " | ".join(parts)

    @staticmethod
    def _parse_track_selection(selection: str, total: int) -> list[int] | None:
        tokens = [token.strip().lower() for token in selection.split(",") if token.strip()]
        if not tokens:
            return None

        if len(tokens) == 1 and tokens[0] == "all":
            return list(range(1, total + 1))

        selected_indices = []
        for token in tokens:
            if token == "all":
                return list(range(1, total + 1))

            if "-" in token:
                start_text, end_text = token.split("-", 1)
                if not start_text.isdigit() or not end_text.isdigit():
                    return None
                start_index = int(start_text)
                end_index = int(end_text)
                if start_index > end_index:
                    start_index, end_index = end_index, start_index
                selected_indices.extend(range(start_index, end_index + 1))
            else:
                if not token.isdigit():
                    return None
                selected_indices.append(int(token))

        filtered_indices = []
        for index in sorted(set(selected_indices)):
            if 1 <= index <= total:
                filtered_indices.append(index)

        if not filtered_indices:
            return None

        return filtered_indices

    async def ask_search_result(
        self,
        search_type: str,
        results: list[dict],
    ) -> dict:
        choices = [
            Choice(
                name=self._format_search_result_name(result),
                value=result,
            )
            for result in results
            if result.get("attributes")
        ]

        selected = await inquirer.select(
            message=f"Select which {search_type} to download:",
            choices=choices,
        ).execute_async()

        return selected

    async def ask_collection_tracks(
        self,
        collection_metadata: dict,
        tracks: list[dict],
    ) -> list[dict]:
        collection_name = collection_metadata.get("attributes", {}).get(
            "name",
            "Unknown",
        )

        click.echo(f'Selected collection: {collection_name}')
        click.echo("Available tracks:")
        for index, track in enumerate(tracks, 1):
            attributes = track.get("attributes", {})
            track_name = attributes.get("name", "Unknown")
            artist_name = attributes.get("artistName")
            line = f"  {index:>2}. {track_name}"
            if artist_name:
                line += f" - {artist_name}"
            click.echo(line)

        while True:
            selection = click.prompt(
                "Select tracks to download (press Enter for all, or use 1-5, 1,3,7)",
                default="all",
                show_default=True,
            )

            selected_indices = self._parse_track_selection(selection, len(tracks))
            if selected_indices:
                return [tracks[index - 1] for index in selected_indices]

            click.echo("Invalid selection, try again.")
