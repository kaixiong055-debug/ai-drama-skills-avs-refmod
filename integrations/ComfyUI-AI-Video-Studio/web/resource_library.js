import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { chooseLibraryDirectory, useNativePicker, serverPathCompatible } from "./library_folders.js";

const EXTENSION_NAME = "ai_video_studio.resource_library.v040";

const I18N = {
    "zh-CN": {
        nodeTitle: "AI视频工作室｜永久资源库",
        purposeLabel: "作用",
        purpose: "永久素材入口。扫描指定目录并建立索引；在独立素材中心里把文件整理成角色、场景、道具、动作、声音等资源组，后续可直接用 @资源组 引用。不会把整个资源库加载到显存。",
        language: "界面语言",
        libraryPath: "资源库目录",
        notSelected: "尚未选择资源库目录",
        chooseFolder: "选择目录",
        openLibrary: "打开素材中心",
        rescan: "重新扫描",
        savingPath: "正在保存目录...",
        readingStatus: "正在读取资源库状态...",
        pathSelected: "资源库目录已保存",
        chooseFirst: "请先选择资源库目录",
        scanDone: (n) => `扫描完成：${n} 个素材`,
        scanDoneTime: (n, s) => `扫描完成：${n} 个媒体素材，用时 ${s}s`,
        status: (s) => `图片 ${s.image || 0} ｜ 视频 ${s.video || 0} ｜ 音频 ${s.audio || 0} ｜ 总计 ${s.total || 0}`,
        statusFailed: (e) => `资源库状态读取失败：${e}`,
        directoryTitle: "选择永久资源库目录",
        currentPath: "当前目录",
        up: "上一级",
        chooseCurrent: "选择当前目录",
        close: "关闭",
        loadingDirs: "正在读取目录...",
        noSubdirs: "这个目录下面没有子目录。",
        readFailed: (e) => `读取失败：${e}`,
        driveRoot: "位置",
        libraryTitle: "AI视频工作室｜永久资源库",
        browse: "选择目录",
        saveScan: "保存并扫描",
        searchPlaceholder: "搜索名称 / 文件名 / 路径 / @别名 / 标签",
        allTypes: "全部类型",
        image: "图片",
        video: "视频",
        audio: "音频",
        allCategories: "全部分类",
        notScanned: "未扫描",
        loading: "加载中...",
        noAssets: "没有找到素材。请先选择资源库目录并扫描。",
        uncategorized: "未分类",
        noAlias: "未设置 @别名",
        loadFailed: (e) => `加载失败：${e}`,
        scanning: "正在扫描资源库...",
        scanFailed: "扫描失败",
        editAsset: (n) => `编辑素材｜${n}`,
        displayName: "显示名称",
        alias: "@别名",
        category: "分类",
        tags: "标签（逗号分隔）",
        cancel: "取消",
        save: "保存",
        assetSaved: "素材信息已保存",
        outputDb: "资源数据库",
        outputSummary: "摘要",
    },
    "en-US": {
        nodeTitle: "AI Video Studio | Permanent Library",
        purposeLabel: "Purpose",
        purpose: "Permanent asset entry point. It indexes a folder, then the Asset Center lets you organize files into Character, Scene, Prop, Motion and Voice groups for future @ references. The whole library is never loaded into VRAM.",
        language: "Language",
        libraryPath: "Library Folder",
        notSelected: "No library folder selected",
        chooseFolder: "Choose Folder",
        openLibrary: "Open Asset Center",
        rescan: "Rescan",
        savingPath: "Saving folder...",
        readingStatus: "Reading library status...",
        pathSelected: "Library folder saved",
        chooseFirst: "Please choose a library folder first",
        scanDone: (n) => `Scan complete: ${n} assets`,
        scanDoneTime: (n, s) => `Scan complete: ${n} media assets in ${s}s`,
        status: (s) => `Images ${s.image || 0} | Videos ${s.video || 0} | Audio ${s.audio || 0} | Total ${s.total || 0}`,
        statusFailed: (e) => `Failed to read library status: ${e}`,
        directoryTitle: "Choose Permanent Library Folder",
        currentPath: "Current Folder",
        up: "Up",
        chooseCurrent: "Use This Folder",
        close: "Close",
        loadingDirs: "Reading folders...",
        noSubdirs: "This folder has no subfolders.",
        readFailed: (e) => `Failed to read folder: ${e}`,
        driveRoot: "Location",
        libraryTitle: "AI Video Studio | Permanent Library",
        browse: "Choose Folder",
        saveScan: "Save & Scan",
        searchPlaceholder: "Search name / filename / path / @alias / tags",
        allTypes: "All Types",
        image: "Images",
        video: "Videos",
        audio: "Audio",
        allCategories: "All Categories",
        notScanned: "Not scanned",
        loading: "Loading...",
        noAssets: "No assets found. Choose a library folder and scan first.",
        uncategorized: "Uncategorized",
        noAlias: "No @alias",
        loadFailed: (e) => `Load failed: ${e}`,
        scanning: "Scanning library...",
        scanFailed: "Scan failed",
        editAsset: (n) => `Edit Asset | ${n}`,
        displayName: "Display Name",
        alias: "@Alias",
        category: "Category",
        tags: "Tags (comma separated)",
        cancel: "Cancel",
        save: "Save",
        assetSaved: "Asset metadata saved",
        outputDb: "RESOURCE_DB",
        outputSummary: "Summary",
    },
};

