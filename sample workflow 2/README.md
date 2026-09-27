# Sample Multi-Prompt Scene: Project Eclipse — The Rooftop Protocol (Rated PG-13)

This directory contains a complete, 5-shot cyberpunk anime action sample sequence and associated reference assets designed for the **MiniMax Hailuo H3 Reference Bus** workflow and the `LoadText` node.

---

## 🎨 Reference Images & Voice Audio

| Reference Key | Filename | Description | Role / Subject |
| :--- | :--- | :--- | :--- |
| `<Picture 1>` | `reference_01_ren_shinobi.jpg` | Ren Kurogane — Cyberpunk Shinobi Mercenary | `<Subject 1>` (Lead Character) |
| `<Picture 2>` | `reference_02_aoi_netrunner.jpg` | Aoi Vance — Netrunner Vanguard Specialist | `<Subject 2>` (Companion / Hacker) |
| `<Picture 3>` | `reference_03_neo_shinjuku_rooftop.jpg` | Neo-Shinjuku Skyscraper Helipad in Midnight Rain | `<Subject 3>` (Environment / Setting) |
| `<Audio 1>` | `Ren.flac` | Ren's stoic, focused baritone-tenor mercenary voice | Voice reference for `<Subject 1>` |
| `<Audio 2>` | `Aoi.flac` | Aoi's energetic, sharp, charismatic netrunner voice | Voice reference for `<Subject 2>` |

---

## ⏱️ Timing Notes & Shot Breakdown

Each prompt is paced for a standard **10-to-11-second multi-shot generation block**, utilizing an internal cut marker at approximately the halfway point (~5.3s – 5.5s). When chained together through continuation windows, the 5 prompts produce a continuous **~54–55 second** cinematic anime sequence.

### Timing Overview Table

| Prompt | Cut Marker | Shot 1 Length | Shot 2 Length | Total Prompt Length | Cumulative Scene Time |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Prompt 01**: *The Rainy Infiltration* | `00:05.400` | 5.4s | 5.1s – 5.6s | **~10.5s – 11.0s** | `00:00.0` – `00:11.0` |
| **Prompt 02**: *The Drone Ambush and Deflection* | `00:05.500` | 5.5s | 5.0s – 5.5s | **~10.5s – 11.0s** | `00:11.0` – `00:22.0` |
| **Prompt 03**: *The EMP Overload* | `00:05.300` | 5.3s | 5.2s – 5.7s | **~10.5s – 11.0s** | `00:22.0` – `00:33.0` |
| **Prompt 04**: *The Rooftop Dash* | `00:05.500` | 5.5s | 5.0s – 5.5s | **~10.5s – 11.0s** | `00:33.0` – `00:44.0` |
| **Prompt 05**: *The Sky Extraction* | `00:05.400` | 5.4s | 5.1s – 5.6s | **~10.5s – 11.0s** | `00:44.0` – `00:55.0` |
| **Total 5-Prompt Sequence** | — | — | — | **5 Prompts** | **~55.0 seconds** |

---

### Detailed Shot Breakdown

#### Prompt 01: *The Rainy Infiltration* (Total: ~10.5s – 11.0s)
* **[Shot 1] Establishing Track** (`00:00.000 – 00:05.400` \| **Duration: 5.4s**):
  - *Action*: Wide tracking shot gliding south across the rain-slicked carbon tarmac of the skyscraper helipad. Ren kneels at the central landing circle, rain dripping from his silver hair, surveying the stormy neon metropolis.
* **[Shot 2] Reverse Medium Two-Shot** (`00:05.400 – 00:11.000` \| **Duration: ~5.6s**):
  - *Action*: Reverse 180° cut looking north. Aoi drops from the antenna gantry, boots splashing on wet carbon tarmac with flaring cyber-rings. Ren rises to meet her.
  - *Dialogue*: Ren's calm inquiry (`~2.8s`), followed by Aoi's bold smirk and warning line (`~2.5s`).

#### Prompt 02: *The Drone Ambush and Deflection* (Total: ~10.5s – 11.0s)
* **[Shot 1] Vent Breach & Drone Launch** (`00:00.000 – 00:05.500` \| **Duration: 5.5s**):
  - *Action*: High-angle medium-wide shot. Rooftop vents blast open with pressurized steam. Three quadruped combat drones ascend into hover mode, converging crimson targeting lasers on the duo. Aoi drops behind a terminal; Ren steps into the vanguard.
* **[Shot 2] Plasma Katana Deflection** (`00:05.500 – 00:11.000` \| **Duration: ~5.5s**):
  - *Action*: Dynamic 45° low-angle framing. Ren draws his cyan plasma katana in an arc of light, spinning into a circular guard that bats away rapid-fire laser rounds into sparkling rain-splashes.
  - *Dialogue*: Ren's command (`~2.5s`), followed by Aoi's rapid hacking confirmation (`~2.0s`).

#### Prompt 03: *The EMP Overload* (Total: ~10.5s – 11.0s)
* **[Shot 1] Sword Bisect & Execution** (`00:00.000 – 00:05.300` \| **Duration: 5.3s**):
  - *Action*: Ren fluidly slides under a leaping drone's strike and cleanly cleaves the chassis with his plasma blade in a burst of electrical sparks, while Aoi initiates the final console protocol.
