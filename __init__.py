from comfy_api.latest import ComfyExtension
from .nodes import (
    MiniMaxH3CreateReferenceBus,
    MiniMaxH3ExpandReferenceBus,
    MiniMaxH3CreateVideoSettingsBus,
    MiniMaxH3ExpandVideoSettingsBus,
    MiniMaxH3ModelFromBus,
    MiniMaxH3ClipFromBus,
    MiniMaxH3VideoVaeFromBus,
    MiniMaxH3AudioVaeFromBus,
    MiniMaxH3VAEsFromBus,
    MiniMaxH3ResolutionFromBus,
    MiniMaxH3WidthFromBus,
    MiniMaxH3HeightFromBus,
    MiniMaxH3StepsFromBus,
    GetStepsFromBus,
    MiniMaxH3SaveNestedLatent,
    MiniMaxH3LoadNestedLatent,
    MiniMaxH3ConcatAVLatent,
    MiniMaxH3SaveAVLatent,
    MiniMaxH3LoadAVLatent,
    MiniMaxH3ConcatAVLatents,
)

WEB_DIRECTORY = "web"


class H3ReferenceBusExtension(ComfyExtension):
    """ComfyUI extension registering MiniMax H3 reference, settings, extractor, and latent bus nodes."""

    async def get_node_list(self):
        return [
            MiniMaxH3CreateReferenceBus,
            MiniMaxH3ExpandReferenceBus,
            MiniMaxH3CreateVideoSettingsBus,
            MiniMaxH3ExpandVideoSettingsBus,
            MiniMaxH3ModelFromBus,
            MiniMaxH3ClipFromBus,
            MiniMaxH3VideoVaeFromBus,
            MiniMaxH3AudioVaeFromBus,
            MiniMaxH3VAEsFromBus,
            MiniMaxH3ResolutionFromBus,
            MiniMaxH3WidthFromBus,
            MiniMaxH3HeightFromBus,
            MiniMaxH3StepsFromBus,
            GetStepsFromBus,
            MiniMaxH3SaveNestedLatent,
            MiniMaxH3LoadNestedLatent,
            MiniMaxH3ConcatAVLatent,
        ]


async def comfy_entrypoint() -> H3ReferenceBusExtension:
    return H3ReferenceBusExtension()


__all__ = [
    "comfy_entrypoint",
    "MiniMaxH3CreateReferenceBus",
    "MiniMaxH3ExpandReferenceBus",
    "MiniMaxH3CreateVideoSettingsBus",
    "MiniMaxH3ExpandVideoSettingsBus",
    "MiniMaxH3ModelFromBus",
    "MiniMaxH3ClipFromBus",
    "MiniMaxH3VideoVaeFromBus",
    "MiniMaxH3AudioVaeFromBus",
    "MiniMaxH3VAEsFromBus",
    "MiniMaxH3ResolutionFromBus",
    "MiniMaxH3WidthFromBus",
    "MiniMaxH3HeightFromBus",
    "MiniMaxH3StepsFromBus",
    "GetStepsFromBus",
    "MiniMaxH3SaveNestedLatent",
    "MiniMaxH3LoadNestedLatent",
    "MiniMaxH3ConcatAVLatent",
    "MiniMaxH3SaveAVLatent",
    "MiniMaxH3LoadAVLatent",
    "MiniMaxH3ConcatAVLatents",
    "WEB_DIRECTORY",
]