function langCodeFromWidget(node) {
    return findWidget(node, "language")?.value === "English" ? "en-US" : "zh-CN";
}

function tr(lang) {
    return I18N[lang] || I18N["zh-CN"];
}

function css(el, styles) {
    Object.assign(el.style, styles);
    return el;
}

function elem(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
        if (key === "className") el.className = value;
        else if (key === "text") el.textContent = value;
        else if (key.startsWith("on") && typeof value === "function") {
            el.addEventListener(key.slice(2).toLowerCase(), value);
        } else if (value !== undefined && value !== null) {
            el.setAttribute(key, value);
        }
    }
    for (const child of children) {
        if (child == null) continue;
        el.append(child.nodeType ? child : document.createTextNode(String(child)));
    }
    return el;
}

function toast(message, isError = false) {
    const box = elem("div", { text: message });
    css(box, {
        position: "fixed", right: "24px", bottom: "24px", zIndex: "100000",
        background: isError ? "#8f2d2d" : "#265d3a", color: "white",
        padding: "12px 16px", borderRadius: "10px", boxShadow: "0 8px 30px #0007",
        fontSize: "14px", maxWidth: "520px"
    });
    document.body.append(box);
    setTimeout(() => box.remove(), 3600);
}

async function jsonFetch(url, options = {}) {
    const res = await api.fetchApi(url, options);
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (!res.ok || data.ok === false) {
        throw new Error(data.error || `${res.status} ${res.statusText}`);
    }
    return data;
}

function findWidget(node, name) {
    return node.widgets?.find((w) => w.name === name);
}

function setWidget(node, name, value) {
    const w = findWidget(node, name);
    if (!w) return;
    w.value = value;
    w.callback?.(value);
    node.graph?.setDirtyCanvas?.(true, true);
}

function hideNativeWidget(widget) {
    if (!widget || widget.__avsHidden) return;
    widget.__avsHidden = true;
    widget.__avsOriginalComputeSize = widget.computeSize;
    widget.computeSize = () => [0, -4];
    widget.hidden = true;
}

