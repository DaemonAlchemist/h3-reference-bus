"""MiniMax H3 Reference Bus nodes for ComfyUI.

Provides create and expand bus nodes for multimodal references
(images, videos, video soundtracks, and standalone audio) tailored
for the MiniMax H3 Reference-to-Video (Ref2VA) workflow.
"""

from typing import Any
import nodes
from comfy_api.latest import io
from comfy_api.latest._ui import PreviewText

H3RefBusType = io.Custom("H3_REF_BUS")
H3VideoSettingsBusType = io.Custom("H3_VIDEO_SETTINGS_BUS")


def _extract_indexed_item(container: Any, prefix: str, index: int) -> Any:
    """Safely extracts an item from a dict or sequence using either prefix key, int key, or list index."""
    if container is None:
        return None
    if isinstance(container, dict):
        key = f"{prefix}{index}"
        if key in container:
            return container[key]
        if index in container:
            return container[index]
        # Check 1-based key fallback (e.g. ref_image_1 for index 0)
        alt_key = f"{prefix}{index + 1}"
        if alt_key in container:
            return container[alt_key]
        return None
    if isinstance(container, (list, tuple)):
        if 0 <= index < len(container):
            return container[index]
    return None


class MiniMaxH3CreateReferenceBus(io.ComfyNode):
    """Create a MiniMax H3 reference bus bundling reference images, videos, soundtracks, and audios."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3CreateReferenceBus",
            display_name="Create MiniMax H3 Reference Bus",
            category="Bus/MiniMax",
            description="Bundle MiniMax H3 multimodal reference assets (images, videos, soundtracks, audios) into a single bus connection for Ref2VA workflows.",
            inputs=[
                io.Combo.Input(
                    "bus_behavior",
                    options=["append", "overwrite"],
                    default="append",
                    tooltip=(
                        "How new references are merged when an existing bus is connected:\n"
                        "- 'append': Increments indices so new inputs are added after existing items (e.g. 2 existing images + 1 new = <Picture 3>).\n"
                        "- 'overwrite': Replaces existing references at the same slot indices."
                    ),
                ),
                H3RefBusType.Input(
                    "bus",
                    optional=True,
                    tooltip="Optional existing H3 reference bus to extend or override.",
                ),
                io.Autogrow.Input(
                    "ref_images",
                    optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Image.Input(
                            "ref_image",
                            tooltip="Reference image (up to 9, referenced in prompt as <Picture 1>..<Picture 9>)",
                        ),
                        prefix="ref_image_",
                        min=0,
                        max=9,
                    ),
                ),
                io.Autogrow.Input(
                    "ref_videos",
                    optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Image.Input(
                            "ref_video",
                            tooltip="Reference video frames at 24 fps (up to 3, referenced in prompt as <Video 1>..<Video 3>)",
                        ),
                        prefix="ref_video_",
                        min=0,
                        max=3,
                    ),
                ),
                io.Autogrow.Input(
                    "ref_video_audios",
                    optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Audio.Input(
                            "ref_video_audio",
                            tooltip="Soundtrack of the corresponding reference video",
                        ),
                        prefix="ref_video_audio_",
                        min=0,
                        max=3,
                    ),
                ),
                io.Autogrow.Input(
                    "ref_audios",
                    optional=True,
                    template=io.Autogrow.TemplatePrefix(
                        input=io.Audio.Input(
                            "ref_audio",
                            tooltip="Standalone reference audio (up to 3, referenced in prompt as <Audio 1>..<Audio 3>)",
                        ),
                        prefix="ref_audio_",
                        min=0,
                        max=3,
                    ),
                ),
            ],
            outputs=[H3RefBusType.Output("bus", display_name="bus")],
        )

    @classmethod
    def execute(
        cls,
        bus_behavior: str = "append",
        bus: dict[str, Any] | None = None,
        ref_images: dict[str, Any] | None = None,
        ref_videos: dict[str, Any] | None = None,
        ref_video_audios: dict[str, Any] | None = None,
        ref_audios: dict[str, Any] | None = None,
        **kwargs,
    ) -> io.NodeOutput:
        out_bus = {
            "ref_images": dict(bus.get("ref_images", {})) if bus else {},
            "ref_videos": dict(bus.get("ref_videos", {})) if bus else {},
            "ref_video_audios": dict(bus.get("ref_video_audios", {})) if bus else {},
            "ref_audios": dict(bus.get("ref_audios", {})) if bus else {},
        }

        inherited_counts = {
            "images": len(out_bus["ref_images"]),
            "videos": len(out_bus["ref_videos"]),
            "video_audios": len(out_bus["ref_video_audios"]),
            "audios": len(out_bus["ref_audios"]),
        }

        # Collect raw inputs from autogrow dicts and kwargs
        all_images = dict(ref_images or {})
        all_videos = dict(ref_videos or {})
        all_video_audios = dict(ref_video_audios or {})
        all_audios = dict(ref_audios or {})

        for k, v in kwargs.items():
            if v is None:
                continue
            if k.startswith("ref_image_"):
                all_images[k] = v
            elif k.startswith("ref_video_audio_"):
                all_video_audios[k] = v
            elif k.startswith("ref_video_"):
                all_videos[k] = v
            elif k.startswith("ref_audio_"):
                all_audios[k] = v

        added_counts = {"images": 0, "videos": 0, "video_audios": 0, "audios": 0}

        if bus_behavior == "append":
            # 1. Images (up to 9 total)
            sorted_images = sorted(
                [(int(k.split("_")[-1]), v) for k, v in all_images.items() if v is not None],
                key=lambda x: x[0]
            )
            existing_img_indices = [int(k.split("_")[-1]) for k in out_bus["ref_images"].keys()]
            next_img_idx = (max(existing_img_indices) + 1) if existing_img_indices else 0

            for _, img in sorted_images:
                if next_img_idx >= 9:
                    raise ValueError(
                        f"MiniMax H3 supports a maximum of 9 reference images (<Picture 1>..<Picture 9>). "
                        f"Incoming bus has {len(existing_img_indices)} images; cannot add more."
                    )
                out_bus["ref_images"][f"ref_image_{next_img_idx}"] = img
                next_img_idx += 1
                added_counts["images"] += 1

            # 2. Videos and paired Soundtracks (up to 3 total)
            sorted_videos = sorted(
                [(int(k.split("_")[-1]), v) for k, v in all_videos.items() if v is not None],
                key=lambda x: x[0]
            )
            existing_vid_indices = [int(k.split("_")[-1]) for k in out_bus["ref_videos"].keys()]
            next_vid_idx = (max(existing_vid_indices) + 1) if existing_vid_indices else 0

            for orig_idx, vid in sorted_videos:
                if next_vid_idx >= 3:
                    raise ValueError(
                        f"MiniMax H3 supports a maximum of 3 reference videos (<Video 1>..<Video 3>). "
                        f"Incoming bus has {len(existing_vid_indices)} videos; cannot add more."
                    )
                out_bus["ref_videos"][f"ref_video_{next_vid_idx}"] = vid

                # Automatically map corresponding soundtrack to the incremented video index
                soundtrack = all_video_audios.get(f"ref_video_audio_{orig_idx}")
                if soundtrack is not None:
                    out_bus["ref_video_audios"][f"ref_video_audio_{next_vid_idx}"] = soundtrack
                    added_counts["video_audios"] += 1

                next_vid_idx += 1
                added_counts["videos"] += 1

            # Standalone video audios not connected via a matching video index
            for k, v in all_video_audios.items():
                orig_idx = int(k.split("_")[-1])
                if orig_idx not in [x[0] for x in sorted_videos] and v is not None:
                    existing_va = [int(x.split("_")[-1]) for x in out_bus["ref_video_audios"].keys()]
                    va_idx = (max(existing_va) + 1) if existing_va else 0
                    if va_idx < 3:
                        out_bus["ref_video_audios"][f"ref_video_audio_{va_idx}"] = v
                        added_counts["video_audios"] += 1

            # 3. Standalone Audios (up to 3 total)
            sorted_audios = sorted(
                [(int(k.split("_")[-1]), v) for k, v in all_audios.items() if v is not None],
                key=lambda x: x[0]
            )
            existing_aud_indices = [int(k.split("_")[-1]) for k in out_bus["ref_audios"].keys()]
            next_aud_idx = (max(existing_aud_indices) + 1) if existing_aud_indices else 0

            for _, aud in sorted_audios:
                if next_aud_idx >= 3:
                    raise ValueError(
                        f"MiniMax H3 supports a maximum of 3 standalone reference audios (<Audio 1>..<Audio 3>). "
                        f"Incoming bus has {len(existing_aud_indices)} audios; cannot add more."
                    )
                out_bus["ref_audios"][f"ref_audio_{next_aud_idx}"] = aud
                next_aud_idx += 1
                added_counts["audios"] += 1

        else:
            # Overwrite mode: replace matching slot keys directly
            for k, v in all_images.items():
                if v is not None:
                    out_bus["ref_images"][k] = v
                    added_counts["images"] += 1

            for k, v in all_videos.items():
                if v is not None:
                    out_bus["ref_videos"][k] = v
                    added_counts["videos"] += 1

            for k, v in all_video_audios.items():
                if v is not None:
                    out_bus["ref_video_audios"][k] = v
                    added_counts["video_audios"] += 1

            for k, v in all_audios.items():
                if v is not None:
                    out_bus["ref_audios"][k] = v
                    added_counts["audios"] += 1

        # Format visual summary for ComfyUI canvas feedback
        total_img = len(out_bus["ref_images"])
        total_vid = len(out_bus["ref_videos"])
        total_aud = len(out_bus["ref_audios"])

        img_tag_str = f"<Picture 1..{total_img}>" if total_img > 1 else ("<Picture 1>" if total_img == 1 else "none")
        vid_tag_str = f"<Video 1..{total_vid}>" if total_vid > 1 else ("<Video 1>" if total_vid == 1 else "none")
        aud_tag_str = f"<Audio 1..{total_aud}>" if total_aud > 1 else ("<Audio 1>" if total_aud == 1 else "none")

        summary_text = (
            f"[H3 Reference Bus]\n"
            f"Mode: {bus_behavior}\n"
            f"Incoming: {inherited_counts['images']} img, {inherited_counts['videos']} vid, {inherited_counts['audios']} aud\n"
            f"Added: +{added_counts['images']} img, +{added_counts['videos']} vid, +{added_counts['audios']} aud\n"
            f"Total Bus: {total_img} img ({img_tag_str}), {total_vid} vid ({vid_tag_str}), {total_aud} aud ({aud_tag_str})"
        )

        return io.NodeOutput(out_bus, ui=PreviewText(summary_text))


class MiniMaxH3ExpandReferenceBus(io.ComfyNode):
    """Expand a MiniMax H3 reference bus back into individual reference image, video, and audio outputs."""

    @classmethod
    def define_schema(cls):
        outputs = []
        # 9 Reference Images (<Picture 1> .. <Picture 9>)
        for i in range(9):
            outputs.append(
                io.Image.Output(
                    f"ref_image_{i}",
                    display_name=f"ref_image_{i+1} (<Picture {i+1}>)",
                    tooltip=f"Reference image {i+1}, referenced in prompt as <Picture {i+1}>",
                )
            )

        # 3 Reference Videos (<Video 1> .. <Video 3>)
        for i in range(3):
            outputs.append(
                io.Image.Output(
                    f"ref_video_{i}",
                    display_name=f"ref_video_{i+1} (<Video {i+1}>)",
                    tooltip=f"Reference video frames {i+1}, referenced in prompt as <Video {i+1}>",
                )
            )

        # 3 Reference Video Soundtracks
        for i in range(3):
            outputs.append(
                io.Audio.Output(
                    f"ref_video_audio_{i}",
                    display_name=f"ref_video_audio_{i+1} (<Video {i+1} Soundtrack>)",
                    tooltip=f"Soundtrack of reference video {i+1}",
                )
            )

        # 3 Standalone Reference Audios (<Audio 1> .. <Audio 3>)
        for i in range(3):
            outputs.append(
                io.Audio.Output(
                    f"ref_audio_{i}",
                    display_name=f"ref_audio_{i+1} (<Audio {i+1}>)",
                    tooltip=f"Standalone reference audio {i+1}, referenced in prompt as <Audio {i+1}>",
                )
            )

        return io.Schema(
            node_id="MiniMaxH3ExpandReferenceBus",
            display_name="Expand MiniMax H3 Reference Bus",
            category="Bus/MiniMax",
            description="Unpack a MiniMax H3 reference bus into individual reference images (<Picture 1..9>), videos (<Video 1..3>), soundtracks, and audios (<Audio 1..3>).",
            inputs=[
                H3RefBusType.Input(
                    "bus",
                    tooltip="MiniMax H3 reference bus to expand into individual outputs.",
                ),
            ],
            outputs=outputs,
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        ref_images = bus.get("ref_images", {})
        ref_videos = bus.get("ref_videos", {})
        ref_video_audios = bus.get("ref_video_audios", {})
        ref_audios = bus.get("ref_audios", {})

        outputs = []

        # Extract 9 reference images
        for i in range(9):
            outputs.append(_extract_indexed_item(ref_images, "ref_image_", i))

        # Extract 3 reference videos
        for i in range(3):
            outputs.append(_extract_indexed_item(ref_videos, "ref_video_", i))

        # Extract 3 reference video soundtracks
        for i in range(3):
            outputs.append(_extract_indexed_item(ref_video_audios, "ref_video_audio_", i))

        # Extract 3 standalone reference audios
        for i in range(3):
            outputs.append(_extract_indexed_item(ref_audios, "ref_audio_", i))

        return io.NodeOutput(*outputs)


class MiniMaxH3CreateVideoSettingsBus(io.ComfyNode):
    """Create a MiniMax H3 video settings bus bundling model, clip, video VAE, audio VAE, width, and height."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3CreateVideoSettingsBus",
            display_name="Create MiniMax H3 Video Settings Bus",
            category="Bus/MiniMax",
            description="Bundle global video settings (model, clip, video VAE, audio VAE, width, height) into a single bus for MiniMax H3 workflows.",
            inputs=[
                H3VideoSettingsBusType.Input(
                    "bus",
                    optional=True,
                    tooltip="Optional existing video settings bus to extend or override.",
                ),
                io.Model.Input("model", optional=True, tooltip="Diffusion model"),
                io.Clip.Input("clip", optional=True, tooltip="CLIP / Text encoder model"),
                io.Vae.Input("vae", optional=True, tooltip="Video VAE"),
                io.Vae.Input("audio_vae", optional=True, tooltip="Audio VAE for synchronized audio"),
                io.Int.Input("width", default=1344, min=32, max=nodes.MAX_RESOLUTION, step=32, tooltip="Output video width (multiple of 32, default 1344)"),
                io.Int.Input("height", default=768, min=32, max=nodes.MAX_RESOLUTION, step=32, tooltip="Output video height (multiple of 32, default 768)"),
            ],
            outputs=[H3VideoSettingsBusType.Output("bus", display_name="bus")],
        )

    @classmethod
    def execute(
        cls,
        bus: dict[str, Any] | None = None,
        model: Any = None,
        clip: Any = None,
        vae: Any = None,
        audio_vae: Any = None,
        width: int = 1344,
        height: int = 768,
        **kwargs,
    ) -> io.NodeOutput:
        bus = bus or {}
        out_bus = {
            "model": model if model is not None else bus.get("model"),
            "clip": clip if clip is not None else bus.get("clip"),
            "vae": vae if vae is not None else bus.get("vae"),
            "audio_vae": audio_vae if audio_vae is not None else bus.get("audio_vae"),
            "width": width if width is not None else bus.get("width", 1344),
            "height": height if height is not None else bus.get("height", 768),
        }

        model_str = "Connected" if out_bus["model"] is not None else "None"
        clip_str = "Connected" if out_bus["clip"] is not None else "None"
        vae_str = "Connected" if out_bus["vae"] is not None else "None"
        avae_str = "Connected" if out_bus["audio_vae"] is not None else "None"

        summary = (
            f"[H3 Video Settings Bus]\n"
            f"Model: {model_str}\n"
            f"CLIP: {clip_str}\n"
            f"Video VAE: {vae_str}\n"
            f"Audio VAE: {avae_str}\n"
            f"Resolution: {out_bus['width']}x{out_bus['height']}"
        )

        return io.NodeOutput(out_bus, ui=PreviewText(summary))


