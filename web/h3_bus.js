import { app } from "../../scripts/app.js";

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
                const res = `${wWidget?.value || 1344}x${hWidget?.value || 768}`;

                const busTag = busIn?.link != null ? " [Bus Connected]" : "";
                const itemsStr = items.length > 0 ? items.join(", ") : "None";
                statusWidget.value = `Packed: ${itemsStr} (${res})${busTag}`;
                node.setDirtyCanvas(true, true);
            }

            const origOnConnectionsChange = node.onConnectionsChange;
            node.onConnectionsChange = function(type, index, isConnected, link_info) {
                if (origOnConnectionsChange) {
                    origOnConnectionsChange.apply(this, arguments);
                }
                setTimeout(updateSettingsStatus, 60);
            };

            setTimeout(updateSettingsStatus, 100);
        }
    }
});