function humanBytes(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let n = Number(bytes), i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function mediaIcon(type) {
    return type === "video" ? "🎬" : type === "audio" ? "🔊" : "🖼️";
}

function translatedCategory(category, lang) {
    if (lang !== "en-US") return category;
    const map = {
        "角色": "Character", "场景": "Scene", "道具": "Prop",
        "动作": "Motion", "声音": "Voice / Audio", "未分类": "Uncategorized"
    };
    return map[category] || category;
}

function updateNodeLanguage(node, lang, refs = null) {
    const t = tr(lang);
    node.title = t.nodeTitle;
    if (node.outputs?.[0]) node.outputs[0].name = t.outputDb;
    if (node.outputs?.[1]) node.outputs[1].name = t.outputSummary;
    if (refs) {
        refs.purposeLabel.textContent = `${t.purposeLabel}：`;
        refs.purposeText.textContent = t.purpose;
        refs.languageLabel.textContent = t.language;
        refs.pathLabel.textContent = t.libraryPath;
        refs.chooseBtn.textContent = t.chooseFolder;
        refs.chooseBtn.title = refs.nativePicker ? t.chooseFolder : (lang === "en-US" ? "Choose and upload media from a computer folder" : "选择电脑文件夹，将其中的媒体素材上传到当前 ComfyUI");
        refs.serverBtn.textContent = lang === "en-US" ? "Server Folder" : "服务器目录";
        refs.serverBtn.style.display = refs.nativePicker ? "none" : "";
        refs.selectionHint.textContent = refs.nativePicker ? "" : (lang === "en-US" ? "Computer folder: selected media will be uploaded. Server folder: use files already on ComfyUI." : "电脑文件夹：上传所选图片、视频和音频；服务器目录：使用已放在云端的素材。");
        refs.openBtn.textContent = t.openLibrary;
        refs.scanBtn.textContent = t.rescan;
        if (!refs.pathText.dataset.hasPath) refs.pathText.textContent = t.notSelected;
    }
    node.graph?.setDirtyCanvas?.(true, true);
}

async function saveLanguage(lang) {
    await jsonFetch("/avs/settings/language", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: lang }),
    });
}

async function openDirectoryBrowser(initialPath, onSelect, lang = "zh-CN") {
    const t = tr(lang);
    const overlay = elem("div");
    css(overlay, {
        position: "fixed", inset: "0", zIndex: "100002", background: "#0009",
        display: "flex", alignItems: "center", justifyContent: "center"
    });
    const panel = elem("div");
    css(panel, {
        width: "760px", maxWidth: "94vw", maxHeight: "84vh", background: "#17181c",
        color: "#eee", border: "1px solid #3a3c43", borderRadius: "14px",
        boxShadow: "0 18px 70px #000a", display: "flex", flexDirection: "column"
    });

    const title = elem("div", { text: t.directoryTitle });
    css(title, { padding: "14px 14px 4px", fontWeight: "700", fontSize: "16px" });

    const rootRow = elem("div");
    css(rootRow, { padding: "8px 14px", display: "flex", gap: "8px", alignItems: "center" });
    const rootLabel = elem("span", { text: `${t.driveRoot}:` });
    css(rootLabel, { color: "#aaa", fontSize: "12px" });
    const roots = elem("select");
    css(roots, { background: "#202228", color: "#eee", border: "1px solid #41434b", borderRadius: "8px", padding: "7px", minWidth: "150px" });
    rootRow.append(rootLabel, roots);

    const head = elem("div");
    css(head, { padding: "8px 14px 14px", display: "flex", gap: "8px", borderBottom: "1px solid #333" });
    const pathInput = elem("input", { value: initialPath || "", readonly: "readonly", title: t.currentPath });
    css(pathInput, { flex: "1", background: "#0f1013", color: "#eee", border: "1px solid #444", borderRadius: "8px", padding: "9px" });
    const upBtn = elem("button", { text: t.up });
    const useBtn = elem("button", { text: t.chooseCurrent });
    const closeBtn = elem("button", { text: t.close });
    for (const b of [upBtn, useBtn, closeBtn]) css(b, { padding: "8px 12px", cursor: "pointer" });
    css(useBtn, { background: "#356ae6", color: "white", border: "none", borderRadius: "7px" });
    head.append(pathInput, upBtn, useBtn, closeBtn);

    const list = elem("div");
    css(list, { padding: "12px", overflow: "auto", display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "8px" });
    panel.append(title, rootRow, head, list);
    overlay.append(panel);
    document.body.append(overlay);

    let currentParent = "";
    async function load(path) {
        list.textContent = t.loadingDirs;
        useBtn.disabled = true;
        try {
            const data = await jsonFetch(`/avs/library/dirs?path=${encodeURIComponent(path || "")}`);
            pathInput.value = data.path;
            useBtn.disabled = false;
            currentParent = data.parent || "";

            const oldRoot = roots.value;
            roots.textContent = "";
            for (const root of data.roots || []) roots.append(elem("option", { value: root, text: root }));
            if ([...roots.options].some(o => o.value === oldRoot)) roots.value = oldRoot;
            else {
                const matched = [...roots.options].find(o => data.path.toLowerCase().startsWith(o.value.toLowerCase()));
                if (matched) roots.value = matched.value;
            }

            list.textContent = "";
            for (const name of data.dirs) {
                const item = elem("button", { text: `📁 ${name}` });
                css(item, {
                    textAlign: "left", padding: "10px", background: "#24262c", color: "#eee",
                    border: "1px solid #383a42", borderRadius: "8px", cursor: "pointer"
                });
                item.onclick = () => {
                    const sep = data.path.includes("\\") ? "\\" : "/";
                    load(data.path.replace(/[\\/]$/, "") + sep + name);
                };
                list.append(item);
            }
            if (!data.dirs.length) list.textContent = t.noSubdirs;
        } catch (e) {
            list.textContent = t.readFailed(e.message);
        }
    }

    roots.onchange = () => roots.value && load(roots.value);
    upBtn.onclick = () => currentParent && load(currentParent);
    useBtn.onclick = () => { onSelect(pathInput.value); overlay.remove(); };
    closeBtn.onclick = () => overlay.remove();
    load(initialPath || "");
}

