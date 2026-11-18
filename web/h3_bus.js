import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function isCreateNamedBus(node) {
    if (!node) return false;
    const c = node.comfyClass || node.constructor?.comfyClass || node.type;
    return c === "MiniMaxH3CreateNamedReferenceBus" || c === "CreateNamedReferenceBus";
}

function isCreateImageBus(node) {
    if (!node) return false;
    const c = node.comfyClass || node.constructor?.comfyClass || node.type;
    return c === "MiniMaxH3CreateImageReferenceBus" || c === "CreateImageReferenceBus";
}

function isExpandNamedBus(node) {
    if (!node) return false;
    const c = node.comfyClass || node.constructor?.comfyClass || node.type;
    return c === "MiniMaxH3ExpandNamedReferenceBus" || c === "ExpandNamedReferenceBus";
}

function isMapNamedBus(node) {
    if (!node) return false;
    const c = node.comfyClass || node.constructor?.comfyClass || node.type;
    return c === "MiniMaxH3MapNamedReferenceBus" || c === "MapNamedReferenceBus";
}

function cleanBasename(pathStr) {
    if (!pathStr || typeof pathStr !== "string") return "entity";
    let clean = pathStr.trim().replace(/^["'`]|["'`]$/g, "");
    clean = clean.split(/[\\/]/).pop() || clean;
    return clean.trim() || "entity";
}

function resolveSourceNode(originNode, slotIndex) {
    let curr = originNode;
    let slot = slotIndex;
    const visited = new Set();
    while (curr && !visited.has(curr.id)) {
        visited.add(curr.id);
        if (curr.type === "Reroute" || curr.comfyClass === "Reroute") {
            const inp = curr.inputs?.[0];
            if (inp && inp.link != null) {
                const link = app.graph.links[inp.link];
                if (link) {
                    const nextId = link.origin_id !== undefined ? link.origin_id : link[1];
                    const nextSlot = link.origin_slot !== undefined ? link.origin_slot : link[2];
                    curr = app.graph.getNodeById(nextId);
                    slot = nextSlot;
                    continue;
                }
            }
        }
        break;
    }
    return { node: curr, slot };
}

function extractFilenameFromNode(sourceNode, slotIndex) {
    if (!sourceNode) return "entity";

    // 1. Specific file widget names by priority
    const fileWidgetNames = [
        "image", "audio", "video", "filename", "file", "path",
        "file_path", "image_path", "sound_path", "audio_path", "video_path"
    ];

    if (sourceNode.widgets) {
        for (const name of fileWidgetNames) {
            const w = sourceNode.widgets.find(w => w.name && w.name.toLowerCase() === name);
            if (w && typeof w.value === "string" && w.value.trim()) {
                return cleanBasename(w.value);
            }
        }

        // 2. Check string widgets with a file extension or path slash
        for (const w of sourceNode.widgets) {
            if (typeof w.value === "string" && w.value.trim()) {
                const val = w.value.trim();
                if (/\.[a-zA-Z0-9]{2,5}$/.test(val) || val.includes("/") || val.includes("\\")) {
                    return cleanBasename(val);
                }
            }
        }

        // 3. Fallback: string widget with reasonable length and not multiline
        for (const w of sourceNode.widgets) {
            if (typeof w.value === "string" && w.value.trim() && w.value.length < 80 && !w.value.includes("\n")) {
                return cleanBasename(w.value);
            }
        }
    }

    // 4. Custom node title or type
    if (sourceNode.title && sourceNode.title !== sourceNode.type) {
        return cleanBasename(sourceNode.title);
    }
    return cleanBasename(sourceNode.type || "entity");
}

function collectEntitiesFromCreateBus(createNode, visited = new Set()) {
    if (!createNode || visited.has(createNode.id)) return [];
    visited.add(createNode.id);

    let upstreamEntities = [];
    const busBehaviorWidget = createNode.widgets?.find(w => w.name === "bus_behavior");
    const busBehavior = busBehaviorWidget ? busBehaviorWidget.value : "append";

    const upBusInput = createNode.inputs?.find(i => i.name === "bus");
    if (upBusInput && upBusInput.link != null) {
        const upLink = app.graph.links[upBusInput.link];
        if (upLink) {
            const originId = upLink.origin_id !== undefined ? upLink.origin_id : upLink[1];
            const originSlot = upLink.origin_slot !== undefined ? upLink.origin_slot : upLink[2];
            const upNode = app.graph.getNodeById(originId);
            const resolved = resolveSourceNode(upNode, originSlot);
            if (resolved && resolved.node) {
                upstreamEntities = collectEntitiesFromCreateBus(resolved.node, visited);
            }
        }
    }

    // Collect local attached entities
    const localEntities = [];
    if (createNode.inputs) {
        for (let i = 0; i < createNode.inputs.length; i++) {
            const inp = createNode.inputs[i];
            if (inp.name === "bus") continue;
            if (inp.link != null) {
                const link = app.graph.links[inp.link];
                if (link) {
                    const originId = link.origin_id !== undefined ? link.origin_id : link[1];
                    const originSlot = link.origin_slot !== undefined ? link.origin_slot : link[2];
                    const originNode = app.graph.getNodeById(originId);
                    const resolved = resolveSourceNode(originNode, originSlot);
                    const filename = extractFilenameFromNode(resolved.node, resolved.slot);

                    let slotType = "*";
                    if (resolved.node && resolved.node.outputs && resolved.node.outputs[resolved.slot]) {
                        slotType = resolved.node.outputs[resolved.slot].type || "*";
                    }

                    localEntities.push({
                        slotIndex: i,
                        inputName: inp.name,
                        label: filename,
                        type: slotType,
                        sourceNode: resolved.node,
                    });
                }
            }
        }
    }

function disambiguateEntityLabels(entities) {
    const seen = new Map();
    return entities.map(ent => {
        const raw = ent.label || "entity";
        const count = seen.get(raw) || 0;
        seen.set(raw, count + 1);
        if (count === 0) return ent;
        const dotIdx = raw.lastIndexOf(".");
        const uniqueLabel = dotIdx > 0
            ? `${raw.slice(0, dotIdx)} (${count + 1})${raw.slice(dotIdx)}`
            : `${raw} (${count + 1})`;
        return { ...ent, label: uniqueLabel };
    });
}

    let result = [];
    if (busBehavior === "append") {
        result = [...upstreamEntities, ...localEntities];
    } else {
        const map = new Map();
        for (const ent of upstreamEntities) map.set(ent.label, ent);
        for (const ent of localEntities) map.set(ent.label, ent);
        result = Array.from(map.values());
    }
    return disambiguateEntityLabels(result);
}

function getUpstreamCreateBusNode(expandNode) {
    if (!app.graph || !expandNode.inputs) return null;
    const busIn = expandNode.inputs.find(i => i.name === "bus");
    if (!busIn || busIn.link == null) return null;
    const link = app.graph.links[busIn.link];
    if (!link) return null;

    const originId = link.origin_id !== undefined ? link.origin_id : link[1];
    const originSlot = link.origin_slot !== undefined ? link.origin_slot : link[2];
    const node = app.graph.getNodeById(originId);
    const resolved = resolveSourceNode(node, originSlot);
    return resolved.node;
}

function updateExpandNodeOutputs(expandNode) {
    if (!app.graph || !expandNode) return;

    const createNode = getUpstreamCreateBusNode(expandNode);
    const isCreateBus = createNode && (
        isCreateNamedBus(createNode) ||
        isCreateImageBus(createNode) ||
        createNode.comfyClass === "MiniMaxH3CreateReferenceBus" ||
        createNode.type === "MiniMaxH3CreateReferenceBus"
    );

    const entities = isCreateBus ? collectEntitiesFromCreateBus(createNode) : [];
    const oldOutputs = expandNode.outputs ? [...expandNode.outputs] : [];

    // Map existing links by label and previous index to preserve user connections
    const linkMap = new Map();
    for (let i = 0; i < oldOutputs.length; i++) {
        const out = oldOutputs[i];
        if (out && out.links && out.links.length > 0) {
            if (out.label) linkMap.set(out.label, [...out.links]);
            linkMap.set(`slot_${i}`, [...out.links]);
        }
    }

    const newOutputs = [];
    const usedLinks = new Set();

    for (let i = 0; i < entities.length; i++) {
        const ent = entities[i];
        let preservedLinks = linkMap.get(ent.label);
        if (!preservedLinks) {
            preservedLinks = linkMap.get(`slot_${i}`);
        }

        const slotLinks = [];
        if (preservedLinks) {
            for (const lid of preservedLinks) {
                if (!usedLinks.has(lid) && app.graph.links[lid]) {
                    usedLinks.add(lid);
                    slotLinks.push(lid);
                    const linkObj = app.graph.links[lid];
                    if (linkObj) {
                        if (linkObj.origin_slot !== undefined) {
                            linkObj.origin_slot = i;
                        }
                        if (Array.isArray(linkObj)) {
                            linkObj[2] = i;
                        }
                    }
                }
            }
        }

        newOutputs.push({
            name: `entity_${i}`,
            label: ent.label,
            type: ent.type || "*",
            links: slotLinks.length > 0 ? slotLinks : null,
        });
    }

    // Clean up any remaining links that were disconnected
    for (let i = 0; i < oldOutputs.length; i++) {
        const out = oldOutputs[i];
        if (out && out.links) {
            for (const lid of out.links) {
                if (!usedLinks.has(lid) && app.graph.links[lid]) {
                    app.graph.removeLink(lid);
                }
            }
        }
    }

    expandNode.outputs = newOutputs;

    // Update status widget if present
    const statusWidget = expandNode.widgets?.find(w => w.name === "expand_status");
    if (statusWidget) {
        if (!isCreateBus) {
            statusWidget.value = "Bus: Not Connected";
        } else {
            statusWidget.value = `Bus: Connected (${entities.length} ${entities.length === 1 ? 'entity' : 'entities'})`;
        }
    }

    // Resize node to fit outputs cleanly
    if (expandNode.computeSize) {
        const sz = expandNode.computeSize();
        expandNode.setSize([Math.max(sz[0], 240), Math.max(sz[1], 60)]);
    }
    expandNode.setDirtyCanvas(true, true);
}

function notifyDownstreamExpandNodes(createNode, visited = new Set()) {
    if (!createNode || !app.graph || visited.has(createNode.id)) return;
    visited.add(createNode.id);

    const busOut = createNode.outputs?.find(o => o.name === "bus");
    if (!busOut || !busOut.links) return;

    for (const linkId of busOut.links) {
        const link = app.graph.links[linkId];
        if (!link) continue;
        const targetId = link.target_id !== undefined ? link.target_id : link[3];
        const targetNode = app.graph.getNodeById(targetId);
        if (!targetNode) continue;

        if (isExpandNamedBus(targetNode)) {
            updateExpandNodeOutputs(targetNode);
        } else if (isMapNamedBus(targetNode)) {
            updateMapStatus(targetNode);
        } else if (targetNode.type === "Reroute" || targetNode.comfyClass === "Reroute") {
            notifyThroughReroute(targetNode, visited);
        } else if (isCreateNamedBus(targetNode)) {
            notifyDownstreamExpandNodes(targetNode, visited);
        }
    }
}

function notifyThroughReroute(rerouteNode, visited) {
    const out = rerouteNode.outputs?.[0];
    if (!out || !out.links) return;
    for (const linkId of out.links) {
        const link = app.graph.links[linkId];
        if (!link) continue;
        const targetId = link.target_id !== undefined ? link.target_id : link[3];
        const targetNode = app.graph.getNodeById(targetId);
        if (!targetNode) continue;

        if (isExpandNamedBus(targetNode)) {
            updateExpandNodeOutputs(targetNode);
        } else if (isMapNamedBus(targetNode)) {
            updateMapStatus(targetNode);
        } else if (targetNode.type === "Reroute" || targetNode.comfyClass === "Reroute") {
            notifyThroughReroute(targetNode, visited);
        }
    }
}

function updateMapStatus(node) {
    if (!node) return;
    const mappingWidget = node.widgets?.find(w => w.name === "mapping");
    const statusWidget = node.widgets?.find(w => w.name === "map_status");
    if (!statusWidget) return;

    let map = {};
    if (mappingWidget && mappingWidget.value) {
        try {
            map = typeof mappingWidget.value === "string" ? JSON.parse(mappingWidget.value) : mappingWidget.value;
        } catch (e) {
            map = {};
        }
    }

    const upstreamCreateNode = getUpstreamCreateBusNode(node);
    let entityCount = 0;
    if (upstreamCreateNode) {
        const entities = collectEntitiesFromCreateBus(upstreamCreateNode);
        entityCount = entities.length;
    }

    const imgCount = Object.keys(map).filter(k => k.startsWith("ref_image_")).length;
    const vidCount = Object.keys(map).filter(k => k.startsWith("ref_video_") && !k.startsWith("ref_video_audio_")).length;
    const vaCount = Object.keys(map).filter(k => k.startsWith("ref_video_audio_")).length;
    const audCount = Object.keys(map).filter(k => k.startsWith("ref_audio_")).length;
    const totalMapped = imgCount + vidCount + vaCount + audCount;

    const busIn = node.inputs?.find(i => i.name === "bus");
    const isConnected = busIn && busIn.link != null;

    if (!isConnected) {
        statusWidget.value = "Bus: Not Connected";
    } else if (totalMapped === 0) {
        statusWidget.value = `Mapped: Auto (${entityCount} ${entityCount === 1 ? 'entity' : 'entities'})`;
    } else {
        const parts = [];
        if (imgCount > 0) parts.push(`${imgCount} pic`);
        if (vidCount > 0) parts.push(`${vidCount} vid`);
        if (vaCount > 0) parts.push(`${vaCount} snd`);
        if (audCount > 0) parts.push(`${audCount} aud`);
        statusWidget.value = `Mapped: ${parts.join(", ")} (${entityCount} total)`;
    }
    node.setDirtyCanvas(true, true);
}

function syncCreateNodeInputs(node) {
    if (!node || node._syncingInputs) return;
    const graph = node.graph || app.graph || (app.canvas && app.canvas.graph);
    if (!graph) return;

    node._syncingInputs = true;
    try {
        if (!node.inputs) node.inputs = [];

        // Ensure "bus" input exists
        if (!node.inputs.some(inp => inp.name === "bus")) {
            node.addInput("bus", "H3_NAMED_REF_BUS,H3_REF_BUS");
        }

        // Get all entity inputs (all inputs except "bus")
        let entityInputs = node.inputs.filter(inp => inp.name !== "bus");

        // Rule 1: Ensure at least one entity input exists (entity_0)
        if (entityInputs.length === 0) {
            node.addInput("entity_0", "*");
            entityInputs = node.inputs.filter(inp => inp.name !== "bus");
        }

        // Count connected entity inputs
        const connectedEntities = entityInputs.filter(inp => inp.link != null);

        // Count trailing empty entity inputs
        let trailingEmptyCount = 0;
        for (let i = entityInputs.length - 1; i >= 0; i--) {
            if (entityInputs[i].link == null) {
                trailingEmptyCount++;
            } else {
                break;
            }
        }

        // Rule 2: There must ALWAYS be AT LEAST ONE trailing empty slot!
        // If trailingEmptyCount === 0 (all entity slots are connected, whether 1, 2, or N),
        // we MUST append an empty trailing extension slot!
        if (trailingEmptyCount === 0) {
            let nextIdx = entityInputs.length;
            while (node.inputs.some(inp => inp.name === `entity_${nextIdx}`)) {
                nextIdx++;
            }
            const added = node.addInput(`entity_${nextIdx}`, "*");
            if (added) {
                added.label = `entity_${nextIdx}`;
            }
            entityInputs = node.inputs.filter(inp => inp.name !== "bus");
            trailingEmptyCount = 1;
        } else if (trailingEmptyCount > 1) {
            // Rule 3: There must NEVER be more than ONE trailing empty slot!
            // Trim excess trailing empty slots from the bottom until exactly 1 remains
            while (trailingEmptyCount > 1) {
                const slotToRemove = entityInputs[entityInputs.length - 1];
                const idxInNode = node.inputs.lastIndexOf(slotToRemove);
                if (idxInNode !== -1) {
                    node.removeInput(idxInNode);
                    entityInputs.pop();
                    trailingEmptyCount--;
                } else {
                    break;
                }
            }
        }

        // Rule 4: Update labels and collect filenames from connected inputs
        const filenames = [];
        const seenNames = new Map();
        let connectedCount = 0;

        for (let i = 0; i < node.inputs.length; i++) {
            const inp = node.inputs[i];
            if (inp.name === "bus") continue;

            if (inp.link != null) {
                connectedCount++;
                const link = graph.links ? graph.links[inp.link] : (graph._links ? graph._links.get(inp.link) : null);
                if (link) {
                    const originId = link.origin_id !== undefined ? link.origin_id : link[1];
                    const originSlot = link.origin_slot !== undefined ? link.origin_slot : link[2];
                    const originNode = graph.getNodeById(originId);
                    const resolved = resolveSourceNode(originNode, originSlot);
                    let fname = extractFilenameFromNode(resolved.node, resolved.slot);
                    const count = seenNames.get(fname) || 0;
                    seenNames.set(fname, count + 1);
                    if (count > 0) {
                        const dotIdx = fname.lastIndexOf(".");
                        if (dotIdx > 0) {
                            fname = `${fname.slice(0, dotIdx)} (${count + 1})${fname.slice(dotIdx)}`;
                        } else {
                            fname = `${fname} (${count + 1})`;
                        }
                    }
                    inp.label = fname;
                    filenames.push(fname);

                    // Hook source node widgets
                    if (resolved.node && resolved.node.widgets) {
                        for (const w of resolved.node.widgets) {
                            if (!w._h3_bus_hooked) {
                                w._h3_bus_hooked = true;
                                const origCb = w.callback;
                                w.callback = function() {
                                    if (origCb) origCb.apply(this, arguments);
                                    setTimeout(() => syncCreateNodeInputs(node), 50);
                                };
                            }
                        }
                    }
                }
            } else {
                inp.label = inp.name;
            }
        }

        // Hidden entity_names widget
        let entityNamesWidget = node.widgets?.find(w => w.name === "entity_names");
        if (!entityNamesWidget) {
            entityNamesWidget = node.addWidget("text", "entity_names", "[]", () => {}, { serialize: true });
            entityNamesWidget.type = "hidden";
            if (entityNamesWidget.inputEl) entityNamesWidget.inputEl.style.display = "none";
        }
        if (entityNamesWidget) {
            entityNamesWidget.value = JSON.stringify(filenames);
        }

        // Status widget
        let statusWidget = node.widgets?.find(w => w.name === "bus_status");
        if (!statusWidget) {
            statusWidget = node.addWidget("text", "bus_status", "Attached: 0 entities (Root)", () => {}, { serialize: false });
            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }
        }
        if (statusWidget) {
            const busIn = node.inputs.find(i => i.name === "bus");
            const busTag = busIn?.link != null ? " [Bus Connected]" : " (Root)";
            statusWidget.value = `Attached: ${connectedCount} ${connectedCount === 1 ? 'entity' : 'entities'}${busTag}`;
        }

        // Node size
        if (node.computeSize) {
            const sz = node.computeSize();
            const currW = node.size ? node.size[0] : 240;
            node.setSize([Math.max(sz[0], currW, 240), Math.max(sz[1], 60)]);
        }

        node.setDirtyCanvas(true, true);
        if (graph.setDirtyCanvas) {
            graph.setDirtyCanvas(true, true);
        }
        if (app.canvas?.setDirty) {
            app.canvas.setDirty(true, true);
        }

        // Notify downstream expand nodes
        notifyDownstreamExpandNodes(node);
    } finally {
        node._syncingInputs = false;
    }
}

function classifyEntity(ent) {
    if (!ent) return "IMAGE";
    const type = (ent.type || "").toUpperCase();
    const fname = (ent.label || "").toLowerCase();
    const sourceClass = (ent.sourceNode?.comfyClass || ent.sourceNode?.type || "").toLowerCase();

    const isAudioExt = fname.endsWith(".flac") || fname.endsWith(".mp3") || fname.endsWith(".wav") || fname.endsWith(".ogg") || fname.endsWith(".m4a") || fname.endsWith(".aac") || fname.endsWith(".wma") || fname.endsWith(".opus");
    const isVideoExt = fname.endsWith(".mp4") || fname.endsWith(".mov") || fname.endsWith(".webm") || fname.endsWith(".mkv") || fname.endsWith(".avi") || fname.endsWith(".m4v");
    const isImageExt = fname.endsWith(".png") || fname.endsWith(".jpg") || fname.endsWith(".jpeg") || fname.endsWith(".webp") || fname.endsWith(".bmp") || fname.endsWith(".gif") || fname.endsWith(".tiff") || fname.endsWith(".tif");

    if (type === "AUDIO" || isAudioExt || sourceClass.includes("audio") || sourceClass.includes("sound") || sourceClass.includes("voice")) {
        return "AUDIO";
    }
    if (type === "VIDEO" || isVideoExt || sourceClass.includes("video") || sourceClass.includes("vhs_loadvideo")) {
        return "VIDEO";
    }
    if (type === "IMAGE" || isImageExt || sourceClass.includes("image")) {
        return "IMAGE";
    }

    if (fname.includes("audio") || fname.includes("sound") || fname.includes("voice") || fname.includes("bgm")) return "AUDIO";
    if (fname.includes("video") || fname.includes("vid_") || fname.includes("clip") || fname.includes("scene")) return "VIDEO";

    return "IMAGE";
}

function detectReferenceTypes(entities, currentMapping = {}) {
    let hasImages = false;
    let hasVideos = false;
    let hasAudios = false;

    for (const ent of entities) {
        const cat = classifyEntity(ent);
        if (cat === "IMAGE") hasImages = true;
        else if (cat === "VIDEO") hasVideos = true;
        else if (cat === "AUDIO") hasAudios = true;
    }

    if (entities.length === 0 && currentMapping) {
        for (const [k, v] of Object.entries(currentMapping)) {
            if (!v) continue;
            if (k.startsWith("ref_image_")) hasImages = true;
            if (k.startsWith("ref_video_") && !k.startsWith("ref_video_audio_")) hasVideos = true;
            if (k.startsWith("ref_audio_") || k.startsWith("ref_video_audio_")) hasAudios = true;
        }
    }

    return {
        hasImages,
        hasVideos,
        hasAudios,
        hasVideoAudios: hasVideos && hasAudios,
    };
}

function openSlotMappingModal(node) {
    const upstreamCreateNode = getUpstreamCreateBusNode(node);
    let entities = [];
    if (upstreamCreateNode) {
        entities = collectEntitiesFromCreateBus(upstreamCreateNode);
    }

    let mappingWidget = node.widgets?.find(w => w.name === "mapping");
    let currentMapping = {};
    if (mappingWidget && mappingWidget.value) {
        try {
            currentMapping = typeof mappingWidget.value === "string" ? JSON.parse(mappingWidget.value) : mappingWidget.value;
        } catch (e) {
            currentMapping = {};
        }
    }

    const refTypes = detectReferenceTypes(entities, currentMapping);

    const allSections = [
        {
            id: "images",
            title: "🖼️ Reference Images (Up to 9)",
            desc: "Referenced in prompt as <Picture 1> .. <Picture 9>",
            isRelevant: refTypes.hasImages,
            slots: Array.from({ length: 9 }, (_, i) => ({
                id: `ref_image_${i}`,
                name: `ref_image_${i + 1}`,
                tag: `<Picture ${i + 1}>`,
                expectedType: "IMAGE",
            })),
        },
        {
            id: "videos",
            title: "🎬 Reference Videos (Up to 3)",
            desc: "Referenced in prompt as <Video 1> .. <Video 3>",
            isRelevant: refTypes.hasVideos,
            slots: Array.from({ length: 3 }, (_, i) => ({
                id: `ref_video_${i}`,
                name: `ref_video_${i + 1}`,
                tag: `<Video ${i + 1}>`,
                expectedType: "VIDEO",
            })),
        },
        {
            id: "soundtracks",
            title: "🎵 Video Soundtracks (Up to 3)",
            desc: "Paired audio soundtrack for <Video 1> .. <Video 3>",
            isRelevant: refTypes.hasVideoAudios,
            slots: Array.from({ length: 3 }, (_, i) => ({
                id: `ref_video_audio_${i}`,
                name: `ref_video_audio_${i + 1}`,
                tag: `<Video ${i + 1} Soundtrack>`,
                expectedType: "AUDIO",
            })),
        },
        {
            id: "audios",
            title: "🔊 Standalone Audios (Up to 3)",
            desc: "Referenced in prompt as <Audio 1> .. <Audio 3>",
            isRelevant: refTypes.hasAudios,
            slots: Array.from({ length: 3 }, (_, i) => ({
                id: `ref_audio_${i}`,
                name: `ref_audio_${i + 1}`,
                tag: `<Audio ${i + 1}>`,
                expectedType: "AUDIO",
            })),
        },
    ];

    const visibleSections = allSections.filter(s => s.isRelevant);

    const existing = document.getElementById("h3-slot-mapping-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "h3-slot-mapping-overlay";
    Object.assign(overlay.style, {
        position: "fixed",
        top: "0",
        left: "0",
        width: "100vw",
        height: "100vh",
        backgroundColor: "rgba(0, 0, 0, 0.72)",
        backdropFilter: "blur(4px)",
        zIndex: "10005",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    });

    const modal = document.createElement("div");
    Object.assign(modal.style, {
        backgroundColor: "#181820",
        border: "1px solid #333346",
        borderRadius: "12px",
        width: "740px",
        maxWidth: "94vw",
        maxHeight: "85vh",
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 24px 54px rgba(0, 0, 0, 0.8)",
        color: "#eee",
        overflow: "hidden",
    });

    const header = document.createElement("div");
    Object.assign(header.style, {
        padding: "16px 20px",
        borderBottom: "1px solid #2d2d3c",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        backgroundColor: "#20202c",
    });

    header.innerHTML = `
        <div>
            <div style="font-size: 15px; font-weight: 600; color: #fff;">
                Map Named Bus to H3 Reference Slots
            </div>
            <div style="font-size: 11px; color: #9a9ab4; margin-top: 2px;">
                Assign named references from the incoming bus into standard MiniMax H3 prompt slots.
            </div>
        </div>
        <button id="h3-modal-close-btn" style="background: none; border: none; color: #aaa; font-size: 24px; cursor: pointer; padding: 2px 8px; line-height: 1; border-radius: 4px;">&times;</button>
    `;

    const subbar = document.createElement("div");
    Object.assign(subbar.style, {
        padding: "10px 20px",
        backgroundColor: "#1a1a24",
        borderBottom: "1px solid #262634",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "10px",
        fontSize: "12px",
    });

    const entityCountStr = entities.length > 0
        ? `<span style="color: #4ade80; font-weight: 500;">✓ Connected:</span> ${entities.length} ${entities.length === 1 ? 'entity' : 'entities'} available`
        : `<span style="color: #f87171; font-weight: 500;">⚠️ Notice:</span> No incoming Named Bus connected`;

    subbar.innerHTML = `
        <div style="color: #bbb;">${entityCountStr}</div>
        <div style="display: flex; gap: 8px;">
            <button id="h3-btn-auto-map" style="background: #25334c; color: #60a5fa; border: 1px solid #3b5278; padding: 5px 12px; border-radius: 5px; font-size: 11px; cursor: pointer; font-weight: 500;">⚡ Auto-Map</button>
            <button id="h3-btn-clear-all" style="background: #2b1f24; color: #f87171; border: 1px solid #4f2d37; padding: 5px 12px; border-radius: 5px; font-size: 11px; cursor: pointer;">🧹 Clear All</button>
        </div>
    `;

    const body = document.createElement("div");
    Object.assign(body.style, {
        padding: "16px 20px",
        overflowY: "auto",
        flex: "1",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
    });

    function escapeHtml(str) {
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function buildOptions(slot, selectedVal, expectedType) {
        const slotPrefix = slot && slot.tag ? `${slot.tag}: ` : "";
        let html = `<option value="">${escapeHtml(slotPrefix)}-- None (Unassigned) --</option>`;

        let relevantEntities = entities;
        if (expectedType && expectedType !== "*") {
            const filtered = entities.filter(ent => {
                if (ent.label === selectedVal) return true;
                const cat = classifyEntity(ent);
                return cat === expectedType || ent.type === "*";
            });
            if (filtered.length > 0) {
                relevantEntities = filtered;
            }
        }

        for (const ent of relevantEntities) {
            const isSel = ent.label === selectedVal ? "selected" : "";
            html += `<option value="${escapeHtml(ent.label)}" ${isSel}>${escapeHtml(slotPrefix)}${escapeHtml(ent.label)}</option>`;
        }
        if (selectedVal && !relevantEntities.some(e => e.label === selectedVal)) {
            html += `<option value="${escapeHtml(selectedVal)}" selected>${escapeHtml(slotPrefix)}⚠️ ${escapeHtml(selectedVal)} (saved)</option>`;
        }
        return html;
    }

    if (visibleSections.length === 0) {
        const emptyNotice = document.createElement("div");
        Object.assign(emptyNotice.style, {
            textAlign: "center",
            padding: "44px 20px",
            color: "#8a8aa0",
        });
        emptyNotice.innerHTML = `
            <div style="font-size: 32px; margin-bottom: 10px;">📁</div>
            <div style="font-size: 14px; font-weight: 500; color: #ddd; margin-bottom: 6px;">No Relevant References Connected</div>
            <div style="font-size: 12px; color: #7a7a92; max-width: 420px; margin: 0 auto; line-height: 1.5;">
                Connect reference nodes (images, videos, or audio) to the upstream <b>Create Named Reference Bus</b> to configure slot mappings.
            </div>
        `;
        body.appendChild(emptyNotice);
    } else {
        visibleSections.forEach((sec, idx) => {
            const secEl = document.createElement("div");
            Object.assign(secEl.style, {
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                paddingBottom: idx < visibleSections.length - 1 ? "18px" : "4px",
                borderBottom: idx < visibleSections.length - 1 ? "1px solid #28283a" : "none",
            });

            secEl.innerHTML = `
                <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 2px;">
                    <div style="font-weight: 600; font-size: 13px; color: #f0f0fa;">${sec.title}</div>
                    <div style="font-size: 11px; color: #7f7f98;">${escapeHtml(sec.desc)}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px;">
                    ${sec.slots.map(s => {
                        const selVal = currentMapping[s.id] || "";
                        return `
                            <select data-slot="${s.id}" data-expected="${s.expectedType}" title="${escapeHtml(s.tag)}" style="width: 100%; box-sizing: border-box; background: #20202c; color: #eee; border: 1px solid #3c3c52; border-radius: 4px; padding: 6px 8px; font-size: 12px; outline: none; cursor: pointer; text-overflow: ellipsis;">
                                ${buildOptions(s, selVal, s.expectedType)}
                            </select>
                        `;
                    }).join("")}
                </div>
            `;
            body.appendChild(secEl);
        });
    }

    const footer = document.createElement("div");
    Object.assign(footer.style, {
        padding: "12px 20px",
        borderTop: "1px solid #2d2d3a",
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        gap: "10px",
        backgroundColor: "#20202a",
    });

    footer.innerHTML = `
        <button id="h3-modal-cancel-btn" style="background: #2a2a36; color: #bbb; border: 1px solid #3c3c4e; padding: 7px 16px; border-radius: 6px; font-size: 13px; cursor: pointer;">Cancel</button>
        <button id="h3-modal-save-btn" style="background: #2563eb; color: #fff; border: 1px solid #1d4ed8; padding: 7px 18px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer;">Apply & Save</button>
    `;

    modal.appendChild(header);
    modal.appendChild(subbar);
    modal.appendChild(body);
    modal.appendChild(footer);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    function closeModal() {
        overlay.remove();
        document.removeEventListener("keydown", onKeyDown);
    }

    function onKeyDown(e) {
        if (e.key === "Escape") closeModal();
    }
    document.addEventListener("keydown", onKeyDown);

    overlay.onclick = (e) => {
        if (e.target === overlay) closeModal();
    };

    header.querySelector("#h3-modal-close-btn").onclick = closeModal;
    footer.querySelector("#h3-modal-cancel-btn").onclick = closeModal;

    subbar.querySelector("#h3-btn-clear-all").onclick = () => {
        const selects = modal.querySelectorAll("select[data-slot]");
        selects.forEach(s => s.value = "");
    };

    subbar.querySelector("#h3-btn-auto-map").onclick = () => {
        const selects = modal.querySelectorAll("select[data-slot]");
        selects.forEach(s => s.value = "");

        let imgSlotIdx = 0;
        let audSlotIdx = 0;
        let vidSlotIdx = 0;

        for (const ent of entities) {
            const cat = classifyEntity(ent);

            if (cat === "AUDIO") {
                if (audSlotIdx < 3) {
                    const sel = modal.querySelector(`select[data-slot="ref_audio_${audSlotIdx}"]`);
                    if (sel) sel.value = ent.label;
                    audSlotIdx++;
                }
            } else if (cat === "VIDEO") {
                if (vidSlotIdx < 3) {
                    const sel = modal.querySelector(`select[data-slot="ref_video_${vidSlotIdx}"]`);
                    if (sel) sel.value = ent.label;
                    vidSlotIdx++;
                }
            } else {
                if (imgSlotIdx < 9) {
                    const sel = modal.querySelector(`select[data-slot="ref_image_${imgSlotIdx}"]`);
                    if (sel) sel.value = ent.label;
                    imgSlotIdx++;
                }
            }
        }
    };

    footer.querySelector("#h3-modal-save-btn").onclick = () => {
        const selects = modal.querySelectorAll("select[data-slot]");
        const newMap = { ...currentMapping };
        visibleSections.forEach(sec => {
            sec.slots.forEach(slot => {
                delete newMap[slot.id];
            });
        });
        selects.forEach(s => {
            if (s.value) {
                newMap[s.getAttribute("data-slot")] = s.value;
            }
        });

        if (mappingWidget) {
            mappingWidget.value = JSON.stringify(newMap);
            if (mappingWidget.callback) {
                mappingWidget.callback(mappingWidget.value);
            }
        }

        updateMapStatus(node);
        node.setDirtyCanvas(true, true);
        closeModal();
    };
}

app.registerExtension({
    name: "MiniMaxH3.ReferenceBus",

    async nodeCreated(node) {
        if (node.comfyClass === "MiniMaxH3CreateReferenceBus") {
            const statusWidget = node.addWidget(
                "text",
                "bus_status",
                "Incoming Bus: None (Root)",
                () => {},
                { serialize: false }
            );

            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }

            function updateBusStatus() {
                if (!app.graph) return;
                const busInput = node.inputs?.find(i => i.name === "bus");
                if (!busInput || busInput.link == null) {
                    statusWidget.value = "Incoming Bus: None (Root)";
                    node.setDirtyCanvas(true, true);
                    return;
                }

                const link = app.graph.links[busInput.link];
                if (!link) {
                    statusWidget.value = "Incoming Bus: Connected";
                    node.setDirtyCanvas(true, true);
                    return;
                }

                let imgCount = 0;
                let vidCount = 0;
                let audCount = 0;

                function traverse(currentNode, visited = new Set()) {
                    if (!currentNode || visited.has(currentNode.id)) return;
                    visited.add(currentNode.id);

                    if (currentNode.inputs) {
                        for (const inp of currentNode.inputs) {
                            if (inp.link != null) {
                                if (inp.name.startsWith("ref_image_") || inp.name === "ref_images") {
                                    imgCount++;
                                } else if (inp.name.startsWith("ref_video_audio_") || inp.name === "ref_video_audios") {
                                    // Paired soundtrack
                                } else if (inp.name.startsWith("ref_video_") || inp.name === "ref_videos") {
                                    vidCount++;
                                } else if (inp.name.startsWith("ref_audio_") || inp.name === "ref_audios") {
                                    audCount++;
                                }
                            }
                        }
                    }

                    const upBus = currentNode.inputs?.find(i => i.name === "bus");
                    if (upBus && upBus.link != null) {
                        const upLink = app.graph.links[upBus.link];
                        if (upLink) {
                            traverse(app.graph.getNodeById(upLink.origin_id), visited);
                        }
                    }
                }

                traverse(app.graph.getNodeById(link.origin_id));
                const imgTag = imgCount > 0 ? ` (<Picture 1..${imgCount}>)` : "";
                statusWidget.value = `Incoming Bus: ${imgCount} img${imgTag}, ${vidCount} vid, ${audCount} aud`;
                node.setDirtyCanvas(true, true);
            }

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(updateBusStatus, 60);
            };

            setTimeout(updateBusStatus, 100);
        } else if (node.comfyClass === "MiniMaxH3CreateImageReferenceBus" || node.comfyClass === "CreateImageReferenceBus") {
            const statusWidget = node.addWidget(
                "text",
                "bus_status",
                "Incoming Bus: None (Root)",
                () => {},
                { serialize: false }
            );

            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }

            function updateImageBusStatus() {
                if (!app.graph) return;
                const busInput = node.inputs?.find(i => i.name === "bus");
                if (!busInput || busInput.link == null) {
                    statusWidget.value = "Incoming Bus: None (Root)";
                    node.setDirtyCanvas(true, true);
                    return;
                }

                const link = app.graph.links[busInput.link];
                if (!link) {
                    statusWidget.value = "Incoming Bus: Connected";
                    node.setDirtyCanvas(true, true);
                    return;
                }

                let imgCount = 0;

                function traverse(currentNode, visited = new Set()) {
                    if (!currentNode || visited.has(currentNode.id)) return;
                    visited.add(currentNode.id);

                    if (currentNode.inputs) {
                        for (const inp of currentNode.inputs) {
                            if (inp.link != null) {
                                if (inp.name.startsWith("ref_image_") || inp.name === "ref_images") {
                                    imgCount++;
                                }
                            }
                        }
                    }

                    const upBus = currentNode.inputs?.find(i => i.name === "bus");
                    if (upBus && upBus.link != null) {
                        const upLink = app.graph.links[upBus.link];
                        if (upLink) {
                            traverse(app.graph.getNodeById(upLink.origin_id), visited);
                        }
                    }
                }

                traverse(app.graph.getNodeById(link.origin_id));
                const imgTag = imgCount > 0 ? ` (<Picture 1..${imgCount}>)` : "";
                statusWidget.value = `Incoming Bus: ${imgCount} img${imgTag}`;
                node.setDirtyCanvas(true, true);
            }

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(updateImageBusStatus, 60);
            };

            setTimeout(updateImageBusStatus, 100);
        } else if (node.comfyClass === "MiniMaxH3CreateVideoSettingsBus") {
            const statusWidget = node.addWidget(
                "text",
                "settings_status",
                "Settings: Initializing...",
                () => {},
                { serialize: false }
            );

            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }

            function updateSettingsStatus() {
                if (!app.graph) return;
                const items = [];
                const modelIn = node.inputs?.find(i => i.name === "model");
                const clipIn = node.inputs?.find(i => i.name === "clip");
                const vaeIn = node.inputs?.find(i => i.name === "vae");
                const avaeIn = node.inputs?.find(i => i.name === "audio_vae");
                const busIn = node.inputs?.find(i => i.name === "bus");

                if (modelIn?.link != null) items.push("Model");
                if (clipIn?.link != null) items.push("CLIP");
                if (vaeIn?.link != null) items.push("Video VAE");
                if (avaeIn?.link != null) items.push("Audio VAE");

                const wWidget = node.widgets?.find(w => w.name === "width");
                const hWidget = node.widgets?.find(w => w.name === "height");
                const sWidget = node.widgets?.find(w => w.name === "steps");
                const res = `${wWidget?.value || 1344}x${hWidget?.value || 768}`;
                const stepsStr = sWidget?.value ? `, ${sWidget.value} steps` : "";

                const busTag = busIn?.link != null ? " [Bus Connected]" : "";
                const itemsStr = items.length > 0 ? items.join(", ") : "None";
                statusWidget.value = `Packed: ${itemsStr} (${res}${stepsStr})${busTag}`;
                node.setDirtyCanvas(true, true);
            }

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(updateSettingsStatus, 60);
            };

            for (const wName of ["width", "height", "steps"]) {
                const w = node.widgets?.find(x => x.name === wName);
                if (w) {
                    const origCb = w.callback;
                    w.callback = function() {
                        if (origCb) origCb.apply(this, arguments);
                        updateSettingsStatus();
                    };
                }
            }

            setTimeout(updateSettingsStatus, 100);
        } else if (node.comfyClass === "LoadText" || node.comfyClass === "MiniMaxH3LoadText" || node.comfyClass === "H3LoadText") {
            const filenameWidget = node.widgets?.find(w => w.name === "filename");

            // Add Choose File button widget
            const chooseBtn = node.addWidget(
                "button",
                "Choose File...",
                "choose_file",
                () => {
                    openFileDialog();
                }
            );
            chooseBtn.serialize = false;

            // Add File Info status widget
            const statusWidget = node.addWidget(
                "text",
                "file_info",
                "No file chosen",
                () => {},
                { serialize: false }
            );

            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }

            function updateStatusDisplay(val, extraInfo = "") {
                if (!statusWidget) return;
                if (!val || !val.trim()) {
                    statusWidget.value = "No file chosen";
                } else {
                    const clean = val.trim().replace(/^["'`]|["'`]$/g, "");
                    const base = clean.split(/[\\/]/).pop() || clean;
                    statusWidget.value = extraInfo ? `${base} (${extraInfo})` : `Selected: ${base}`;
                }
                node.setDirtyCanvas(true, true);
            }

            // Sync status display if filename already populated
            if (filenameWidget?.value) {
                updateStatusDisplay(filenameWidget.value);
            }

            // Listen to manual changes in filename widget
            if (filenameWidget) {
                const origCb = filenameWidget.callback;
                filenameWidget.callback = function(value) {
                    if (origCb) origCb.apply(this, arguments);
                    updateStatusDisplay(value);
                };
            }

            function getRealLocalPath(file) {
                if (!file) return null;
                // 1. Comfy Desktop Electron API (window.api.getPathForFile via webUtils)
                if (window.api && typeof window.api.getPathForFile === "function") {
                    try {
                        const p = window.api.getPathForFile(file);
                        if (p && typeof p === "string" && p.length > 0) return p;
                    } catch (e) {
                        console.warn("[LoadText] window.api.getPathForFile error:", e);
                    }
                }
                // 2. window.electronAPI
                if (window.electronAPI && typeof window.electronAPI.getPathForFile === "function") {
                    try {
                        const p = window.electronAPI.getPathForFile(file);
                        if (p && typeof p === "string" && p.length > 0) return p;
                    } catch (e) {
                        console.warn("[LoadText] window.electronAPI.getPathForFile error:", e);
                    }
                }
                // 3. Electron webUtils
                if (window.electron?.webUtils && typeof window.electron.webUtils.getPathForFile === "function") {
                    try {
                        const p = window.electron.webUtils.getPathForFile(file);
                        if (p && typeof p === "string" && p.length > 0) return p;
                    } catch (e) {}
                }
                // 4. Direct file.path (older Electron)
                if (file.path && typeof file.path === "string" && file.path.length > 0) {
                    return file.path;
                }
                return null;
            }

            let lastVisitedDir = "";
            try {
                lastVisitedDir = localStorage.getItem("h3_loadtext_last_visited_dir") || "";
            } catch (e) {}

            function recordLastVisitedDir(filePath) {
                if (!filePath || typeof filePath !== "string") return;
                const clean = filePath.trim().replace(/^["'`]|["'`]$/g, "");
                const idx = Math.max(clean.lastIndexOf("/"), clean.lastIndexOf("\\"));
                if (idx > 0) {
                    lastVisitedDir = clean.substring(0, idx);
                    try {
                        localStorage.setItem("h3_loadtext_last_visited_dir", lastVisitedDir);
                    } catch (e) {}
                }
            }

            async function handleSelectedFile(file) {
                if (!file) return;

                const sizeKb = (file.size / 1024).toFixed(1);
                const localPath = getRealLocalPath(file);

                if (localPath) {
                    recordLastVisitedDir(localPath);
                    if (filenameWidget) {
                        filenameWidget.value = localPath;
                        if (filenameWidget.callback) {
                            filenameWidget.callback(localPath);
                        }
                    }
                    updateStatusDisplay(localPath, `${sizeKb} KB`);
                    return;
                }

                // If running in browser and no local path could be resolved:
                // Do NOT silently upload and break auto-updating!
                alert(
                    "Note: In a remote web browser, browser sandbox security hides the full OS file path.\n\n" +
                    "To enable live auto-updates on file changes, please paste or type the full file path directly into the filename box."
                );
                if (filenameWidget) {
                    filenameWidget.value = file.name;
                    if (filenameWidget.callback) filenameWidget.callback(file.name);
                }
                updateStatusDisplay(file.name, "path sandboxed");
            }

            async function openFileDialog() {
                // 1. Ask backend server to launch host OS native file dialog on the last visited folder
                try {
                    statusWidget.value = "Opening system dialog...";
                    node.setDirtyCanvas(true, true);

                    const resp = await api.fetchApi("/h3/open_file_dialog", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            current_path: filenameWidget?.value || "",
                            last_visited_dir: lastVisitedDir || ""
                        }),
                    });

                    if (resp.ok) {
                        const data = await resp.json();
                        if (data.last_visited_dir) {
                            lastVisitedDir = data.last_visited_dir;
                            try {
                                localStorage.setItem("h3_loadtext_last_visited_dir", lastVisitedDir);
                            } catch (e) {}
                        }
                        if (data.path) {
                            recordLastVisitedDir(data.path);
                            if (filenameWidget) {
                                filenameWidget.value = data.path;
                                if (filenameWidget.callback) filenameWidget.callback(data.path);
                            }
                            updateStatusDisplay(data.path, data.size_kb ? `${data.size_kb} KB` : "");
                            return;
                        } else if (data.canceled) {
                            updateStatusDisplay(filenameWidget?.value || "");
                            return;
                        }
                    }
                } catch (err) {
                    console.warn("[LoadText] Server open_file_dialog failed, trying fallback browser picker:", err);
                }

                // 2. Fallback to browser file input (if server dialog fails or remote headless host)
                let fileInput = document.getElementById("h3-loadtext-file-input");
                if (!fileInput) {
                    fileInput = document.createElement("input");
                    fileInput.id = "h3-loadtext-file-input";
                    fileInput.type = "file";
                    fileInput.accept = ".txt,.md,.json,.yaml,.yml,.csv,.xml,.log,.prompt,.rtf,text/*,*/*";
                    fileInput.style.display = "none";
                    document.body.appendChild(fileInput);
                }

                fileInput.value = "";
                fileInput.onchange = async (e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                        await handleSelectedFile(file);
                    }
                };

                fileInput.click();
            }

            // Drag-and-drop file support directly onto the node
            const origOnDropFile = node.onDropFile;
            node.onDropFile = function(file) {
                if (file) {
                    handleSelectedFile(file);
                    return true;
                }
                if (origOnDropFile) {
                    return origOnDropFile.apply(this, arguments);
                }
                return false;
            };

            // Resize node to fit widgets nicely
            setTimeout(() => {
                if (node.computeSize) {
                    const sz = node.computeSize();
                    node.setSize([Math.max(node.size[0], sz[0], 280), Math.max(node.size[1], sz[1])]);
                    node.setDirtyCanvas(true, true);
                }
            }, 60);
        } else if (isCreateNamedBus(node)) {
            // Status widget
            let statusWidget = node.widgets?.find(w => w.name === "bus_status");
            if (!statusWidget) {
                statusWidget = node.addWidget(
                    "text",
                    "bus_status",
                    "Attached: 0 entities (Root)",
                    () => {},
                    { serialize: false }
                );
                if (statusWidget.inputEl) {
                    statusWidget.inputEl.readOnly = true;
                    statusWidget.inputEl.style.opacity = "0.75";
                    statusWidget.inputEl.style.fontSize = "11px";
                    statusWidget.inputEl.style.fontFamily = "monospace";
                }
            }

            // Hidden entity_names widget for serialization to python backend
            let entityNamesWidget = node.widgets?.find(w => w.name === "entity_names");
            if (!entityNamesWidget) {
                entityNamesWidget = node.addWidget(
                    "text",
                    "entity_names",
                    "[]",
                    () => {},
                    { serialize: true }
                );
                entityNamesWidget.type = "hidden";
                if (entityNamesWidget.inputEl) {
                    entityNamesWidget.inputEl.style.display = "none";
                }
            }

            node._syncCreateNodeInputs = () => syncCreateNodeInputs(node);

            const origOnConfigure = node.onConfigure;
            node.onConfigure = function(info) {
                if (origOnConfigure) {
                    origOnConfigure.apply(this, arguments);
                }
                setTimeout(() => syncCreateNodeInputs(node), 20);
                setTimeout(() => syncCreateNodeInputs(node), 100);
                setTimeout(() => syncCreateNodeInputs(node), 250);
            };

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(() => syncCreateNodeInputs(node), 20);
                setTimeout(() => syncCreateNodeInputs(node), 80);
            };

            const origOnInputRemoved = node.onInputRemoved;
            node.onInputRemoved = function(slot, input) {
                if (origOnInputRemoved) {
                    origOnInputRemoved.apply(this, arguments);
                }
                setTimeout(() => syncCreateNodeInputs(node), 20);
            };

            const origOnInputAdded = node.onInputAdded;
            node.onInputAdded = function(slot) {
                if (origOnInputAdded) {
                    origOnInputAdded.apply(this, arguments);
                }
            };

            setTimeout(() => syncCreateNodeInputs(node), 30);
            setTimeout(() => syncCreateNodeInputs(node), 120);
        } else if (isExpandNamedBus(node)) {
            const statusWidget = node.addWidget(
                "text",
                "expand_status",
                "Bus: Not Connected",
                () => {},
                { serialize: false }
            );
            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(() => updateExpandNodeOutputs(node), 30);
            };

            // Immediately shrink node on creation
            updateExpandNodeOutputs(node);
            setTimeout(() => updateExpandNodeOutputs(node), 20);
            setTimeout(() => updateExpandNodeOutputs(node), 80);
        } else if (isMapNamedBus(node)) {
            // Button to open popup modal
            const mapBtn = node.addWidget(
                "button",
                "Map Slots...",
                "map_slots",
                () => {
                    openSlotMappingModal(node);
                }
            );
            mapBtn.serialize = false;

            // Status display
            const statusWidget = node.addWidget(
                "text",
                "map_status",
                "Mapped: None (Auto by order)",
                () => {},
                { serialize: false }
            );
            if (statusWidget.inputEl) {
                statusWidget.inputEl.readOnly = true;
                statusWidget.inputEl.style.opacity = "0.75";
                statusWidget.inputEl.style.fontSize = "11px";
                statusWidget.inputEl.style.fontFamily = "monospace";
            }

            // Style raw JSON mapping input
            const mappingWidget = node.widgets?.find(w => w.name === "mapping");
            if (mappingWidget && mappingWidget.inputEl) {
                mappingWidget.inputEl.style.fontSize = "10px";
                mappingWidget.inputEl.style.maxHeight = "40px";
            }

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(() => updateMapStatus(node), 50);
            };

            setTimeout(() => {
                updateMapStatus(node);
                if (node.computeSize) {
                    const sz = node.computeSize();
                    node.setSize([Math.max(sz[0], 250), Math.max(sz[1], 80)]);
                }
            }, 80);
        }
    },

    loadedGraphNode(node) {
        if (isCreateNamedBus(node)) {
            setTimeout(() => syncCreateNodeInputs(node), 20);
            setTimeout(() => syncCreateNodeInputs(node), 100);
        } else if (isExpandNamedBus(node)) {
            setTimeout(() => updateExpandNodeOutputs(node), 20);
        } else if (isMapNamedBus(node)) {
            setTimeout(() => updateMapStatus(node), 20);
        }
    },

    afterConfigureGraph() {
        const syncAll = () => {
            const graph = app.graph || (app.canvas && app.canvas.graph);
            if (graph && graph._nodes) {
                for (const n of graph._nodes) {
                    if (isCreateNamedBus(n)) {
                        syncCreateNodeInputs(n);
                    } else if (isExpandNamedBus(n)) {
                        updateExpandNodeOutputs(n);
                    } else if (isMapNamedBus(n)) {
                        updateMapStatus(n);
                    }
                }
            }
        };
        setTimeout(syncAll, 20);
        setTimeout(syncAll, 100);
        setTimeout(syncAll, 300);
    },

    async setup() {
        const syncAllNodes = (targetGraph) => {
            const graph = targetGraph || app.graph || (app.canvas && app.canvas.graph);
            if (graph && graph._nodes) {
                for (const n of graph._nodes) {
                    if (isCreateNamedBus(n)) {
                        syncCreateNodeInputs(n);
                    } else if (isExpandNamedBus(n)) {
                        updateExpandNodeOutputs(n);
                    } else if (isMapNamedBus(n)) {
                        updateMapStatus(n);
                    }
                }
            }
        };

        // 1. Hook LiteGraph.LGraph.prototype.configure (catches all graph instances on load)
        const LGraphClass = window.LiteGraph?.LGraph || (app.graph ? app.graph.constructor : null);
        if (LGraphClass && LGraphClass.prototype && LGraphClass.prototype.configure) {
            const origProtoConfigure = LGraphClass.prototype.configure;
            LGraphClass.prototype.configure = function() {
                const res = origProtoConfigure.apply(this, arguments);
                const g = this;
                setTimeout(() => syncAllNodes(g), 20);
                setTimeout(() => syncAllNodes(g), 100);
                setTimeout(() => syncAllNodes(g), 300);
                return res;
            };
        }

        // 2. Also hook app.graph.configure if present
        if (app.graph && app.graph.configure) {
            const origConfigure = app.graph.configure;
            app.graph.configure = function() {
                const res = origConfigure.apply(this, arguments);
                setTimeout(() => syncAllNodes(app.graph), 20);
                setTimeout(() => syncAllNodes(app.graph), 100);
                setTimeout(() => syncAllNodes(app.graph), 300);
                return res;
            };
        }
    }
});

