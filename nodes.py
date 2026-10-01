"""MiniMax H3 Reference Bus nodes for ComfyUI.

Provides create and expand bus nodes for multimodal references
(images, videos, video soundtracks, and standalone audio) tailored
for the MiniMax H3 Reference-to-Video (Ref2VA) workflow.
"""

import hashlib
import json
import os
import re
from typing import Any

import nodes
import folder_paths
import safetensors.torch
from safetensors import safe_open
import torch

import comfy.utils
try:
    from comfy.nested_tensor import NestedTensor
except ImportError:
    class NestedTensor:
        def __init__(self, tensors):
            self.tensors = list(tensors)
            self.is_nested = True

        def unbind(self):
            return self.tensors

from comfy_api.latest import io
from comfy_api.latest._ui import PreviewText

H3RefBusType = io.Custom("H3_REF_BUS")
H3VideoSettingsBusType = io.Custom("H3_VIDEO_SETTINGS_BUS")
H3NamedRefBusType = io.Custom("H3_NAMED_REF_BUS")


class DynamicReturnTypes(list):
    """Dynamically returns '*' for any index to support arbitrary dynamic outputs in ComfyUI."""

    def __getitem__(self, idx):
        return "*"

    def __len__(self):
        return 10000



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


class MiniMaxH3CreateNamedReferenceBus(io.ComfyNode):
    """Create a Named Reference Bus bundling arbitrary multimodal references without limit."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3CreateNamedReferenceBus",
            display_name="Create Named Reference Bus",
            category="Bus/MiniMax",
            description="Bundle an unlimited number of multimodal reference assets (images, audios, videos, etc.) into a single Named Reference Bus.",
            search_aliases=["Create Named Reference Bus", "Named Reference Bus", "NamedReferenceBus", "CreateReferenceBus"],
            accept_all_inputs=True,
            inputs=[
                io.Combo.Input(
                    "bus_behavior",
                    options=["append", "overwrite"],
                    default="append",
                    tooltip=(
                        "How new references are merged when an existing bus is connected:\n"
                        "- 'append': Appends new references after existing bus entities.\n"
                        "- 'overwrite': Replaces existing references with matching names or slot keys."
                    ),
                ),
                io.MultiType.Input(
                    "bus",
                    types=[H3NamedRefBusType, H3RefBusType],
                    optional=True,
                    tooltip="Optional existing Named Reference Bus or H3 Reference Bus to extend.",
                ),
                io.AnyType.Input(
                    "entity_0",
                    optional=True,
                    tooltip="Reference entity (image, audio, video, etc.) to attach to the bus. Additional entity slots are added dynamically as wires are connected.",
                ),
            ],
            outputs=[H3NamedRefBusType.Output("bus", display_name="bus")],
        )

    @classmethod
    def execute(
        cls,
        bus_behavior: str = "append",
        bus: dict[str, Any] | None = None,
        entity_names: str | list[str] | None = None,
        **kwargs,
    ) -> io.NodeOutput:
        bus = bus or {}

        # 1. Inherit incoming entities from upstream bus
        inherited_entities: list[dict[str, Any]] = []
        if "entities" in bus:
            inherited_entities = [dict(e) for e in bus.get("entities", [])]
        elif "ordered" in bus:
            inherited_entities = [{"name": f"entity_{i+1}", "value": v} for i, v in enumerate(bus.get("ordered", []))]
        else:
            # Fallback for legacy H3 reference bus structure
            for k, v in bus.get("ref_images", {}).items():
                if v is not None:
                    inherited_entities.append({"name": k, "value": v, "type": "IMAGE"})
            for k, v in bus.get("ref_videos", {}).items():
                if v is not None:
                    inherited_entities.append({"name": k, "value": v, "type": "IMAGE"})
            for k, v in bus.get("ref_audios", {}).items():
                if v is not None:
                    inherited_entities.append({"name": k, "value": v, "type": "AUDIO"})

        # 2. Parse entity names passed from UI canvas
        name_list: list[str] = []
        if isinstance(entity_names, str):
            try:
                name_list = json.loads(entity_names)
            except Exception:
                name_list = [s.strip() for s in entity_names.split(",") if s.strip()]
        elif isinstance(entity_names, list):
            name_list = list(entity_names)

        # 3. Collect attached inputs from kwargs sorted numerically
        def _sort_key(key: str) -> tuple[int, int, str]:
            if key.startswith("entity_"):
                suffix = key[len("entity_"):]
                if suffix.isdigit():
                    return (0, int(suffix), "")
            elif key.startswith("ref_image_"):
                suffix = key[len("ref_image_"):]
                if suffix.isdigit():
                    return (1, int(suffix), "")
            elif key.startswith("ref_video_"):
                suffix = key[len("ref_video_"):]
                if suffix.isdigit():
                    return (2, int(suffix), "")
            elif key.startswith("ref_audio_"):
                suffix = key[len("ref_audio_"):]
                if suffix.isdigit():
                    return (3, int(suffix), "")
            return (4, 0, key)

        sorted_kwargs = sorted(
            [
                (k, v)
                for k, v in kwargs.items()
                if v is not None and not k.startswith("_") and k not in ("bus_behavior", "bus", "entity_names")
            ],
            key=lambda item: _sort_key(item[0]),
        )

        new_entities: list[dict[str, Any]] = []
        for idx, (k, val) in enumerate(sorted_kwargs):
            ent_name = name_list[idx] if idx < len(name_list) and name_list[idx] else k
            new_entities.append({"name": ent_name, "value": val, "key": k})

        # 4. Merge entities according to bus_behavior
        final_entities: list[dict[str, Any]] = []
        if bus_behavior == "append":
            final_entities = inherited_entities + new_entities
        else:
            merged_map: dict[str, dict[str, Any]] = {}
            for item in inherited_entities:
                merged_map[item.get("name", "")] = item
            for item in new_entities:
                merged_map[item.get("name", item.get("key", ""))] = item
            final_entities = list(merged_map.values())

        # Disambiguate duplicate entity names if any
        seen_names: dict[str, int] = {}
        for ent in final_entities:
            raw_name = ent.get("name", "entity")
            count = seen_names.get(raw_name, 0)
            seen_names[raw_name] = count + 1
            if count > 0:
                dot_idx = raw_name.rfind(".")
                if dot_idx > 0:
                    ent["name"] = f"{raw_name[:dot_idx]} ({count + 1}){raw_name[dot_idx:]}"
                else:
                    ent["name"] = f"{raw_name} ({count + 1})"

        # 5. Build output bus dict
        out_bus: dict[str, Any] = {
            "entities": final_entities,
            "ordered": [e["value"] for e in final_entities],
            "by_name": {e["name"]: e["value"] for e in final_entities},
            "ref_images": dict(bus.get("ref_images", {})),
            "ref_videos": dict(bus.get("ref_videos", {})),
            "ref_video_audios": dict(bus.get("ref_video_audios", {})),
            "ref_audios": dict(bus.get("ref_audios", {})),
        }

        # Populate legacy slots for any tensor/audio entities for seamless backward-compatibility
        img_idx = len(out_bus["ref_images"])
        aud_idx = len(out_bus["ref_audios"])
        for e in new_entities:
            v = e["value"]
            if hasattr(v, "shape") and len(v.shape) == 4 and img_idx < 9:
                out_bus["ref_images"][f"ref_image_{img_idx}"] = v
                img_idx += 1
            elif isinstance(v, dict) and "waveform" in v and aud_idx < 3:
                out_bus["ref_audios"][f"ref_audio_{aud_idx}"] = v
                aud_idx += 1

        # Visual preview text on canvas
        entity_labels = [e["name"] for e in final_entities]
        preview_lines = [f"- {name}" for name in entity_labels[:10]]
        if len(entity_labels) > 10:
            preview_lines.append(f"... and {len(entity_labels) - 10} more")
        summary_text = (
            f"[Named Reference Bus]\n"
            f"Mode: {bus_behavior}\n"
            f"Incoming: {len(inherited_entities)} entities\n"
            f"Added: +{len(new_entities)} entities\n"
            f"Total Bus: {len(final_entities)} entities\n"
            + ("\n".join(preview_lines) if preview_lines else "(No entities attached)")
        )

        return io.NodeOutput(out_bus, ui=PreviewText(summary_text))


class CreateNamedReferenceBus(MiniMaxH3CreateNamedReferenceBus):
    """Create a Named Reference Bus bundling arbitrary multimodal references without limit (alias)."""

    @classmethod
    def define_schema(cls):
        schema = super().define_schema()
        return io.Schema(
            node_id="CreateNamedReferenceBus",
            display_name="Create Named Reference Bus",
            category="Bus/MiniMax",
            description=schema.description,
            search_aliases=schema.search_aliases,
            accept_all_inputs=True,
            inputs=schema.inputs,
            outputs=schema.outputs,
        )


class MiniMaxH3ExpandNamedReferenceBus(io.ComfyNode):
    """Expand a Named Reference Bus into individual outputs for each attached entity."""

    _RETURN_TYPES = DynamicReturnTypes()

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ExpandNamedReferenceBus",
            display_name="Expand Named Reference Bus",
            category="Bus/MiniMax",
            description="Unpack a Named Reference Bus into individual outputs for every attached entity, labeled by filename.",
            search_aliases=["Expand Named Reference Bus", "Named Reference Bus", "NamedReferenceBus", "ExpandReferenceBus"],
            inputs=[
                io.MultiType.Input(
                    "bus",
                    types=[H3NamedRefBusType, H3RefBusType],
                    tooltip="Named Reference Bus to expand into individual entity outputs.",
                ),
            ],
            outputs=[],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None, **kwargs) -> io.NodeOutput:
        bus = bus or {}
        items: list[Any] = []
        if "entities" in bus:
            items = [e["value"] for e in bus["entities"]]
        elif "ordered" in bus:
            items = list(bus["ordered"])
        else:
            items = (
                list(bus.get("ref_images", {}).values())
                + list(bus.get("ref_videos", {}).values())
                + list(bus.get("ref_video_audios", {}).values())
                + list(bus.get("ref_audios", {}).values())
            )

        if not items:
            return io.NodeOutput(None)
        return io.NodeOutput(*items)


class ExpandNamedReferenceBus(MiniMaxH3ExpandNamedReferenceBus):
    """Expand a Named Reference Bus into individual outputs for each attached entity (alias)."""

    _RETURN_TYPES = DynamicReturnTypes()

    @classmethod
    def define_schema(cls):
        schema = super().define_schema()
        return io.Schema(
            node_id="ExpandNamedReferenceBus",
            display_name="Expand Named Reference Bus",
            category="Bus/MiniMax",
            description=schema.description,
            search_aliases=schema.search_aliases,
            inputs=schema.inputs,
            outputs=schema.outputs,
        )


class MiniMaxH3MapNamedReferenceBus(io.ComfyNode):
    """Map a Named Reference Bus into a standard MiniMax H3 Reference Bus via explicit slot mapping."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3MapNamedReferenceBus",
            display_name="Map Named Bus to H3 Reference Bus",
            category="Bus/MiniMax",
            description="Map entities from an incoming Named Reference Bus into standard MiniMax H3 reference slots (<Picture 1..9>, <Video 1..3>, <Audio 1..3>).",
            search_aliases=["Map Named Reference Bus", "Named Reference Bus to H3", "MapNamedReferenceBus", "NamedBusToH3Bus"],
            inputs=[
                io.MultiType.Input(
                    "bus",
                    types=[H3NamedRefBusType, H3RefBusType],
                    tooltip="Incoming Named Reference Bus to map to standard H3 reference slots.",
                ),
                io.String.Input(
                    "mapping",
                    default="{}",
                    tooltip="Slot mapping configuration in JSON format. Use the 'Map Slots...' button to configure interactively.",
                ),
            ],
            outputs=[H3RefBusType.Output("bus", display_name="bus")],
        )

    @classmethod
    def execute(
        cls,
        bus: dict[str, Any] | None = None,
        mapping: str | dict[str, str] | None = None,
        **kwargs,
    ) -> io.NodeOutput:
        bus = bus or {}

        # 1. Build entities lookup from incoming bus
        entities_by_name: dict[str, Any] = {}
        ordered_entities: list[dict[str, Any]] = []

        if "entities" in bus:
            for item in bus["entities"]:
                name = item.get("name", "")
                val = item.get("value")
                if name and val is not None:
                    entities_by_name[name] = val
                    ordered_entities.append(item)
        elif "by_name" in bus:
            entities_by_name = dict(bus["by_name"])
            ordered_entities = [{"name": k, "value": v} for k, v in entities_by_name.items()]
        else:
            # Fallback for standard H3 reference bus inputs
            for prefix in ("ref_images", "ref_videos", "ref_video_audios", "ref_audios"):
                for k, v in bus.get(prefix, {}).items():
                    if v is not None:
                        entities_by_name[k] = v
                        ordered_entities.append({"name": k, "value": v})

        # 2. Parse slot mapping
        slot_map: dict[str, str] = {}
        if isinstance(mapping, str):
            try:
                slot_map = json.loads(mapping) if mapping.strip() else {}
            except Exception:
                pass
        elif isinstance(mapping, dict):
            slot_map = dict(mapping)

        out_bus: dict[str, Any] = {
            "ref_images": {},
            "ref_videos": {},
            "ref_video_audios": {},
            "ref_audios": {},
        }

        # 3. Apply explicit mapping if configured
        if slot_map:
            # Images (<Picture 1> .. <Picture 9>)
            for i in range(9):
                key = f"ref_image_{i}"
                target_name = slot_map.get(key)
                if target_name and target_name in entities_by_name:
                    out_bus["ref_images"][key] = entities_by_name[target_name]

            # Videos (<Video 1> .. <Video 3>)
            for i in range(3):
                key = f"ref_video_{i}"
                target_name = slot_map.get(key)
                if target_name and target_name in entities_by_name:
                    out_bus["ref_videos"][key] = entities_by_name[target_name]

            # Video Soundtracks (<Video 1 Soundtrack> .. <Video 3 Soundtrack>)
            for i in range(3):
                key = f"ref_video_audio_{i}"
                target_name = slot_map.get(key)
                if target_name and target_name in entities_by_name:
                    out_bus["ref_video_audios"][key] = entities_by_name[target_name]

            # Standalone Audios (<Audio 1> .. <Audio 3>)
            for i in range(3):
                key = f"ref_audio_{i}"
                target_name = slot_map.get(key)
                if target_name and target_name in entities_by_name:
                    out_bus["ref_audios"][key] = entities_by_name[target_name]
        else:
            # Automatic mapping fallback when no explicit mapping is set
            img_idx = 0
            aud_idx = 0
            vid_idx = 0
            for item in ordered_entities:
                v = item.get("value")
                if v is None:
                    continue
                name_lower = str(item.get("name", "")).lower()
                is_audio = (
                    item.get("type") == "AUDIO"
                    or (isinstance(v, dict) and "waveform" in v)
                    or any(name_lower.endswith(ext) for ext in (".flac", ".mp3", ".wav", ".ogg", ".m4a"))
                )
                is_video = (
                    item.get("type") == "VIDEO"
                    or any(name_lower.endswith(ext) for ext in (".mp4", ".mov", ".webm", ".mkv"))
                    or (hasattr(v, "shape") and len(v.shape) == 4 and v.shape[0] > 1 and "video" in name_lower)
                )

                if is_audio:
                    if aud_idx < 3:
                        out_bus["ref_audios"][f"ref_audio_{aud_idx}"] = v
                        aud_idx += 1
                elif is_video:
                    if vid_idx < 3:
                        out_bus["ref_videos"][f"ref_video_{vid_idx}"] = v
                        vid_idx += 1
                else:
                    if img_idx < 9:
                        out_bus["ref_images"][f"ref_image_{img_idx}"] = v
                        img_idx += 1

        out_bus["entities"] = ordered_entities
        out_bus["by_name"] = entities_by_name

        total_img = len(out_bus["ref_images"])
        total_vid = len(out_bus["ref_videos"])
        total_va = len(out_bus["ref_video_audios"])
        total_aud = len(out_bus["ref_audios"])

        img_tag = f"<Picture 1..{total_img}>" if total_img > 1 else ("<Picture 1>" if total_img == 1 else "none")
        vid_tag = f"<Video 1..{total_vid}>" if total_vid > 1 else ("<Video 1>" if total_vid == 1 else "none")
        aud_tag = f"<Audio 1..{total_aud}>" if total_aud > 1 else ("<Audio 1>" if total_aud == 1 else "none")

        summary_text = (
            f"[Mapped H3 Reference Bus]\n"
            f"Images: {total_img} ({img_tag})\n"
            f"Videos: {total_vid} ({vid_tag})\n"
            f"Soundtracks: {total_va}\n"
            f"Audios: {total_aud} ({aud_tag})"
        )

        return io.NodeOutput(out_bus, ui=PreviewText(summary_text))


