import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

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
        }
    }
});

