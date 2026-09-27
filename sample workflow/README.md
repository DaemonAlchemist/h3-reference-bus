# Sample Multi-Prompt Scene: The Star-Berry Pie (Rated G)

This directory contains a complete, 5-shot sample sequence and associated reference assets designed for the **MiniMax Hailuo H3 Reference Bus** workflow and the `LoadText` node.

---

## 🎨 Reference Images & Voice Audio

| Reference Key | Filename | Description | Role / Subject |
| :--- | :--- | :--- | :--- |
| `<Picture 1>` | `reference_01_barnaby_baker.jpg` | Barnaby the Bear Cub Apprentice Baker | `<Subject 1>` (Main Character) |
| `<Picture 2>` | `reference_02_pip_hummingbird.jpg` | Pip the Magical Hummingbird Finch | `<Subject 2>` (Companion) |
| `<Picture 3>` | `reference_03_botanical_kitchen.jpg` | Sunlit Botanical Greenhouse Bakery | `<Subject 3>` (Environment / Setting) |
| `<Audio 1>` | `Barnaby.flac` | Barnaby's gentle, youthful bear apprentice voice | Voice reference for `<Subject 1>` |
| `<Audio 2>` | `Pip.flac` | Pip's chirpy, musical animated critter voice | Voice reference for `<Subject 2>` |

---

## ⏱️ Timing Notes & Shot Breakdown

Each prompt is paced for a standard **10-to-11-second multi-shot generation block**, utilizing an internal cut marker at approximately the halfway point (~5.2s – 5.5s). When chained together, the 5 prompts produce a continuous **~54–55 second** cinematic narrative sequence.

### Timing Overview Table

| Prompt | Cut Marker | Shot 1 Length | Shot 2 Length | Total Prompt Length | Cumulative Scene Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Prompt 01**: *The Flour and the Flutter* | `00:05.500` | 5.5s | 5.0s – 5.5s | **~10.5s – 11.0s** | `00:00.0` – `00:11.0` |
| **Prompt 02**: *The Baking Montage* | `00:05.500` | 5.5s | 5.0s – 5.5s | **~10.5s – 11.0s** | `00:11.0` – `00:22.0` |
| **Prompt 03**: *The Missing Star-Berry* | `00:05.200` | 5.2s | 5.3s – 5.8s | **~10.5s – 11.0s** | `00:22.0` – `00:33.0` |
| **Prompt 04**: *The Stool and the Reach* | `00:05.500` | 5.5s | 5.0s – 5.5s | **~10.5s – 11.0s** | `00:33.0` – `00:44.0` |
| **Prompt 05**: *The Star-Berry Masterpiece*| `00:05.400` | 5.4s | 5.1s – 5.6s | **~10.5s – 11.0s** | `00:44.0` – `00:55.0` |
| **Total 5-Prompt Sequence** | — | — | — | **5 Prompts** | **~55.0 seconds** |

---

### Detailed Shot Breakdown

#### Prompt 01: *The Flour and the Flutter* (Total: ~10.5s – 11.0s)
* **[Shot 1] Establishing Track** (`00:00.000 – 00:05.500` \| **Duration: 5.5s**):
  - *Action*: Wide tracking shot from the south entrance gliding north across terracotta floor tiles toward the central oak table. Barnaby rolls sweet dough facing the open window.
* **[Shot 2] Reverse Medium Two-Shot** (`00:05.500 – 00:11.000` \| **Duration: ~5.5s**):
  - *Action*: Reverse 180° cut looking south. Barnaby rests the rolling pin and dusts his apron; Pip swoops in through the north window and hovers by his right shoulder.
  - *Dialogue*: Barnaby speaks (`~3.0s`), followed by Pip's welcoming two-tone chirp and bob.

#### Prompt 02: *The Baking Montage* (Total: ~10.5s – 11.0s)
* **[Shot 1] Filling & Spices** (`00:00.000 – 00:05.500` \| **Duration: 5.5s**):
  - *Action*: Lively medium shot at the center table. Barnaby swirls sweet spiced berry compote into the crust; Pip drops a cinnamon stick and fans a cloud of nutmeg and sparkling sugar crystals through the sunbeams.
* **[Shot 2] Lattice Weaving & Scallop Crimp** (`00:05.500 – 00:11.000` \| **Duration: ~5.5s**):
  - *Action*: Dynamic 45° close-up. Barnaby rolls pastry ribbons, weaves an intricate diagonal lattice with an open center ring, and crimps the crust with a fork while Pip taps his claws in tempo on the flour canister.
  - *Dialogue*: Barnaby's proud remark (`~2.5s`), followed by Pip's excited whistle and melodic trill.