function createEditor(asset, onSaved, lang = "zh-CN") {
    const t = tr(lang);
    const overlay = elem("div");
    css(overlay, { position: "fixed", inset: "0", zIndex: "100003", background: "#000a", display: "flex", alignItems: "center", justifyContent: "center" });
    const panel = elem("div");
    css(panel, { width: "560px", maxWidth: "92vw", background: "#18191e", color: "#eee", border: "1px solid #40424a", borderRadius: "14px", padding: "18px", boxShadow: "0 18px 70px #000b" });
    const title = elem("h3", { text: t.editAsset(asset.file_name) });
    css(title, { margin: "0 0 14px" });
    panel.append(title);

    const fields = {};
    const rows = [
        ["display_name", t.displayName, asset.display_name || ""],
        ["alias", t.alias, asset.alias || ""],
        ["category", t.category, asset.category || "未分类"],
        ["tags", t.tags, (asset.tags || []).join(", ")],
    ];
    for (const [key, label, value] of rows) {
        const wrap = elem("label");
        css(wrap, { display: "block", marginBottom: "12px", fontSize: "13px", color: "#bbb" });
        wrap.append(elem("div", { text: label }));
        const input = elem("input", { value });
        css(input, { width: "100%", boxSizing: "border-box", marginTop: "5px", background: "#0f1013", color: "#fff", border: "1px solid #444", borderRadius: "8px", padding: "9px" });
        fields[key] = input;
        wrap.append(input);
        panel.append(wrap);
    }
    const pathText = elem("div", { text: asset.relative_path });
    css(pathText, { fontSize: "12px", color: "#888", margin: "6px 0 16px", wordBreak: "break-all" });
    panel.append(pathText);
    const actions = elem("div");
    css(actions, { display: "flex", justifyContent: "flex-end", gap: "8px" });
    const cancel = elem("button", { text: t.cancel });
    const save = elem("button", { text: t.save });
    css(cancel, { padding: "9px 14px", cursor: "pointer" });
    css(save, { padding: "9px 14px", cursor: "pointer", background: "#356ae6", color: "white", border: "none", borderRadius: "7px" });
    actions.append(cancel, save);
    panel.append(actions);
    overlay.append(panel);
    document.body.append(overlay);
    cancel.onclick = () => overlay.remove();
    save.onclick = async () => {
        save.disabled = true;
        try {
            const data = await jsonFetch(`/avs/library/asset/${asset.id}/meta`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    display_name: fields.display_name.value,
                    alias: fields.alias.value,
                    category: fields.category.value,
                    tags: fields.tags.value,
                }),
            });
            overlay.remove();
            toast(t.assetSaved);
            onSaved?.(data.asset);
        } catch (e) {
            toast(e.message, true);
        } finally {
            save.disabled = false;
        }
    };
}