class MiniMaxH3ExpandVideoSettingsBus(io.ComfyNode):
    """Expand a MiniMax H3 video settings bus into model, clip, video VAE, audio VAE, width, and height."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ExpandVideoSettingsBus",
            display_name="Expand MiniMax H3 Video Settings Bus",
            category="Bus/MiniMax",
            description="Unpack a MiniMax H3 video settings bus into model, clip, video VAE, audio VAE, width, and height.",
            inputs=[
                H3VideoSettingsBusType.Input(
                    "bus",
                    tooltip="Video settings bus to expand.",
                ),
            ],
            outputs=[
                io.Model.Output("model", display_name="model", tooltip="Diffusion model"),
                io.Clip.Output("clip", display_name="clip", tooltip="CLIP / Text encoder model"),
                io.Vae.Output("vae", display_name="video_vae", tooltip="Video VAE"),
                io.Vae.Output("audio_vae", display_name="audio_vae", tooltip="Audio VAE for synchronized audio"),
                io.Int.Output("width", display_name="width", tooltip="Output video width"),
                io.Int.Output("height", display_name="height", tooltip="Output video height"),
            ],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(
            bus.get("model"),
            bus.get("clip"),
            bus.get("vae"),
            bus.get("audio_vae"),
            bus.get("width", 1344),
            bus.get("height", 768),
        )


class MiniMaxH3ModelFromBus(io.ComfyNode):
    """Extract the diffusion model from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ModelFromBus",
            display_name="Model from Bus",
            category="Bus/MiniMax",
            description="Extract the diffusion model (MODEL) from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Model.Output("model", display_name="model", tooltip="Extracted diffusion model")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("model"))