#### Prompt 03: *The Missing Star-Berry* (Total: ~10.5s – 11.0s)
* **[Shot 1] Medium Close-up** (`00:00.000 – 00:05.200` \| **Duration: 5.2s**):
  - *Action*: Continuing after the montage, Barnaby at the center table admires the newly crimped lattice, searches empty dishes for the centerpiece fruit, and scratches behind his ear in puzzle.
  - *Dialogue*: Barnaby mutters his search line (`~3.2s`).
* **[Shot 2] Ascending Tilt & Track** (`00:05.200 – 00:10.8s` \| **Duration: ~5.6s**):
  - *Action*: Pip zips from Barnaby's shoulder up and west to the top shelf above the copper rack, hovering beside the porcelain dish with the glowing star-berry.
  - *Dialogue*: Pip calls out stage-directed chirp, spoken line (`~1.8s`), and happy trill.

#### Prompt 04: *The Stool and the Reach* (Total: ~10.5s – 11.0s)
* **[Shot 1] Low-Angle Walk & Step** (`00:00.000 – 00:05.500` \| **Duration: 5.5s**):
  - *Action*: Barnaby walks from the center table to the west wall, slides the round oak stool into place, and steps up to full height.
* **[Shot 2] Eye-Level Shelf Close-up** (`00:05.500 – 00:11.000` \| **Duration: ~5.5s**):
  - *Action*: Barnaby's paw enters from below to cradle the glowing fruit. Pip hovers close, fluttering a draft that blows flour off Barnaby's nose.
  - *Dialogue*: Barnaby's tickled chuckle and whisper (`~2.5s`), with Pip's soft encouraging cheep.

#### Prompt 05: *The Star-Berry Masterpiece* (Total: ~10.5s – 11.0s)
* **[Shot 1] Top-Down Placement** (`00:00.000 – 00:05.400` \| **Duration: 5.4s**):
  - *Action*: 45° close-up over the central prep table. Barnaby lowers the glowing star-berry into the lattice center; an amber ripple and fragrant vanilla stardust sparkle outward.
* **[Shot 2] Medium Two-Shot Pull-back** (`00:05.400 – 00:11.000` \| **Duration: ~5.6s**):
  - *Action*: Barnaby steps back with paws on hips. Pip glides down and perches atop his baker's cap.
  - *Dialogue*: Pip's proud warble and line (`~2.0s`), followed by Barnaby's cheerful response (`~2.2s`) as morning sunbeams bathe the kitchen.

---

### 💡 Generation & Pacing Tips
1. **Target Generation Duration**:
   - Set your video generation duration to **10s** or **11s** per prompt to allow both shots adequate screen time for dialogue and physical staging.
   - For **6-second** generation models, scale the cut marker to `00:03.000` (Shot 1: 3.0s, Shot 2: 3.0s).
2. **Audio / Speech Synchronization**:
   - Each shot provides a 1.5–2.0 second visual lead-in before dialogue begins, preventing cut clipping and allowing natural mouth-shape synchronization.
3. **Sequential Stitching**:
   - The end frame of each prompt's `[Shot 2]` directly matches the spatial staging, character postures, and camera line of the next prompt's `[Shot 1]`, enabling clean hard cuts or 0.3s soft cross-fades in an editor.

---

## 📝 Sequence Prompts (YAML / Structured Format)

1. **[`Prompt 01 - The Flour and the Flutter.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow/Prompt%2001%20-%20The%20Flour%20and%20the%20Flutter.txt)**
2. **[`Prompt 02 - The Baking Montage.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow/Prompt%2002%20-%20The%20Baking%20Montage.txt)**
3. **[`Prompt 03 - The Missing Star-Berry.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow/Prompt%2003%20-%20The%20Missing%20Star-Berry.txt)**
4. **[`Prompt 04 - The Stool and the Reach.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow/Prompt%2004%20-%20The%20Stool%20and%20the%20Reach.txt)**
5. **[`Prompt 05 - The Star-Berry Masterpiece.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow/Prompt%2005%20-%20The%20Star-Berry%20Masterpiece.txt)**

---

## 🚀 Recommended ComfyUI Setup

1. **Reference Bus**:
   - Connect `reference_01_barnaby_baker.jpg` to `ref_image_0` (`<Picture 1>`).
   - Connect `reference_02_pip_hummingbird.jpg` to `ref_image_1` (`<Picture 2>`).
   - Connect `reference_03_botanical_kitchen.jpg` to `ref_image_2` (`<Picture 3>`).
   - Connect `Barnaby.flac` to audio input (`<Audio 1>`).
   - Connect `Pip.flac` to audio input (`<Audio 2>`).
2. **Prompt Loader (`LoadText`)**:
   - Point your `LoadText` node to any of the 5 prompt `.txt` files in this directory.
   - Keep `auto_reload` set to `on_file_change` so that editing prompts in your external editor updates generations automatically!