async function openLibrary(node, lang = "zh-CN") {
    const t = tr(lang);
    const overlay = elem("div");
    css(overlay, {
        position: "fixed", inset: "0", zIndex: "100001", background: "#08090ccf",
        display: "flex", alignItems: "center", justifyContent: "center", padding: "24px"
    });
    const panel = elem("div");
    css(panel, {
        width: "min(1280px, 96vw)", height: "min(850px, 92vh)", background: "#15161a",
        color: "#eee", border: "1px solid #353740", borderRadius: "16px",
        boxShadow: "0 24px 90px #000c", display: "flex", flexDirection: "column", overflow: "hidden"
    });

    const top = elem("div");
    css(top, { padding: "14px", borderBottom: "1px solid #30323a", display: "flex", gap: "8px", alignItems: "center" });
    const title = elem("strong", { text: t.libraryTitle });
    css(title, { minWidth: "220px", fontSize: "16px" });
    const pathInput = elem("input", { value: findWidget(node, "library_path")?.value || "", readonly: "readonly" });
    css(pathInput, { flex: "1", minWidth: "180px", background: "#0d0e11", color: "#eee", border: "1px solid #40424a", borderRadius: "8px", padding: "9px" });
    const browse = elem("button", { text: t.browse });
    const saveScan = elem("button", { text: t.saveScan });
    const scan = elem("button", { text: t.rescan });
    const close = elem("button", { text: t.close });
    for (const b of [browse, saveScan, scan, close]) css(b, { padding: "9px 12px", cursor: "pointer" });
    css(saveScan, { background: "#356ae6", color: "white", border: "none", borderRadius: "7px" });
    top.append(title, pathInput, browse, saveScan, scan, close);

    const toolbar = elem("div");
    css(toolbar, { padding: "10px 14px", display: "flex", gap: "8px", alignItems: "center", borderBottom: "1px solid #2a2c32" });
    const search = elem("input", { placeholder: t.searchPlaceholder });
    search.value = findWidget(node, "search")?.value || "";
    css(search, { flex: "1", background: "#0d0e11", color: "#eee", border: "1px solid #3a3c44", borderRadius: "8px", padding: "9px" });
    const type = elem("select");
    for (const [value, label] of [["all", t.allTypes], ["image", t.image], ["video", t.video], ["audio", t.audio]]) {
        type.append(elem("option", { value, text: label }));
    }
    type.value = findWidget(node, "media_type")?.value || "all";
    const category = elem("select");
    const statusText = elem("span", { text: t.notScanned });
    css(statusText, { color: "#aaa", minWidth: "260px", textAlign: "right", fontSize: "12px" });
    for (const x of [type, category]) css(x, { background: "#202228", color: "#eee", border: "1px solid #41434b", borderRadius: "8px", padding: "8px" });
    toolbar.append(search, type, category, statusText);

    const content = elem("div");
    css(content, { flex: "1", overflow: "auto", padding: "14px" });
    const grid = elem("div");
    css(grid, { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "12px" });
    content.append(grid);
    panel.append(top, toolbar, content);
    overlay.append(panel);
    document.body.append(overlay);

    let debounceTimer = null;

    async function loadStatus() {
        const data = await jsonFetch("/avs/library/status");
        if (data.config?.library_path && !pathInput.value) pathInput.value = data.config.library_path;
        const s = data.stats || {};
        statusText.textContent = t.status(s);
        const old = category.value;
        category.textContent = "";
        category.append(elem("option", { value: "", text: t.allCategories }));
        for (const c of s.categories || []) category.append(elem("option", { value: c, text: translatedCategory(c, lang) }));
        if ([...category.options].some(o => o.value === old)) category.value = old;
    }

    async function loadAssets() {
        grid.textContent = t.loading;
        try {
            const q = search.value.trim();
            const url = `/avs/library/assets?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type.value)}&category=${encodeURIComponent(category.value)}&limit=500`;
            const data = await jsonFetch(url);
            grid.textContent = "";
            if (!data.assets.length) {
                const empty = elem("div", { text: t.noAssets });
                css(empty, { color: "#aaa", gridColumn: "1 / -1", padding: "40px", textAlign: "center" });
                grid.append(empty);
                return;
            }
            for (const asset of data.assets) {
                const card = elem("div");
                css(card, { background: "#202126", border: "1px solid #34363e", borderRadius: "10px", overflow: "hidden", cursor: "pointer" });
                const preview = elem("div");
                css(preview, { height: "130px", background: "#0d0e11", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", fontSize: "42px" });
                if (asset.has_thumbnail) {
                    const img = elem("img", { src: `/avs/library/thumb/${asset.id}?v=${Math.floor(asset.mtime || 0)}` });
                    css(img, { width: "100%", height: "100%", objectFit: "cover" });
                    img.onerror = () => { img.remove(); preview.textContent = mediaIcon(asset.media_type); };
                    preview.append(img);
                } else {
                    preview.textContent = mediaIcon(asset.media_type);
                }
                const body = elem("div");
                css(body, { padding: "10px" });
                const name = elem("div", { text: asset.display_name });
                css(name, { fontWeight: "600", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" });
                const meta = elem("div", { text: `${translatedCategory(asset.category, lang)} · ${humanBytes(asset.size_bytes)}` });
                css(meta, { fontSize: "11px", color: "#999", marginTop: "4px" });
                const alias = elem("div", { text: asset.alias ? `@${asset.alias}` : t.noAlias });
                css(alias, { fontSize: "11px", color: asset.alias ? "#7fb1ff" : "#666", marginTop: "5px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" });
                body.append(name, meta, alias);
                card.append(preview, body);
                card.title = asset.relative_path;
                card.onclick = () => createEditor(asset, () => { loadStatus(); loadAssets(); }, lang);
                grid.append(card);
            }
        } catch (e) {
            grid.textContent = t.loadFailed(e.message);
        }
    }

    async function doScan(saveFirst) {
        const path = pathInput.value.trim();
        if (!path) return toast(t.chooseFirst, true);
        scan.disabled = saveScan.disabled = true;
        statusText.textContent = t.scanning;
        try {
            if (saveFirst) {
                await jsonFetch("/avs/library/config", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ library_path: path }),
                });
            }
            const result = await jsonFetch("/avs/library/scan", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ library_path: path }),
            });
            setWidget(node, "library_path", result.library_path);
            toast(t.scanDoneTime(result.scanned, result.seconds));
            await loadStatus();
            await loadAssets();
        } catch (e) {
            toast(e.message, true);
            statusText.textContent = t.scanFailed;
        } finally {
            scan.disabled = saveScan.disabled = false;
        }
    }

    browse.onclick = () => openDirectoryBrowser(pathInput.value, (p) => { pathInput.value = p; }, lang);
    saveScan.onclick = () => doScan(true);
    scan.onclick = () => doScan(false);
    close.onclick = () => overlay.remove();
    type.onchange = () => { setWidget(node, "media_type", type.value); loadAssets(); };
    category.onchange = () => { setWidget(node, "category", category.value); loadAssets(); };
    search.oninput = () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => { setWidget(node, "search", search.value); loadAssets(); }, 250);
    };
    await loadStatus();
    await loadAssets();
}