class MiniMaxH3ClipFromBus(io.ComfyNode):
    """Extract the CLIP text encoder from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ClipFromBus",
            display_name="CLIP from Bus",
            category="Bus/MiniMax",
            description="Extract the CLIP text encoder from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Clip.Output("clip", display_name="clip", tooltip="Extracted CLIP model")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("clip"))


class MiniMaxH3VideoVaeFromBus(io.ComfyNode):
    """Extract the Video VAE from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3VideoVaeFromBus",
            display_name="Video VAE from Bus",
            category="Bus/MiniMax",
            description="Extract the Video VAE from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Vae.Output("vae", display_name="video_vae", tooltip="Extracted Video VAE")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("vae"))


class MiniMaxH3AudioVaeFromBus(io.ComfyNode):
    """Extract the Audio VAE from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3AudioVaeFromBus",
            display_name="Audio VAE from Bus",
            category="Bus/MiniMax",
            description="Extract the Audio VAE from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Vae.Output("audio_vae", display_name="audio_vae", tooltip="Extracted Audio VAE")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("audio_vae"))


class MiniMaxH3ResolutionFromBus(io.ComfyNode):
    """Extract width and height resolution from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ResolutionFromBus",
            display_name="Resolution from Bus",
            category="Bus/MiniMax",
            description="Extract width and height integers from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[
                io.Int.Output("width", display_name="width", tooltip="Output video width"),
                io.Int.Output("height", display_name="height", tooltip="Output video height"),
            ],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("width", 1344), bus.get("height", 768))


class MiniMaxH3WidthFromBus(io.ComfyNode):
    """Extract width from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3WidthFromBus",
            display_name="Width from Bus",
            category="Bus/MiniMax",
            description="Extract width integer from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Int.Output("width", display_name="width", tooltip="Output video width")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("width", 1344))


class MiniMaxH3HeightFromBus(io.ComfyNode):
    """Extract height from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3HeightFromBus",
            display_name="Height from Bus",
            category="Bus/MiniMax",
            description="Extract height integer from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Int.Output("height", display_name="height", tooltip="Output video height")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("height", 768))


class MiniMaxH3VAEsFromBus(io.ComfyNode):
    """Extract both Video VAE and Audio VAE from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3VAEsFromBus",
            display_name="VAEs from Bus",
            category="Bus/MiniMax",
            description="Extract both Video VAE and Audio VAE from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[
                io.Vae.Output("video_vae", display_name="video_vae", tooltip="Extracted Video VAE"),
                io.Vae.Output("audio_vae", display_name="audio_vae", tooltip="Extracted Audio VAE"),
            ],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("vae"), bus.get("audio_vae"))



