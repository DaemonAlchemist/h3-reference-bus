# MiniMax H3 Reference Bus for ComfyUI

A pair of ComfyUI bus nodes for handling **MiniMax H3 multimodal references** (reference images, video frames, video soundtracks, and standalone audio) in Reference-to-Video (`Ref2VA`) workflows.

## Overview

In MiniMax H3 reference-driven workflows, models accept multimodal references in a specific order:
- **Up to 9 Reference Images**: Referenced in prompts as `<Picture 1>` through `<Picture 9>`.
- **Up to 3 Reference Videos**: Referenced in prompts as `<Video 1>` through `<Video 3>`.
- **Up to 3 Reference Video Soundtracks**: Soundtracks paired by index to the corresponding reference video.
- **Up to 3 Standalone Audios**: Referenced in prompts as `<Audio 1>` through `<Audio 3>`.

Connecting all of these individual sockets across large workflows or subgraphs introduces significant clutter (up to 18 wires). These nodes solve that problem by bundling all references into a single `H3_REF_BUS` wire and expanding them right at the destination.

---

## Nodes Included

### Reference Bus Pair (`H3_REF_BUS`)

#### 1. Create MiniMax H3 Reference Bus (`MiniMaxH3CreateReferenceBus`)
- **Category**: `Bus/MiniMax`
- **Inputs**:
  - `bus_behavior` *(Combo: `append` vs `overwrite`, default `append`)*: Automatically increments reference indices when an incoming bus is connected.
  - `bus` *(Optional `H3_REF_BUS`)*: Connect an existing reference bus to extend or override references.
  - `ref_images` *(Autogrow, up to 9 `IMAGE` inputs)*: Reference images for `<Picture 1>` to `<Picture 9>`.
  - `ref_videos` *(Autogrow, up to 3 `IMAGE` inputs)*: 24 fps video frames for `<Video 1>` to `<Video 3>`.
  - `ref_video_audios` *(Autogrow, up to 3 `AUDIO` inputs)*: Soundtracks corresponding to reference videos.
  - `ref_audios` *(Autogrow, up to 3 `AUDIO` inputs)*: Standalone audio references for `<Audio 1>` to `<Audio 3>`.
- **Output**:
  - `bus` (`H3_REF_BUS`): Bundled multimodal reference bus.

#### 2. Expand MiniMax H3 Reference Bus (`MiniMaxH3ExpandReferenceBus`)
- **Category**: `Bus/MiniMax`
- **Input**:
  - `bus` (`H3_REF_BUS`): Single incoming reference bus.
- **Outputs** (18 distinct sockets):
  - `ref_image_1 (<Picture 1>)` .. `ref_image_9 (<Picture 9>)` (`IMAGE`)
  - `ref_video_1 (<Video 1>)` .. `ref_video_3 (<Video 3>)` (`IMAGE`)
  - `ref_video_audio_1 (<Video 1 Soundtrack>)` .. `ref_video_audio_3 (<Video 3 Soundtrack>)` (`AUDIO`)
  - `ref_audio_1 (<Audio 1>)` .. `ref_audio_3 (<Audio 3>)` (`AUDIO`)

---

### Video Settings Bus Pair (`H3_VIDEO_SETTINGS_BUS`)

#### 3. Create MiniMax H3 Video Settings Bus (`MiniMaxH3CreateVideoSettingsBus`)
- **Category**: `Bus/MiniMax`
- **Inputs**:
  - `bus` *(Optional `H3_VIDEO_SETTINGS_BUS`)*: Optional incoming settings bus to extend or override.
  - `model` *(Optional `MODEL`)*: Diffusion UNet/DiT model.
  - `clip` *(Optional `CLIP`)*: MiniMax text encoder / CLIP model.
  - `vae` *(Optional `VAE`)*: Video VAE.
  - `audio_vae` *(Optional `VAE`)*: Audio VAE for synchronized stereo sound.
  - `width` *(INT, default 1344, step 32)*: Target video width.
  - `height` *(INT, default 768, step 32)*: Target video height.
- **Output**:
  - `bus` (`H3_VIDEO_SETTINGS_BUS`): Bundled video settings bus.

#### 4. Expand MiniMax H3 Video Settings Bus (`MiniMaxH3ExpandVideoSettingsBus`)
- **Category**: `Bus/MiniMax`
- **Input**:
  - `bus` (`H3_VIDEO_SETTINGS_BUS`): Single incoming video settings bus.
- **Outputs**:
  - `model` (`MODEL`): Unpacked model for KSampler / MiniMax Sampler.
  - `clip` (`CLIP`): Text encoder for conditioning nodes.
  - `video_vae` (`VAE`): Video VAE for conditioning / decode.
  - `audio_vae` (`VAE`): Audio VAE for conditioning / decode.
  - `width` (`INT`): Output width.
  - `height` (`INT`): Output height.

---

### Global Settings Extractor Nodes

When you only need a single setting or resolution pair somewhere in your workflow, use these compact extractor nodes instead of expanding the entire bus:

| Node | Node ID | Output | Description |
|---|---|---|---|
| **Model from Bus** | `MiniMaxH3ModelFromBus` | `MODEL` | Extracts the diffusion model for samplers. |
| **CLIP from Bus** | `MiniMaxH3ClipFromBus` | `CLIP` | Extracts the text encoder for conditioning/prompts. |
| **Video VAE from Bus** | `MiniMaxH3VideoVaeFromBus` | `VAE` | Extracts the Video VAE for encoding/decoding frames. |
| **Audio VAE from Bus** | `MiniMaxH3AudioVaeFromBus` | `VAE` | Extracts the Audio VAE for synchronized audio decoding. |
| **VAEs from Bus** | `MiniMaxH3VAEsFromBus` | `video_vae`, `audio_vae` (`VAE`, `VAE`) | Extracts both Video VAE and Audio VAE together (ideal for decode). |
| **Resolution from Bus** | `MiniMaxH3ResolutionFromBus` | `width`, `height` (`INT`, `INT`) | Extracts both width and height integers. |
| **Width from Bus** | `MiniMaxH3WidthFromBus` | `width` (`INT`) | Extracts only the width integer. |
| **Height from Bus** | `MiniMaxH3HeightFromBus` | `height` (`INT`) | Extracts only the height integer. |

All extractors accept `H3_VIDEO_SETTINGS_BUS` as input and safely return `None` if the specific setting was not connected to the upstream bus.

---

## Bus Chaining: Adding & Overriding References

The `Create MiniMax H3 Reference Bus` node includes a **`bus_behavior`** control (`append` vs `overwrite`) alongside the optional `bus` input, making multi-stage workflows intuitive.

### 1. `bus_behavior = "append"` (Default & Recommended)
- **Automatic Index Incrementing**: If an incoming bus already has attached references (e.g. 2 images: `ref_image_0` and `ref_image_1`), new inputs connected to this node automatically increment from the existing count.
  - The first image on the second node is assigned index `2` (`<Picture 3>`).
  - The second image is assigned index `3` (`<Picture 4>`), up to the MiniMax H3 limit of 9 images.
- **Soundtrack Auto-Pairing**: If you attach a reference video and a soundtrack to the second node, both are incremented together (e.g. to `ref_video_1` and `ref_video_audio_1`), ensuring the soundtrack remains bound to the correct video clip.
- **Model Limit Protection**: If chained nodes attempt to exceed MiniMax H3 limits (9 images, 3 videos, 3 standalone audios), execution raises a clear `ValueError` detailing the count.

### 2. `bus_behavior = "overwrite"`
- Direct slot-level replacement: References connected to this node replace existing items at the identical socket index (e.g. `ref_image_0` overrides `ref_image_0`).
- Unconnected slots on the current node continue to pass through their upstream references untouched.

### Visual Status & Feedback

1. **On-Canvas Status Indicator**:
   - The included web extension dynamically inspects the upstream graph in real time as wires are connected or disconnected.
   - The node displays an active status line directly on the canvas:
     `Incoming Bus: 2 img (<Picture 1..2>), 0 vid, 0 aud`
2. **Execution Summary**:
   - When the graph executes, the node displays a breakdown on the canvas:
     ```
     [H3 Reference Bus]
     Mode: append
     Incoming: 2 img, 0 vid, 0 aud
     Added: +1 img, +0 vid, +0 aud
     Total Bus: 3 img (<Picture 1..3>), 0 vid, 0 aud
     ```

### Practical Use Cases

- **Base Character + Per-Shot References**: Connect base character turnarounds (`ref_image_0`, `ref_image_1`) in the root bus node, then pass that bus to shot-specific nodes. With `bus_behavior = "append"`, adding a shot-specific prop or outfit image automatically becomes `<Picture 3>` without having to manually manage indices.
- **Variant Overriding**: Switch `bus_behavior = "overwrite"` on a branched node to swap out `<Picture 1>` for a different character while preserving all background video and audio references.

---

## Workflow Example: Complete Ref2VA Pipeline

With both buses in place, your entire pipeline is routed using just **two wires**:

```
[Load Model] -------> model
[Load CLIP] --------> clip
[Load Video VAE] ---> vae          -> [ Create Video Settings Bus ]
[Load Audio VAE] ---> audio_vae                   |
[Width: 1344]                                     |
[Height: 768]                                     v (single H3_VIDEO_SETTINGS_BUS wire)
                                      [ Expand Video Settings Bus ]
                                      |   |       |       |       |       |
                 +--------------------+   |       |       |       |       +----+
                 | model                  | clip  | vae   | avae  | width      | height
                 v                        v       v       v       v            v
           [ KSampler ] <=========== [ MiniMax H3 Reference to Video ]
                                                  ^   ^   ^
                                                  |   |   |
                                                  |   |   +--- ref_audio_1
                                                  |   +------- ref_video_1
                                                  +----------- ref_image_1
                                                              |
                                              [ Expand Reference Bus ]
                                                              ^
                                                              | (single H3_REF_BUS wire)
                                              [ Create Reference Bus ]
                                               ^   ^   ^   ^
                                               |   |   |   |
[Load Images (1..9)] --------------------------+   |   |   |
[Load Video (frames)] -----------------------------+   |   |
[Load Video Soundtrack] -------------------------------+   |
[Load Standalone Audio (1..3)] ----------------------------+
```

Unconnected reference sockets safely pass as `None`, which `MiniMaxH3ReferenceToVideo` natively ignores during execution.