async function refreshNodeSummary(node, refs, lang = "zh-CN") {
    const t = tr(lang);
    try {
        const data = await jsonFetch("/avs/library/status");
        const s = data.stats || {};
        refs.status.textContent = t.status(s);
        const pathWidget = findWidget(node, "library_path");
        refs.nativePicker = useNativePicker(data);
        if (pathWidget && !serverPathCompatible(pathWidget.value, data.platform)) pathWidget.value = "";
        if (pathWidget && !pathWidget.value && data.config?.library_path) pathWidget.value = data.config.library_path;
        const path = pathWidget?.value || data.config?.library_path || "";
        refs.pathText.dataset.hasPath = path ? "1" : "";
        refs.pathText.textContent = path || t.notSelected;
        return data;
    } catch (e) {
        refs.status.textContent = t.statusFailed(e.message);
        return null;
    }
}

function buildNodePanel(node) {
    const wrap = elem("div");
    css(wrap, { padding: "4px 2px 8px", color: "#ddd", fontFamily: "sans-serif" });

    const purpose = elem("div");
    css(purpose, { background: "#202228", border: "1px solid #34363e", borderRadius: "8px", padding: "10px", marginBottom: "10px", lineHeight: "1.45" });
    const purposeLabel = elem("strong");
    const purposeText = elem("span");
    purpose.append(purposeLabel, purposeText);

    const langRow = elem("div");
    css(langRow, { display: "flex", alignItems: "center", gap: "8px", marginBottom: "9px" });
    const languageLabel = elem("span");
    css(languageLabel, { minWidth: "92px", color: "#aaa" });
    const languageSelect = elem("select");
    for (const [value, label] of [["zh-CN", "中文"], ["en-US", "English"]]) languageSelect.append(elem("option", { value, text: label }));
    css(languageSelect, { flex: "1", background: "#202228", color: "#eee", border: "1px solid #41434b", borderRadius: "7px", padding: "7px" });
    langRow.append(languageLabel, languageSelect);

    const pathLabel = elem("div");
    css(pathLabel, { color: "#aaa", fontSize: "12px", marginBottom: "5px" });
    const pathRow = elem("div");
    css(pathRow, { display: "flex", gap: "8px", marginBottom: "9px" });
    const pathText = elem("div");
    css(pathText, { flex: "1", background: "#111216", border: "1px solid #34363e", borderRadius: "7px", padding: "8px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "#ddd" });
    const chooseBtn = elem("button");
    css(chooseBtn, { padding: "7px 10px", cursor: "pointer", whiteSpace: "nowrap" });
    const serverBtn = elem("button");
    css(serverBtn, {padding:"7px 10px",cursor:"pointer",whiteSpace:"nowrap"});
    pathRow.append(pathText, chooseBtn, serverBtn);
    const selectionHint = elem("div");
    css(selectionHint, {fontSize:"11px",lineHeight:"1.4",color:"#aaa",marginBottom:"8px"});

    const buttons = elem("div");
    css(buttons, { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "8px" });
    const openBtn = elem("button");
    const scanBtn = elem("button");
    for (const b of [openBtn, scanBtn]) css(b, { padding: "9px", cursor: "pointer", fontWeight: "600" });
    css(openBtn, { background: "#356ae6", color: "white", border: "none", borderRadius: "7px" });
    buttons.append(openBtn, scanBtn);

    const status = elem("div");
    css(status, { padding: "6px 4px 2px", color: "#b7bac4", fontSize: "12px", textAlign: "center" });

    wrap.append(purpose, langRow, pathLabel, pathRow, selectionHint, buttons, status);
    return { wrap, purposeLabel, purposeText, languageLabel, languageSelect, pathLabel, pathText, chooseBtn, serverBtn, selectionHint, openBtn, scanBtn, status };
}

app.registerExtension({
    name: EXTENSION_NAME,
    async nodeCreated(node) {
        if (node.comfyClass !== "AVSResourceLibrary") return;

        // 技术参数继续保留在工作流里，但不要求普通用户手动填写。
        for (const name of ["language", "library_path", "search", "media_type", "category", "limit"]) {
            hideNativeWidget(findWidget(node, name));
        }

        const refs = buildNodePanel(node);
        try {
            node.addDOMWidget("avs_resource_panel", "avs_resource_panel", refs.wrap, { serialize: false });
        } catch (_) {
            // 当前 ComfyUI 已支持 DOM widget；保留兼容保护。
        }
        node.size = [520, 365];

        let lang = langCodeFromWidget(node);
        const statusData = await refreshNodeSummary(node, refs, lang);
        if (statusData?.config?.language) {
            lang = statusData.config.language;
            setWidget(node, "language", lang === "en-US" ? "English" : "中文");
        }
        refs.languageSelect.value = lang;
        updateNodeLanguage(node, lang, refs);
        await refreshNodeSummary(node, refs, lang);

        refs.languageSelect.onchange = async () => {
            lang = refs.languageSelect.value;
            setWidget(node, "language", lang === "en-US" ? "English" : "中文");
            updateNodeLanguage(node, lang, refs);
            try { await saveLanguage(lang); } catch (e) { toast(e.message, true); }
            await refreshNodeSummary(node, refs, lang);
            window.dispatchEvent(new CustomEvent("avs-language-change", { detail: { language: lang } }));
        };

        const saveSelectedDirectory = async (selected, imported=false) => {
                if (!selected) return;
                const t = tr(lang);
                refs.status.textContent = t.savingPath;
                try {
                    const result = await jsonFetch("/avs/library/config", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ library_path: selected }),
                    });
                    setWidget(node, "library_path", result.library_path);
                    refs.pathText.dataset.hasPath = "1";
                    refs.pathText.textContent = result.library_path;
                    if (imported) {
                        refs.status.textContent=t.scanning;
                        await jsonFetch("/avs/library/scan", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({library_path:result.library_path})});
                    }
                    toast(t.pathSelected);
                    await refreshNodeSummary(node, refs, lang);
                } catch (e) {
                    toast(e.message, true);
                }
        };
        refs.chooseBtn.onclick = () => {
            chooseLibraryDirectory({request:jsonFetch,nativePicker:refs.nativePicker,
                initialPath:findWidget(node,"library_path")?.value || "",lang,
                onSelect:saveSelectedDirectory,onProgress:message=>{refs.status.textContent=message;}})
                .catch(error=>toast(error.message,true));
        };
        refs.serverBtn.onclick=()=>openDirectoryBrowser(findWidget(node,"library_path")?.value || "",saveSelectedDirectory,lang);

        refs.openBtn.onclick = () => window.open("/avs/library/ui", "_blank", "noopener,noreferrer");

        refs.scanBtn.onclick = async () => {
            const t = tr(lang);
            const path = findWidget(node, "library_path")?.value || "";
            if (!path) return toast(t.chooseFirst, true);
            refs.scanBtn.disabled = true;
            refs.status.textContent = t.scanning;
            try {
                const result = await jsonFetch("/avs/library/scan", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ library_path: path }),
                });
                toast(t.scanDone(result.scanned));
                await refreshNodeSummary(node, refs, lang);
            } catch (e) {
                toast(e.message, true);
                refs.status.textContent = t.scanFailed;
            } finally {
                refs.scanBtn.disabled = false;
            }
        };

        window.addEventListener("avs-language-change", async (event) => {
            const next = event.detail?.language;
            if (!next || next === lang) return;
            lang = next;
            refs.languageSelect.value = lang;
            setWidget(node, "language", lang === "en-US" ? "English" : "中文");
            updateNodeLanguage(node, lang, refs);
            await refreshNodeSummary(node, refs, lang);
        });
    },
});
