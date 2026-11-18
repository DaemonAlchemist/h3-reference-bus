import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

let cachedPresets = null;

async function fetchStyleOptions() {
    try {
        const resp = await api.fetchApi("/h3/style_options", { method: "GET" });
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.presets) {
                cachedPresets = data.presets;
                return data;
            }
        }
    } catch (e) {
        console.warn("[ModularStyleComposer] Could not fetch style options:", e);
    }
    return null;
}

function isStyleComposerNode(node) {
    if (!node) return false;
    const c = node.comfyClass || node.constructor?.comfyClass || node.type;
    return c === "ModularStyleComposer" || c === "MiniMaxH3StyleComposer" || c === "StyleComposer";
}

app.registerExtension({
    name: "MiniMaxH3.ModularStyleComposer",

    async setup() {
        await fetchStyleOptions();
    },

    async nodeCreated(node) {
        if (!isStyleComposerNode(node)) return;

        if (!cachedPresets) {
            await fetchStyleOptions();
        }

        // Prevent duplicate action buttons if nodeCreated is triggered again
        if (node.widgets?.some(w => w.name === "randomize_options" || w.name === "reload_options")) return;

        const presetWidget = node.widgets?.find(w => w.name === "preset");
        const categoryWidgetNames = ["style", "mood", "lighting", "camera", "detail"];

        let isApplyingPreset = false;

        // Add status text widget
        const statusWidget = node.addWidget(
            "text",
            "style_status",
            presetWidget?.value && presetWidget.value !== "Custom"
                ? `Preset: ${presetWidget.value}`
                : "Style: Ready",
            () => {},
            { serialize: false }
        );

        if (statusWidget.inputEl) {
            statusWidget.inputEl.readOnly = true;
            statusWidget.inputEl.style.opacity = "0.75";
            statusWidget.inputEl.style.fontSize = "11px";
            statusWidget.inputEl.style.fontFamily = "monospace";
        }

        // Function to randomize all style dropdowns
        function randomizeAllDropdowns() {
            isApplyingPreset = true;
            try {
                for (const catName of categoryWidgetNames) {
                    const w = node.widgets?.find(x => x.name === catName);
                    if (!w || !w.options?.values?.length) continue;
                    // Filter out 'None' and 'Custom' if other options exist
                    let pool = w.options.values.filter(v => v !== "None" && v !== "Custom");
                    if (pool.length === 0) pool = w.options.values;
                    const chosen = pool[Math.floor(Math.random() * pool.length)];
                    w.value = chosen;
                }
            } finally {
                isApplyingPreset = false;
            }

            checkAndSyncPreset();

            if (statusWidget) {
                if (presetWidget && presetWidget.value !== "Custom") {
                    statusWidget.value = `🎲 Matched preset: ${presetWidget.value}`;
                } else {
                    statusWidget.value = "🎲 Randomized style combination";
                }
            }
            node.setDirtyCanvas(true, true);
        }

        // Add "Randomize" button widget
        const randomizeBtn = node.addWidget(
            "button",
            "🎲 Randomize",
            "randomize_options",
            () => {
                randomizeAllDropdowns();
            }
        );
        randomizeBtn.serialize = false;

        // Add "Reload Options" button widget
        const reloadBtn = node.addWidget(
            "button",
            "🔄 Reload Options",
            "reload_options",
            async () => {
                await reloadAllStyleNodes(node);
            }
        );
        reloadBtn.serialize = false;

        // Setup Preset dropdown change listener
        if (presetWidget) {
            const origPresetCb = presetWidget.callback;
            presetWidget.callback = function(val) {
                if (origPresetCb) origPresetCb.apply(this, arguments);
                if (!val || val === "Custom" || !cachedPresets) {
                    if (val === "Custom" && statusWidget) {
                        statusWidget.value = "Mode: Custom combination";
                        node.setDirtyCanvas(true, true);
                    }
                    return;
                }

                const presetData = cachedPresets[val];
                if (!presetData) return;

                isApplyingPreset = true;
                try {
                    for (const [key, targetVal] of Object.entries(presetData)) {
                        const targetWidget = node.widgets?.find(w => w.name === key);
                        if (targetWidget) {
                            targetWidget.value = targetVal;
                        }
                    }
                } finally {
                    isApplyingPreset = false;
                }

                if (statusWidget) {
                    statusWidget.value = `Applied preset: ${val}`;
                }
                node.setDirtyCanvas(true, true);
            };
        }

        // Setup Category dropdown change listeners (auto-switch to Custom)
        function checkAndSyncPreset() {
            if (isApplyingPreset || !presetWidget || !cachedPresets) return;

            let matchedPreset = null;
            for (const [pName, pData] of Object.entries(cachedPresets)) {
                if (pName === "Custom") continue;
                let allMatch = true;
                for (const [k, v] of Object.entries(pData)) {
                    const w = node.widgets?.find(x => x.name === k);
                    if (!w || w.value !== v) {
                        allMatch = false;
                        break;
                    }
                }
                if (allMatch) {
                    matchedPreset = pName;
                    break;
                }
            }

            const targetPreset = matchedPreset || "Custom";
            if (presetWidget.value !== targetPreset) {
                presetWidget.value = targetPreset;
                if (statusWidget) {
                    statusWidget.value = matchedPreset
                        ? `Matched preset: ${matchedPreset}`
                        : "Mode: Custom combination";
                }
                node.setDirtyCanvas(true, true);
            }
        }

        for (const catName of categoryWidgetNames) {
            const w = node.widgets?.find(x => x.name === catName);
            if (w) {
                const origCb = w.callback;
                w.callback = function() {
                    if (origCb) origCb.apply(this, arguments);
                    checkAndSyncPreset();
                };
            }
        }
    }
});

async function reloadAllStyleNodes(triggerNode) {
    let triggerStatus = null;
    if (triggerNode) {
        triggerStatus = triggerNode.widgets?.find(w => w.name === "style_status");
        if (triggerStatus) {
            triggerStatus.value = "Reloading options from disk...";
            triggerNode.setDirtyCanvas(true, true);
        }
    }

    try {
        const resp = await api.fetchApi("/h3/reload_style_options", { method: "POST" });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || "Failed to reload options");

        cachedPresets = data.presets || {};

        // Find all style composer nodes on the graph
        const allNodes = app.graph?._nodes || [];
        const styleNodes = allNodes.filter(n => isStyleComposerNode(n));

        for (const sNode of styleNodes) {
            if (!sNode.widgets) continue;

            for (const [category, values] of Object.entries(data.options || {})) {
                const w = sNode.widgets.find(x => x.name === category);
                if (w && w.options) {
                    w.options.values = values;
                    // Keep current value if still valid, otherwise reset
                    if (!values.includes(w.value)) {
                        w.value = values.includes("None")
                            ? "None"
                            : (values.includes("Custom") ? "Custom" : values[0]);
                    }
                }
            }

            const st = sNode.widgets.find(w => w.name === "style_status");
            if (st) {
                const styleCount = data.options?.style?.length || 0;
                const presetCount = Object.keys(cachedPresets).length;
                st.value = `Reloaded! (${styleCount} styles, ${presetCount} presets)`;
            }
            sNode.setDirtyCanvas(true, true);
        }
    } catch (err) {
        console.error("[ModularStyleComposer] Reload error:", err);
        if (triggerStatus) {
            triggerStatus.value = `Reload error: ${err.message}`;
            if (triggerNode) triggerNode.setDirtyCanvas(true, true);
        }
    }
}