* **[Shot 2] EMP Shockwave & Grid Blackout** (`00:05.300 – 00:10.800` \| **Duration: ~5.5s**):
  - *Action*: Elevated wide shot. An expansive toroidal turquoise EMP ring blasts across the wet helipad, shorting out the remaining drones and blacking out terminal floodlights.
  - *Dialogue*: Aoi's triumphant cheer (`~2.2s`), followed by Ren sheathing his katana with a metallic click and calling for extraction (`~2.5s`).

#### Prompt 04: *The Rooftop Dash* (Total: ~10.5s – 11.0s)
* **[Shot 1] Low-Angle Sprint & Blast Doors** (`00:00.000 – 00:05.500` \| **Duration: 5.5s**):
  - *Action*: Red strobe warning sirens pulse as security blast doors grind open in the background. Ren and Aoi break into a dead sprint across the rain-swept tarmac toward the southern ledge.
* **[Shot 2] Profile Tracking & Beacon Uplink** (`00:05.500 – 00:11.000` \| **Duration: ~5.5s**):
  - *Action*: High-speed side profile tracking shot. Armored boots kick up illuminated neon rooster tails; Aoi projects a pulsing rendezvous beacon from her gauntlet into the sky.
  - *Dialogue*: Ren's shouted ETA request (`~1.5s`), answered by Aoi's confident navigational lock (`~2.2s`).

#### Prompt 05: *The Sky Extraction* (Total: ~10.5s – 11.0s)
* **[Shot 1] VTOL Gunship Arrival & The Leap** (`00:00.000 – 00:05.400` \| **Duration: 5.4s**):
  - *Action*: Aerial shot tracking beside the precipice. A stealth VTOL gunship banks through storm clouds with glowing cyan plasma rotors, lowering its cargo ramp. Ren and Aoi leap together into the abyss in a spectacular synchronized arc.
* **[Shot 2] Cargo Bay Touchdown & Escape** (`00:05.400 – 00:11.000` \| **Duration: ~5.6s**):
  - *Action*: Camera inside the gunship bay looking out as the hydraulic ramp seals. Ren and Aoi land on the diamond-plate deck, catching their breath.
  - *Dialogue*: Aoi's cocky banter and salute (`~2.4s`), followed by Ren's understated smirk and closing remark (`~2.3s`) as afterburners ignite into the night sky.

---

## 💡 Generation & Pacing Tips
1. **Target Generation Duration**:
   - Set your video generation duration to **10s** or **11s** per prompt to give both shots full screen time for dialogue, swordplay choreography, and environmental atmosphere.
   - For **6-second** generation models, scale the cut marker to `00:03.000` (Shot 1: 3.0s, Shot 2: 3.0s).
2. **Audio / Speech Synchronization**:
   - Each shot provides a 1.5–2.0 second visual lead-in before dialogue begins, preventing cut clipping and allowing natural mouth-shape synchronization.
3. **Sequential Stitching**:
   - The end frame of each prompt's `[Shot 2]` directly matches the spatial staging, character postures, and camera line of the next prompt's `[Shot 1]`, enabling clean hard cuts or 0.3s soft cross-fades in an editor.

---

## 📝 Sequence Prompts (YAML / Structured Format)

1. **[`Prompt 01 - The Rainy Infiltration.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow%202/Prompt%2001%20-%20The%20Rainy%20Infiltration.txt)**
2. **[`Prompt 02 - The Drone Ambush and Deflection.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow%202/Prompt%2002%20-%20The%20Drone%20Ambush%20and%20Deflection.txt)**
3. **[`Prompt 03 - The EMP Overload.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow%202/Prompt%2003%20-%20The%20EMP%20Overload.txt)**
4. **[`Prompt 04 - The Rooftop Dash.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow%202/Prompt%2004%20-%20The%20Rooftop%20Dash.txt)**
5. **[`Prompt 05 - The Sky Extraction.txt`](file:///c:/Users/andy/AppData/Local/Comfy-Desktop/ComfyUI-Installs/ComfyUI%20Desktop/ComfyUI/custom_nodes/h3-reference-bus/sample%20workflow%202/Prompt%2005%20-%20The%20Sky%20Extraction.txt)**

---

## 🚀 Recommended ComfyUI Setup

1. **Reference Bus**:
   - Connect `reference_01_ren_shinobi.jpg` to `ref_image_0` (`<Picture 1>`).
   - Connect `reference_02_aoi_netrunner.jpg` to `ref_image_1` (`<Picture 2>`).
   - Connect `reference_03_neo_shinjuku_rooftop.jpg` to `ref_image_2` (`<Picture 3>`).
   - Connect `Ren.flac` to audio input (`<Audio 1>`).
   - Connect `Aoi.flac` to audio input (`<Audio 2>`).
2. **Prompt Loader (`LoadText`)**:
   - Point your `LoadText` node to any of the 5 prompt `.txt` files in this directory.
   - Keep `auto_reload` set to `on_file_change` so that editing prompts in your external editor updates generations automatically!