class MapNamedReferenceBus(MiniMaxH3MapNamedReferenceBus):
    """Map a Named Reference Bus into a standard MiniMax H3 Reference Bus (alias)."""

    @classmethod
    def define_schema(cls):
        schema = super().define_schema()
        return io.Schema(
            node_id="MapNamedReferenceBus",
            display_name="Map Named Bus to H3 Reference Bus",
            category="Bus/MiniMax",
            description=schema.description,
            search_aliases=schema.search_aliases,
            inputs=schema.inputs,
            outputs=schema.outputs,
        )


NamedBusToH3Bus = MapNamedReferenceBus



class MiniMaxH3CreateVideoSettingsBus(io.ComfyNode):
    """Create a MiniMax H3 video settings bus bundling model, clip, video VAE, audio VAE, width, height, and steps."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3CreateVideoSettingsBus",
            display_name="Create MiniMax H3 Video Settings Bus",
            category="Bus/MiniMax",
            description="Bundle global video settings (model, clip, video VAE, audio VAE, width, height, steps) into a single bus for MiniMax H3 workflows.",
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
                io.Int.Input("steps", default=20, min=1, max=10000, step=1, tooltip="Sampling steps (default 20)"),
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
        steps: int = 20,
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
            "steps": steps if steps is not None else bus.get("steps", 20),
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
            f"Resolution: {out_bus['width']}x{out_bus['height']}\n"
            f"Steps: {out_bus['steps']}"
        )

        return io.NodeOutput(out_bus, ui=PreviewText(summary))


class MiniMaxH3ExpandVideoSettingsBus(io.ComfyNode):
    """Expand a MiniMax H3 video settings bus into model, clip, video VAE, audio VAE, width, height, and steps."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ExpandVideoSettingsBus",
            display_name="Expand MiniMax H3 Video Settings Bus",
            category="Bus/MiniMax",
            description="Unpack a MiniMax H3 video settings bus into model, clip, video VAE, audio VAE, width, height, and steps.",
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
                io.Int.Output("steps", display_name="steps", tooltip="Sampling steps"),
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
            bus.get("steps", 20),
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


