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
  - `steps` *(INT, default 20, min 1, max 10000)*: Sampling steps.
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
  - `steps` (`INT`): Sampling steps.

---

### Global Settings Extractor Nodes

When you only need a single setting, steps count, or resolution pair somewhere in your workflow, use these compact extractor nodes instead of expanding the entire bus:

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
| **Steps from Bus / Get Steps from Bus** | `MiniMaxH3StepsFromBus` / `GetStepsFromBus` | `steps` (`INT`) | Extracts the sampling steps integer. |

All extractors accept `H3_VIDEO_SETTINGS_BUS` as input and safely return fallback defaults if the specific setting was not connected to the upstream bus.

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

---

## Long Video Creation in Parts: MiniMax H3 NestedTensor Save & Load

When creating long videos (15s, 30s, 60s+) with MiniMax H3, generating the entire duration in a single pass can cause VRAM exhaustion or degradation. The standard technique is to generate videos in sequential parts (e.g. Part 1, Part 2, Part 3) using continuation guides.

### Why Standard Latent Nodes Fail

MiniMax H3 is an omnimodal model that generates video latents (`5D: [B, 24, T, H/16, W/16]`) and synchronized stereo audio latents (`4D: [B, 32, 2, T_audio]`) jointly inside ComfyUI's custom **`NestedTensor`** wrapper (`comfy.nested_tensor.NestedTensor`).

- Standard ComfyUI `SaveLatent` calls `.contiguous()` directly on the latent tensor, which immediately throws `AttributeError: 'NestedTensor' object has no attribute 'contiguous'` and crashes the workflow.
- Standard `LoadLatent` only loads a single `latent_tensor` from `input/`, ignoring audio streams and failing to reconstruct the `NestedTensor` required by MiniMax samplers, continuation nodes, and decoders.

The following nodes solve this by natively saving, loading, and concatenating MiniMax H3's `NestedTensor` format without errors:

### 1. Save MiniMax H3 AV Latent (`MiniMaxH3SaveNestedLatent`)
- **Category**: `Bus/MiniMax/Latent`
- **Search Aliases**: `Save MiniMax H3 AV Latent`, `Save Nested Tensor`, `Save Video Part`
- **Inputs**:
  - `samples` (`LATENT`): The incoming MiniMax H3 joint AV latent (`NestedTensor`).
  - `filename_prefix` (`STRING`, default `latents/h3_part`): Output path and subfolder. Supports ComfyUI formatting tokens like `%date:yyyy-MM-dd%`.
  - `part_number` (`INT`, default `1`, min `0`): Part number for this video segment (e.g. `1` for Part 1). When `> 0`, automatically appends `_part_01` to the filename.
  - `append_counter` (`BOOLEAN`, default `True`): Appends sequential counter (`_00001_`) to prevent accidental overwrites.
  - `save_output` (`BOOLEAN`, default `True`): When `False`, acts as a pass-through without writing to disk.
- **Output**:
  - `samples` (`LATENT`): Pass-through of the input latent for downstream VAE decoding or continuation.
- **Features**:
  - Unbinds and serializes both video and audio streams into standard `.latent` safetensors files without memory-sharing conflicts.
  - Stores part numbering, frame count, audio sample length, resolution, and generation prompt in file metadata.
  - Displays real-time on-canvas summary: filename, folder, part number, frame count, duration, resolution, audio status, and file size in MB.

### 2. Load MiniMax H3 AV Latent (`MiniMaxH3LoadNestedLatent`)
- **Category**: `Bus/MiniMax/Latent`
- **Search Aliases**: `Load MiniMax H3 AV Latent`, `Load Nested Tensor`, `Load Video Part`
- **Inputs**:
  - `latent_file` (`Combo`): Dropdown listing all available `.latent` and `.safetensors` files from **both** `output/` and `input/` directories (no need to manually move files from output to input!).
  - `custom_path` (`STRING`, optional): Optional manual path override. Supports absolute paths or paths relative to `output/` or `input/`.
- **Outputs**:
  - `samples` (`LATENT`): Fully reconstructed native `NestedTensor((video, audio))` ready for KSampler, continuation nodes, or VAE decoders.
  - `video_latent` (`LATENT`): Video stream alone wrapped as standard ComfyUI latent (ideal for video upscalers or isolated video decoding).
  - `audio_latent` (`LATENT`): Audio stream alone wrapped as latent (ideal for `VAEDecodeAudio`).
  - `frame_count` (`INT`): Total pixel frames represented at 24 fps (e.g. `124`).
  - `part_number` (`INT`): Part number extracted from metadata or filename.
  - `width` (`INT`): Video width in pixels (e.g. `1344`).
  - `height` (`INT`): Video height in pixels (e.g. `768`).
  - `duration` (`FLOAT`): Duration in seconds at 24 fps.