class MiniMaxH3StepsFromBus(io.ComfyNode):
    """Extract sampling steps integer from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3StepsFromBus",
            display_name="Steps from Bus",
            category="Bus/MiniMax",
            description="Extract sampling steps integer from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Int.Output("steps", display_name="steps", tooltip="Sampling steps")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("steps", 20))


class GetStepsFromBus(io.ComfyNode):
    """Extract sampling steps integer from a MiniMax H3 video settings bus."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="GetStepsFromBus",
            display_name="Get Steps from Bus",
            category="Bus/MiniMax",
            description="Extract sampling steps integer from a MiniMax H3 video settings bus.",
            inputs=[H3VideoSettingsBusType.Input("bus", tooltip="Video settings bus")],
            outputs=[io.Int.Output("steps", display_name="steps", tooltip="Sampling steps")],
        )

    @classmethod
    def execute(cls, bus: dict[str, Any] | None = None) -> io.NodeOutput:
        bus = bus or {}
        return io.NodeOutput(bus.get("steps", 20))


# ==============================================================================
# MiniMax H3 NestedTensor Latent Save & Load Nodes for Multi-Part Long Videos
# ==============================================================================

FPS = 24
AUDIO_LATENT_FPS = 40


def _h3_video_t_from_frame_count(frame_count: int) -> int:
    """Return the MiniMax H3 video latent length (T) for an aligned frame count."""
    if frame_count <= 5:
        return 2
    return ((frame_count - 5) // 17) * 5 + 2


def _h3_frame_count_from_video_t(video_t: int) -> int:
    """Return the pixel-frame count represented by a MiniMax H3 video latent length (T)."""
    if video_t < 2:
        return max(1, video_t * 4)
    if (video_t - 2) % 5 != 0:
        return ((video_t - 2) // 5) * 17 + 5
    groups = (video_t - 2) // 5
    return groups * 17 + 5


def _h3_audio_t_at_frame(frame_index: int) -> int:
    """Return cumulative 40 Hz audio-latent index at a 24 fps frame boundary."""
    return round(frame_index * AUDIO_LATENT_FPS / FPS)


def _get_latent_files() -> list[str]:
    """Scan both output and input directories (and their subdirectories) for .latent and .safetensors files."""
    found = set()
    # 1. Output directory
    try:
        output_dir = folder_paths.get_output_directory()
        if output_dir and os.path.exists(output_dir):
            for root, _, filenames in os.walk(output_dir):
                for f in filenames:
                    if f.endswith(".latent") or f.endswith(".safetensors"):
                        rel = os.path.relpath(os.path.join(root, f), output_dir).replace("\\", "/")
                        found.add(f"{rel} [output]")
    except Exception:
        pass

    # 2. Input directory
    try:
        input_dir = folder_paths.get_input_directory()
        if input_dir and os.path.exists(input_dir):
            for root, _, filenames in os.walk(input_dir):
                for f in filenames:
                    if f.endswith(".latent") or f.endswith(".safetensors"):
                        rel = os.path.relpath(os.path.join(root, f), input_dir).replace("\\", "/")
                        found.add(f"{rel} [input]")
                        found.add(rel)
    except Exception:
        pass

    sorted_files = sorted(list(found))
    return sorted_files if sorted_files else ["none"]


def _extract_h3_av_streams(latent: Any) -> tuple[torch.Tensor, torch.Tensor | None, list[torch.Tensor], bool]:
    """Safely extract video, audio, and extra streams from a ComfyUI latent dict or raw latent."""
    samples = latent.get("samples") if isinstance(latent, dict) else latent
    if samples is None:
        raise ValueError("Latent contains no samples")

    is_nested = getattr(samples, "is_nested", False)
    if is_nested:
        tensors = samples.unbind()
        if not tensors:
            raise ValueError("NestedTensor contains no tensors")
        video = tensors[0]
        audio = tensors[1] if len(tensors) > 1 else None
        extras = list(tensors[2:]) if len(tensors) > 2 else []
        return video, audio, extras, True
    elif isinstance(samples, torch.Tensor):
        return samples, None, [], False
    else:
        raise TypeError(f"Expected NestedTensor or torch.Tensor in samples, got {type(samples)}")


class MiniMaxH3SaveNestedLatent(io.ComfyNode):
    """Save MiniMax H3 joint video+audio NestedTensor latents to disk for multi-part long video workflows."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3SaveNestedLatent",
            display_name="Save MiniMax H3 AV Latent (NestedTensor)",
            category="Bus/MiniMax/Latent",
            description=(
                "Saves MiniMax H3 joint video and synchronized audio latents in NestedTensor format to disk as .latent (safetensors). "
                "Prevents crashes caused by standard SaveLatent on multi-stream NestedTensors and attaches part numbering, frame count, "
                "and timing metadata to streamline rendering long videos in parts."
            ),
            search_aliases=[
                "save minimax h3 latent",
                "save nested tensor",
                "save av latent",
                "h3 save latent",
                "save video part",
                "save h3 part",
                "export h3 latent",
            ],
            inputs=[
                io.Latent.Input("samples", tooltip="MiniMax H3 joint AV latent (NestedTensor containing video and audio streams)"),
                io.String.Input(
                    "filename_prefix",
                    default="latents/h3_part",
                    tooltip="Filename prefix and optional subfolder (e.g. 'latents/scene_01'). Supports standard ComfyUI format tokens like %date:yyyy-MM-dd%.",
                ),
                io.Int.Input(
                    "part_number",
                    default=1,
                    min=0,
                    max=9999,
                    step=1,
                    tooltip="Part number in multi-part long video sequences (e.g. 1 for Part 1). When > 0, adds '_part_XX' to the filename. Set to 0 to disable.",
                ),
                io.Boolean.Input(
                    "append_counter",
                    default=True,
                    tooltip="Append ComfyUI sequential counter (_00001_) to prevent overwriting previous takes.",
                ),
                io.Boolean.Input(
                    "save_output",
                    default=True,
                    tooltip="Save the file to disk. If False, acts as a non-saving pass-through.",
                ),
            ],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
            is_output_node=True,
            outputs=[
                io.Latent.Output("samples", display_name="samples", tooltip="Pass-through of the input AV latent for downstream nodes (e.g. VAE Decode or continuation)"),
            ],
        )

    @classmethod
    def execute(
        cls,
        samples: Any,
        filename_prefix: str = "latents/h3_part",
        part_number: int = 1,
        append_counter: bool = True,
        save_output: bool = True,
        prompt: Any = None,
        extra_pnginfo: Any = None,
        **kwargs,
    ) -> io.NodeOutput:
        if samples is None:
            raise ValueError("MiniMaxH3SaveNestedLatent: input samples is None")

        video, audio, extras, is_nested = _extract_h3_av_streams(samples)

        # Inspect dimensions
        if video.ndim == 5:
            b, c, t, h, w = video.shape
            width = w * 16
            height = h * 16
            frame_count = _h3_frame_count_from_video_t(t)
            video_dur = frame_count / FPS
        else:
            width = 0
            height = 0
            frame_count = 0
            video_dur = 0.0

        if audio is not None:
            audio_dur = audio.shape[-1] / AUDIO_LATENT_FPS
        else:
            audio_dur = 0.0

        # Construct safetensors state dict without shared memory references
        sd = {
            "video_latent": video.contiguous().cpu(),
            "latent_format_version_0": torch.tensor([]),
            "is_h3_nested": torch.tensor([1 if is_nested else 0], dtype=torch.uint8),
            "num_streams": torch.tensor([1 + (1 if audio is not None else 0) + len(extras)], dtype=torch.int32),
        }

        if audio is not None:
            sd["audio_latent"] = audio.contiguous().cpu()

        for idx, extra in enumerate(extras):
            sd[f"stream_{idx + 2}"] = extra.contiguous().cpu()

        # Handle noise mask
        noise_mask = samples.get("noise_mask") if isinstance(samples, dict) else None
        if noise_mask is not None:
            if getattr(noise_mask, "is_nested", False):
                nm_streams = noise_mask.unbind()
                sd["video_noise_mask"] = nm_streams[0].contiguous().cpu()
                if len(nm_streams) > 1:
                    sd["audio_noise_mask"] = nm_streams[1].contiguous().cpu()
            elif isinstance(noise_mask, torch.Tensor):
                sd["noise_mask"] = noise_mask.contiguous().cpu()

        # Prepare metadata (safetensors requires all metadata values to be strings)
        metadata = {
            "format": "MiniMax_H3_NestedTensor",
            "part_number": str(part_number),
            "frame_count": str(frame_count),
            "video_frames": str(frame_count),
            "video_shape": json.dumps(list(video.shape)),
            "audio_shape": json.dumps(list(audio.shape)) if audio is not None else "",
            "video_duration_seconds": f"{video_dur:.3f}",
            "audio_duration_seconds": f"{audio_dur:.3f}" if audio is not None else "",
            "width": str(width),
            "height": str(height),
            "fps": str(FPS),
        }

        if prompt is not None:
            metadata["prompt"] = json.dumps(prompt)
        if extra_pnginfo is not None:
            for k, v in extra_pnginfo.items():
                metadata[k] = json.dumps(v)

        # Build path and filename
        prefix = filename_prefix.strip()
        if part_number > 0:
            part_tag = f"part_{part_number:02d}"
            if not (prefix.endswith(part_tag) or prefix.endswith(f"part{part_number:02d}")):
                prefix = f"{prefix}_{part_tag}"

        output_dir = folder_paths.get_output_directory()
        full_output_folder, base_filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            prefix, output_dir
        )
        os.makedirs(full_output_folder, exist_ok=True)

        if append_counter:
            file_name = f"{base_filename}_{counter:05}_.latent"
        else:
            file_name = f"{base_filename}.latent"

        full_filepath = os.path.join(full_output_folder, file_name)

        file_size_mb = 0.0
        if save_output:
            comfy.utils.save_torch_file(sd, full_filepath, metadata=metadata)
            if os.path.exists(full_filepath):
                file_size_mb = os.path.getsize(full_filepath) / (1024 * 1024)

        results = [{
            "filename": file_name,
            "subfolder": subfolder,
            "type": "output"
        }]

        status_str = f"{file_size_mb:.2f} MB" if save_output else "Pass-through (Not Saved)"
        summary_text = (
            f"[Saved MiniMax H3 AV Latent]\n"
            f"File: {file_name}\n"
            f"Folder: {subfolder or '(output root)'}\n"
            f"Part: {part_number if part_number > 0 else 'N/A'}\n"
            f"Video: {frame_count} frames ({video_dur:.2f}s @ {FPS}fps, {width}x{height})\n"
            f"Audio: {'Synchronized (' + f'{audio_dur:.2f}s)' if audio is not None else 'None'}\n"
            f"Streams: {sd['num_streams'].item()} (NestedTensor)\n"
            f"Size: {status_str}"
        )

        return io.NodeOutput(
            samples,
            ui={"text": (summary_text,), "latents": results}
        )


class MiniMaxH3LoadNestedLatent(io.ComfyNode):
    """Load MiniMax H3 joint video+audio NestedTensor latents from disk for multi-part long video workflows."""

    @classmethod
    def define_schema(cls):
        files = _get_latent_files()
        return io.Schema(
            node_id="MiniMaxH3LoadNestedLatent",
            display_name="Load MiniMax H3 AV Latent (NestedTensor)",
            category="Bus/MiniMax/Latent",
            description=(
                "Loads MiniMax H3 joint video and synchronized audio latents saved in NestedTensor format from input or output directories. "
                "Reconstructs the native NestedTensor((video, audio)) object required by MiniMax H3 samplers, continuation nodes, and VAE decoders. "
                "Also outputs separate video and audio latents, frame count, part number, and duration to streamline long video continuation."
            ),
            search_aliases=[
                "load minimax h3 latent",
                "load nested tensor",
                "load av latent",
                "h3 load latent",
                "load video part",
                "load h3 part",
                "open h3 latent",
            ],
            inputs=[
                io.Combo.Input(
                    "latent_file",
                    options=files,
                    tooltip="Select a saved latent file (.latent or .safetensors) from output or input directory.",
                ),
                io.String.Input(
                    "custom_path",
                    default="",
                    optional=True,
                    tooltip="Optional direct path or filename override. Supports absolute paths or paths relative to ComfyUI input/output folders.",
                ),
            ],
            outputs=[
                io.Latent.Output("samples", display_name="samples", tooltip="Combined MiniMax H3 joint AV latent (NestedTensor) ready for KSampler, continuation nodes, or VAE Decode"),
                io.Latent.Output("video_latent", display_name="video_latent", tooltip="Video stream alone wrapped as LATENT dict, ready for standard video nodes or VAE Decode"),
                io.Latent.Output("audio_latent", display_name="audio_latent", tooltip="Audio stream alone wrapped as LATENT dict, ready for VAEDecodeAudio"),
                io.Int.Output("frame_count", display_name="frame_count", tooltip="Total pixel frames represented by this latent at 24 fps"),
                io.Int.Output("part_number", display_name="part_number", tooltip="Part number extracted from file metadata or filename (defaults to 1)"),
                io.Int.Output("width", display_name="width", tooltip="Video width in pixels"),
                io.Int.Output("height", display_name="height", tooltip="Video height in pixels"),
                io.Float.Output("duration", display_name="duration", tooltip="Duration in seconds at 24 fps"),
            ],
        )

    @classmethod
    def _resolve_filepath(cls, latent_file: str, custom_path: str | None = None) -> str:
        """Resolve the full path of the target latent file across input, output, and custom locations."""
        if custom_path and custom_path.strip():
            cp = custom_path.strip()
            # 1. Absolute path
            if os.path.isabs(cp) and os.path.exists(cp):
                return cp
            # 2. Relative to output directory
            out_candidate = os.path.join(folder_paths.get_output_directory(), cp)
            if os.path.exists(out_candidate):
                return out_candidate
            # 3. Relative to input directory
            inp_candidate = os.path.join(folder_paths.get_input_directory(), cp)
            if os.path.exists(inp_candidate):
                return inp_candidate
            # 4. Try ComfyUI annotated path resolver
            try:
                resolved = folder_paths.get_annotated_filepath(cp)
                if os.path.exists(resolved):
                    return resolved
            except Exception:
                pass
            if os.path.exists(cp):
                return os.path.abspath(cp)
            raise FileNotFoundError(f"MiniMaxH3LoadNestedLatent: custom_path file not found: {custom_path}")

        if not latent_file or latent_file == "none":
            raise ValueError("MiniMaxH3LoadNestedLatent: no latent file selected and custom_path is empty")

        return folder_paths.get_annotated_filepath(latent_file)

    @classmethod
    def fingerprint_inputs(cls, latent_file: str, custom_path: str = "") -> str:
        try:
            resolved = cls._resolve_filepath(latent_file, custom_path)
            if os.path.exists(resolved):
                mtime = os.path.getmtime(resolved)
                return hashlib.sha256(f"{resolved}_{mtime}".encode()).hexdigest()
        except Exception:
            pass
        return f"{latent_file}_{custom_path}"

    @classmethod
    def validate_inputs(cls, latent_file: str, custom_path: str = "") -> bool | str:
        try:
            resolved = cls._resolve_filepath(latent_file, custom_path)
            if not os.path.exists(resolved):
                return f"Latent file does not exist: {resolved}"
            return True
        except Exception as e:
            return str(e)

    @classmethod
    def execute(
        cls,
        latent_file: str,
        custom_path: str = "",
        **kwargs,
    ) -> io.NodeOutput:
        resolved_path = cls._resolve_filepath(latent_file, custom_path)
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"MiniMaxH3LoadNestedLatent: file not found at {resolved_path}")

        sd = safetensors.torch.load_file(resolved_path, device="cpu")
        metadata = {}
        try:
            with safe_open(resolved_path, framework="pt") as f:
                metadata = f.metadata() or {}
        except Exception:
            pass

        # 1. Extract video stream
        video = None
        for k in ["video_latent", "latent_tensor", "stream_0"]:
            if k in sd:
                video = sd[k]
                break
        if video is None:
            for v in sd.values():
                if isinstance(v, torch.Tensor) and v.ndim in (4, 5):
                    video = v
                    break
        if video is None:
            raise ValueError(f"Could not find video latent tensor in {resolved_path}")

        # 2. Extract audio stream
        audio = None
        for k in ["audio_latent", "audio_tensor", "stream_1"]:
            if k in sd:
                audio = sd[k]
                break

        # 3. Extract extra streams if any
        extras = []
        idx = 2
        while f"stream_{idx}" in sd:
            extras.append(sd[f"stream_{idx}"])
            idx += 1

        # 4. Reconstruct NestedTensor
        is_nested_flag = sd.get("is_h3_nested")
        was_nested = bool(is_nested_flag.item()) if is_nested_flag is not None else (audio is not None)

        if audio is not None or extras or was_nested:
            all_streams = [video]
            if audio is not None:
                all_streams.append(audio)
            all_streams.extend(extras)
            combined_samples = NestedTensor(all_streams)
        else:
            combined_samples = video

        # 5. Extract noise mask if present
        noise_mask = None
        if "video_noise_mask" in sd and "audio_noise_mask" in sd:
            noise_mask = NestedTensor((sd["video_noise_mask"], sd["audio_noise_mask"]))
        elif "video_noise_mask" in sd:
            noise_mask = sd["video_noise_mask"]
        elif "noise_mask" in sd:
            noise_mask = sd["noise_mask"]

        samples_out = {"samples": combined_samples}
        if noise_mask is not None:
            samples_out["noise_mask"] = noise_mask

        # Individual stream latent dicts
        video_out = {"samples": video}
        if "video_noise_mask" in sd:
            video_out["noise_mask"] = sd["video_noise_mask"]

        if audio is not None:
            audio_out = {"samples": audio}
            if "audio_noise_mask" in sd:
                audio_out["noise_mask"] = sd["audio_noise_mask"]
        else:
            audio_out = {"samples": torch.zeros((1, 32, 2, 0))}

        # Calculate dimensions and metadata
        if video.ndim == 5:
            b, c, t, h, w = video.shape
            width = w * 16
            height = h * 16
            frame_count = _h3_frame_count_from_video_t(t)
        else:
            width = int(metadata.get("width", 1344))
            height = int(metadata.get("height", 768))
            meta_fc = metadata.get("frame_count") or metadata.get("video_frames")
            frame_count = int(meta_fc) if meta_fc else 124

        duration = round(frame_count / FPS, 3)

        # Part number
        part_num = None
        if "part_number" in metadata:
            try:
                part_num = int(metadata["part_number"])
            except (ValueError, TypeError):
                pass
        if part_num is None:
            basename = os.path.basename(resolved_path)
            match = re.search(r"part[_-]?(\d+)", basename, re.IGNORECASE)
            if match:
                part_num = int(match.group(1))
            else:
                part_num = 1

        audio_info = f"Synchronized ({audio.shape[-1]} tokens, ~{audio.shape[-1]/AUDIO_LATENT_FPS:.2f}s)" if audio is not None else "None"
        file_size_mb = os.path.getsize(resolved_path) / (1024 * 1024)

        summary_text = (
            f"[Loaded MiniMax H3 AV Latent]\n"
            f"File: {os.path.basename(resolved_path)}\n"
            f"Part: {part_num}\n"
            f"Video: {frame_count} frames ({duration:.2f}s @ {FPS}fps, {width}x{height})\n"
            f"Audio: {audio_info}\n"
            f"NestedTensor: {'Yes (' + str(len(all_streams)) + ' streams)' if (audio is not None or extras or was_nested) else 'No'}\n"
            f"Size: {file_size_mb:.2f} MB"
        )

        return io.NodeOutput(
            samples_out,
            video_out,
            audio_out,
            frame_count,
            part_num,
            width,
            height,
            duration,
            ui=PreviewText(summary_text),
        )


class MiniMaxH3ConcatAVLatent(io.ComfyNode):
    """Concatenate two or three MiniMax H3 AV Latents (NestedTensor) along the temporal timeline to assemble long videos in parts."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="MiniMaxH3ConcatAVLatent",
            display_name="Concat MiniMax H3 AV Latents",
            category="Bus/MiniMax/Latent",
            description=(
                "Stitches two or three MiniMax H3 joint AV latents (NestedTensor) together along their temporal axes "
                "(video along dim 2, audio along dim -1). Maintains synchronized video and audio lengths for full-length long video decode."
            ),
            search_aliases=[
                "concat minimax h3 latents",
                "stitch video parts",
                "join h3 latents",
                "concatenate av latents",
                "merge h3 parts",
                "combine h3 latents",
            ],
            inputs=[
                io.Latent.Input("latent_a", tooltip="First MiniMax H3 AV latent (Part N)"),
                io.Latent.Input("latent_b", tooltip="Second MiniMax H3 AV latent (Part N+1)"),
                io.Latent.Input("latent_c", optional=True, tooltip="Optional third MiniMax H3 AV latent (Part N+2)"),
                io.Int.Input(
                    "trim_overlap_tokens",
                    default=0,
                    min=0,
                    max=1000,
                    step=1,
                    tooltip="Video tokens to trim from the start of subsequent parts (latent_b, latent_c) to eliminate continuation overlap. (5 video tokens = 17 frames = 28 audio tokens).",
                ),
            ],
            outputs=[
                io.Latent.Output("samples", display_name="samples", tooltip="Combined stitched MiniMax H3 AV latent (NestedTensor)"),
                io.Latent.Output("video_latent", display_name="video_latent", tooltip="Stitched video stream alone"),
                io.Latent.Output("audio_latent", display_name="audio_latent", tooltip="Stitched audio stream alone"),
                io.Int.Output("total_frame_count", display_name="total_frame_count", tooltip="Total pixel frames in stitched video"),
                io.Float.Output("duration", display_name="duration", tooltip="Total duration in seconds at 24 fps"),
            ],
        )

    @classmethod
    def execute(
        cls,
        latent_a: Any,
        latent_b: Any,
        latent_c: Any = None,
        trim_overlap_tokens: int = 0,
        **kwargs,
    ) -> io.NodeOutput:
        v_a, a_a, _, _ = _extract_h3_av_streams(latent_a)
        v_b, a_b, _, _ = _extract_h3_av_streams(latent_b)

        # Check spatial dimensions
        if v_a.shape[3:] != v_b.shape[3:]:
            raise ValueError(
                f"MiniMaxH3ConcatAVLatent: Spatial dimensions mismatch between latent_a ({v_a.shape[3:]}) and latent_b ({v_b.shape[3:]})"
            )

        video_list = [v_a]
        audio_list = [a_a] if a_a is not None else []

        # Trim overlap on latent_b if requested
        if trim_overlap_tokens > 0:
            if trim_overlap_tokens >= v_b.shape[2]:
                raise ValueError("trim_overlap_tokens cannot be greater than or equal to latent_b video length")
            v_b = v_b[:, :, trim_overlap_tokens:]
            if a_b is not None:
                trim_frames = _h3_frame_count_from_video_t(trim_overlap_tokens)
                trim_audio_t = _h3_audio_t_at_frame(trim_frames)
                if trim_audio_t < a_b.shape[-1]:
                    a_b = a_b[..., trim_audio_t:]

        video_list.append(v_b)
        if a_b is not None:
            audio_list.append(a_b)

        if latent_c is not None:
            v_c, a_c, _, _ = _extract_h3_av_streams(latent_c)
            if v_c.shape[3:] != v_a.shape[3:]:
                raise ValueError(
                    f"MiniMaxH3ConcatAVLatent: Spatial dimensions mismatch between latent_a and latent_c ({v_c.shape[3:]})"
                )
            if trim_overlap_tokens > 0:
                if trim_overlap_tokens >= v_c.shape[2]:
                    raise ValueError("trim_overlap_tokens cannot be greater than or equal to latent_c video length")
                v_c = v_c[:, :, trim_overlap_tokens:]
                if a_c is not None:
                    trim_frames = _h3_frame_count_from_video_t(trim_overlap_tokens)
                    trim_audio_t = _h3_audio_t_at_frame(trim_frames)
                    if trim_audio_t < a_c.shape[-1]:
                        a_c = a_c[..., trim_audio_t:]
            video_list.append(v_c)
            if a_c is not None:
                audio_list.append(a_c)

        # Concatenate along time axis (video dim=2, audio dim=-1)
        full_video = torch.cat(video_list, dim=2)
        if len(audio_list) == len(video_list):
            full_audio = torch.cat(audio_list, dim=-1)
            combined_samples = NestedTensor((full_video, full_audio))
            audio_out = {"samples": full_audio}
        else:
            full_audio = None
            combined_samples = full_video
            audio_out = {"samples": torch.zeros((1, 32, 2, 0))}

        total_frame_count = _h3_frame_count_from_video_t(full_video.shape[2])
        duration = round(total_frame_count / FPS, 3)

        samples_out = {"samples": combined_samples}
        video_out = {"samples": full_video}

        summary_text = (
            f"[Concatenated MiniMax H3 Latents]\n"
            f"Parts: {len(video_list)}\n"
            f"Total Frames: {total_frame_count} ({duration:.2f}s @ {FPS}fps)\n"
            f"Resolution: {full_video.shape[4] * 16}x{full_video.shape[3] * 16}\n"
            f"Audio: {'Synchronized (' + f'{full_audio.shape[-1]} tokens)' if full_audio is not None else 'None'}"
        )

        return io.NodeOutput(
            samples_out,
            video_out,
            audio_out,
            total_frame_count,
            duration,
            ui=PreviewText(summary_text),
        )


# Aliases for convenience and compatibility
MiniMaxH3SaveAVLatent = MiniMaxH3SaveNestedLatent
MiniMaxH3LoadAVLatent = MiniMaxH3LoadNestedLatent
MiniMaxH3ConcatAVLatents = MiniMaxH3ConcatAVLatent


# ---------------------------------------------------------------------------
# Text Loading Nodes
# ---------------------------------------------------------------------------

class LoadText(io.ComfyNode):
    """Load text contents from a local file as a string for prompts, scripts, or workflows."""

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="LoadText",
            display_name="Load Text",
            category="text",
            description=(
                "Loads text from a local file (e.g. .txt, .md, .json, .yaml, .prompt) and returns "
                "the entire contents as a string. Features a 'Choose File' button to select files "
                "via native file dialog, supports drag-and-drop, and automatically reloads when "
                "the file is modified on disk."
            ),
            search_aliases=[
                "load text",
                "read text",
                "load text file",
                "read file",
                "open text",
                "open file",
                "load prompt",
                "read prompt",
                "text loader",
                "load markdown",
                "prompt file",
                "loadtext",
                "h3 load text",
            ],
            inputs=[
                io.String.Input(
                    "filename",
                    default="",
                    tooltip=(
                        "Path or filename of the text file to load. "
                        "Click 'Choose File...' to select a file via native file dialog, or enter/paste an absolute or relative path."
                    ),
                ),
                io.Combo.Input(
                    "auto_reload",
                    options=["on_file_change", "always"],
                    default="on_file_change",
                    tooltip=(
                        "How auto-updating behaves:\n"
                        "- 'on_file_change': Monitors file timestamp, size, and SHA256 content hash on disk to automatically reload whenever modified.\n"
                        "- 'always': Forces re-reading the file from disk on every queue execution, completely bypassing cache."
                    ),
                ),
            ],
            outputs=[
                io.String.Output(
                    "text",
                    display_name="STRING",
                    tooltip="The contents of the loaded file as a string.",
                ),
            ],
        )

    @classmethod
    def _clean_path(cls, path_str: str) -> str:
        """Strip quotes, leading/trailing whitespace, and expand variables/user."""
        if not path_str:
            return ""
        p = path_str.strip()
        # Strip surrounding double quotes, single quotes, or backticks
        if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")) or (p.startswith("`") and p.endswith("`")):
            p = p[1:-1].strip()
        p = os.path.expanduser(p)
        p = os.path.expandvars(p)
        return p

    @classmethod
    def _resolve_filepath(cls, filename: str) -> str:
        """Resolve a filename or path across absolute paths, CWD, and ComfyUI directories."""
        clean = cls._clean_path(filename)
        if not clean:
            raise ValueError("LoadText: No filename provided. Please provide a file path or click 'Choose File...' to select a file.")

        # 1. Direct path check (handles absolute paths and paths relative to CWD)
        if os.path.isfile(clean):
            return os.path.abspath(clean)

        # 2. Check relative to ComfyUI input directory
        input_dir = None
        try:
            input_dir = folder_paths.get_input_directory()
            candidate = os.path.join(input_dir, clean)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        except Exception:
            pass

        # 3. Check relative to ComfyUI output directory
        output_dir = None
        try:
            output_dir = folder_paths.get_output_directory()
            candidate = os.path.join(output_dir, clean)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        except Exception:
            pass

        # 4. Check relative to ComfyUI base path
        if hasattr(folder_paths, "base_path") and folder_paths.base_path:
            candidate = os.path.join(folder_paths.base_path, clean)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

        # 5. Try ComfyUI annotated path resolver
        try:
            annotated = folder_paths.get_annotated_filepath(clean)
            if os.path.isfile(annotated):
                return os.path.abspath(annotated)
        except Exception:
            pass

        # 6. Check common subfolders in input directory (e.g. input/text/)
        if input_dir:
            candidate = os.path.join(input_dir, "text", clean)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

            base_name = os.path.basename(clean)
            candidate = os.path.join(input_dir, base_name)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)

        if os.path.isabs(clean):
            raise FileNotFoundError(f"LoadText: File not found at absolute path: '{clean}'")

        raise FileNotFoundError(
            f"LoadText: File not found: '{clean}'.\n"
            f"Checked direct path ({os.path.abspath(clean)}), "
            f"input directory ({input_dir}), and output directory ({output_dir})."
        )

    @classmethod
    def fingerprint_inputs(cls, filename: str = "", auto_reload: str = "on_file_change", **kwargs) -> Any:
        """Detect file modification on disk so ComfyUI automatically reloads on change."""
        if auto_reload == "always":
            return float("NaN")

        try:
            fn = filename or kwargs.get("filename", "")
            resolved = cls._resolve_filepath(fn)
            if os.path.isfile(resolved):
                mtime = os.path.getmtime(resolved)
                size = os.path.getsize(resolved)
                # For small text/prompt files (< 5MB), also hash the actual file content!
                # This guarantees immediate detection even on network drives, OneDrive, NAS, or FAT drives.
                if size < 5 * 1024 * 1024:
                    with open(resolved, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    return f"{resolved}_{mtime}_{size}_{file_hash}"
                return hashlib.sha256(f"{resolved}_{mtime}_{size}".encode()).hexdigest()
        except Exception:
            pass
        return f"loadtext_{filename}"

    @classmethod
    def IS_CHANGED(cls, filename: str = "", auto_reload: str = "on_file_change", **kwargs) -> Any:
        return cls.fingerprint_inputs(filename=filename, auto_reload=auto_reload, **kwargs)

    @classmethod
    def validate_inputs(cls, filename: str, auto_reload: str = "on_file_change", **kwargs) -> bool | str:
        try:
            cls._resolve_filepath(filename)
            return True
        except Exception as e:
            return str(e)

    @classmethod
    def execute(cls, filename: str, auto_reload: str = "on_file_change", **kwargs) -> io.NodeOutput:
        resolved_path = cls._resolve_filepath(filename)

        content = None
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "utf-16", "utf-16-le"]
        for enc in encodings:
            try:
                with open(resolved_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        line_count = len(content.splitlines())
        char_count = len(content)
        file_size_kb = os.path.getsize(resolved_path) / 1024.0

        preview_snippet = content[:300] + ("..." if len(content) > 300 else "")
        summary_text = (
            f"[Loaded Text File]\n"
            f"File: {os.path.basename(resolved_path)}\n"
            f"Path: {resolved_path}\n"
            f"Size: {file_size_kb:.2f} KB | Lines: {line_count} | Characters: {char_count}\n"
            f"Reload Mode: {auto_reload}\n"
            f"----------------------------------------\n"
            f"{preview_snippet}"
        )

        return io.NodeOutput(
            content,
            ui=PreviewText(summary_text),
        )


class MiniMaxH3LoadText(LoadText):
    """Load text contents from a local file as a string (MiniMax H3 category alias)."""

    @classmethod
    def define_schema(cls):
        schema = super().define_schema()
        return io.Schema(
            node_id="MiniMaxH3LoadText",
            display_name="Load Text (MiniMax H3)",
            category="Bus/MiniMax",
            description=schema.description,
            search_aliases=schema.search_aliases,
            inputs=schema.inputs,
            outputs=schema.outputs,
        )


H3LoadText = LoadText


_LAST_VISITED_TEXT_DIR: str | None = None
_LAST_VISITED_TEXT_CACHE_FILE: str = os.path.join(os.path.dirname(__file__), ".last_visited_text_dir")


def _get_last_visited_text_dir() -> str | None:
    """Retrieve the last visited folder from memory or persistent disk cache."""
    global _LAST_VISITED_TEXT_DIR
    if _LAST_VISITED_TEXT_DIR and os.path.isdir(_LAST_VISITED_TEXT_DIR):
        return _LAST_VISITED_TEXT_DIR

    if os.path.isfile(_LAST_VISITED_TEXT_CACHE_FILE):
        try:
            with open(_LAST_VISITED_TEXT_CACHE_FILE, "r", encoding="utf-8") as f:
                saved = f.read().strip()
                if saved and os.path.isdir(saved):
                    _LAST_VISITED_TEXT_DIR = saved
                    return saved
        except Exception:
            pass
    return None


def _set_last_visited_text_dir(dir_path: str | None) -> None:
    """Update and persist the last visited folder."""
    global _LAST_VISITED_TEXT_DIR
    if not dir_path or not os.path.isdir(dir_path):
        return
    _LAST_VISITED_TEXT_DIR = os.path.abspath(dir_path)
    try:
        with open(_LAST_VISITED_TEXT_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(_LAST_VISITED_TEXT_DIR)
    except Exception:
        pass


def _open_system_file_dialog(initial_dir: str | None = None) -> str | None:
    """Launch native OS Open File Dialog on host machine."""
    import sys
    import subprocess

    if sys.platform == "win32":
        try:
            ps_script = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                "$d = New-Object System.Windows.Forms.OpenFileDialog; "
                "$d.Filter = 'Text and Prompt Files (*.txt;*.md;*.json;*.prompt;*.yaml;*.yml;*.csv)|*.txt;*.md;*.json;*.prompt;*.yaml;*.yml;*.csv|All Files (*.*)|*.*'; "
                "$d.Title = 'Select Text or Prompt File'; "
            )
            if initial_dir and os.path.isdir(initial_dir):
                clean_dir = os.path.normpath(initial_dir).replace("'", "''")
                ps_script += f"$d.InitialDirectory = '{clean_dir}'; "
            ps_script += "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.FileName }"
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            chosen = res.stdout.strip()
            if chosen and os.path.isfile(chosen):
                return chosen
        except Exception:
            pass

    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askopenfilename(
            title="Select Text or Prompt File",
            initialdir=initial_dir,
            filetypes=[
                ("Text and Prompt Files", "*.txt;*.md;*.json;*.prompt;*.yaml;*.yml;*.csv"),
                ("All Files", "*.*"),
            ],
        )
        root.destroy()
        if chosen and os.path.isfile(chosen):
            return chosen
    except Exception:
        pass

    return None


# Register server endpoints
try:
    from server import PromptServer
    from aiohttp import web
    import asyncio

    if hasattr(PromptServer, "instance") and PromptServer.instance and hasattr(PromptServer.instance, "routes"):
        @PromptServer.instance.routes.post("/h3/open_file_dialog")
        async def open_file_dialog_endpoint(request):
            """Opens native host file dialog on the last visited folder (or default to current file's folder) and returns full filesystem path without uploading."""
            try:
                body = await request.json()
            except Exception:
                body = {}

            client_last_dir = body.get("last_visited_dir", "")
            current_path = body.get("current_path", "")

            # 1. Primary priority: Open on the last visited folder
            initial_dir = None
            if client_last_dir and os.path.isdir(client_last_dir):
                initial_dir = os.path.abspath(client_last_dir)
                _set_last_visited_text_dir(initial_dir)
            else:
                last_saved = _get_last_visited_text_dir()
                if last_saved and os.path.isdir(last_saved):
                    initial_dir = last_saved

            # 2. Secondary fallback (default): If no folder was previously visited, use currently selected file's folder
            if not initial_dir and current_path:
                clean = LoadText._clean_path(current_path)
                try:
                    resolved = LoadText._resolve_filepath(clean)
                    if os.path.exists(resolved):
                        initial_dir = os.path.dirname(resolved) if os.path.isfile(resolved) else resolved
                except Exception:
                    if os.path.exists(clean):
                        initial_dir = os.path.dirname(clean) if os.path.isfile(clean) else clean

            loop = asyncio.get_running_loop()
            chosen = await loop.run_in_executor(None, _open_system_file_dialog, initial_dir)

            if chosen and os.path.isfile(chosen):
                chosen_dir = os.path.dirname(os.path.abspath(chosen))
                _set_last_visited_text_dir(chosen_dir)
                size_kb = round(os.path.getsize(chosen) / 1024.0, 1)
                return web.json_response({
                    "path": os.path.abspath(chosen),
                    "filename": os.path.basename(chosen),
                    "size_kb": size_kb,
                    "last_visited_dir": chosen_dir,
                    "canceled": False,
                })

            return web.json_response({
                "canceled": True,
                "path": "",
                "last_visited_dir": _get_last_visited_text_dir() or initial_dir or "",
            })

except Exception:
    pass