### 3. Concat MiniMax H3 AV Latents (`MiniMaxH3ConcatAVLatent`)
- **Category**: `Bus/MiniMax/Latent`
- **Search Aliases**: `Concat MiniMax H3 Latents`, `Stitch Video Parts`, `Join H3 Latents`
- **Inputs**:
  - `latent_a` (`LATENT`): First MiniMax H3 AV latent (Part N).
  - `latent_b` (`LATENT`): Second MiniMax H3 AV latent (Part N+1).
  - `latent_c` (`LATENT`, optional): Third MiniMax H3 AV latent (Part N+2).
  - `trim_overlap_tokens` (`INT`, default `0`): Video tokens to trim from subsequent parts to eliminate continuation overlaps (5 video tokens = 17 frames = 28 audio tokens).
- **Outputs**:
  - `samples` (`LATENT`): Combined multi-part `NestedTensor` with perfectly synchronized video and audio timelines.
  - `video_latent` (`LATENT`): Stitched video stream alone.
  - `audio_latent` (`LATENT`): Stitched audio stream alone.
  - `total_frame_count` (`INT`): Cumulative frame count of all concatenated parts.
  - `duration` (`FLOAT`): Cumulative duration in seconds.

---

### Text Loader Node (`LoadText`)

#### Load Text (`LoadText` / `MiniMaxH3LoadText`)
- **Category**: `text` (also accessible under `Bus/MiniMax`)
- **Search Aliases**: `Load Text`, `Read Text`, `Text File`, `Load Prompt`, `Open File`, `Text Loader`, `Load Markdown`
- **Inputs**:
  - `filename` (`STRING`): Path or filename of the text/markdown/prompt file to load.
  - `auto_reload` (`COMBO`, options: `["on_file_change", "always"]`, default: `on_file_change`):
    - `on_file_change`: Automatically detects edits by checking the file's modification time, size, and SHA256 content hash on disk.
    - `always`: Forces re-reading the file from disk on every queue execution, unconditionally bypassing cache.
  - **`Choose File...` Button**: Direct button widget on the node that triggers the native OS file open dialog to browse and choose any file directly from disk.
- **Output**:
  - `STRING`: The full text contents of the chosen file as a string, ready to connect directly to CLIP Text Encoders, prompt constructors, or any downstream text input.
- **Key Features**:
  - **Native File Dialog**: Click the "Choose File..." button to open the OS file chooser and populate the exact file path without tedious manual typing.
  - **ComfyUI Desktop / Electron Native Path**: In ComfyUI Desktop, leverages `window.api.getPathForFile` to capture the true absolute OS path (e.g. `O:\Skylands\...\Seq 01 Prompt 01.txt`) directly from the OS—never creating an uploaded, detached copy.
  - **System Dialog for Web Clients**: If opened through a browser on localhost without Electron, invokes the host OS native Open File dialog via the backend server.
  - **Drag and Drop**: Drag and drop any `.txt`, `.md`, `.json`, `.yaml`, or `.prompt` file directly onto the node from your desktop or file manager to immediately set its full local path.
  - **Robust Auto-Updates**: In addition to filesystem timestamps, computes a SHA256 content hash on small text/prompt files (< 5MB). Changes are immediately recognized even across network shares, mapped drives (e.g. `O:\`), NAS, or cloud-synced folders where filesystem timestamps might lag.
  - **Multi-Encoding Support**: Transparently reads UTF-8 (with or without BOM), CP1252/Windows-1252, Latin-1, and UTF-16.
  - **Path Cleaning**: Automatically strips leading/trailing quotes when copying paths from Windows File Explorer (`"C:\path\to\file.md"`).

---

## Multi-Part Long Video Workflow Example

```
=== PASS 1: Generate & Save Part 1 ===
[ Prompt 1 ] -----------------------> [ MiniMax H3 Image to Video ]
                                                  |
                                                  v (samples: NestedTensor)
                                    [ Save MiniMax H3 AV Latent ] (part_number: 1)
                                                  |
                                                  +---> [ VAE Decode Video ] -> [ Save Image/Video ]
                                                  +---> [ VAE Decode Audio ] -> [ Save Audio ]

=== PASS 2: Continue from Part 1 ===
[ Load MiniMax H3 AV Latent ] (part 1)
      |
      +---> samples ------------> [ MiniMax H3 Latent Tail Guide ]
      +---> frame_count           [ MiniMax H3 Guided Continuation Window ]
                                                  |
[ Prompt 2 ] -----------------------> [ Sampler ]
                                            |
                                            v (samples: Part 2 extension)
                                    [ Save MiniMax H3 AV Latent ] (part_number: 2)

=== FINAL PASS: Stitch Parts & Decode Master Video ===
[ Load Part 1 ] ------------------------> latent_a -> [ Concat MiniMax H3 AV Latents ]
[ Load Part 2 ] ------------------------> latent_b                  |
[ Load Part 3 ] ------------------------> latent_c                  v (samples: Complete Video)
                                                            +-------> [ VAE Decode Video ] -> [ Save Full Video ]
                                                            +-------> [ VAE Decode Audio ] -> [ Save Full Soundtrack ]
```


