import { app } from "../../scripts/app.js";

const COLORS = {
  panel: "#111827",
  border: "#334155",
  title: "#f8fafc",
  text: "#cbd5e1",
  muted: "#94a3b8",
  accent: "#6366f1",
};

function addInfoPanel(node) {
  if (node.__avsH3InfoAdded) return;
  node.__avsH3InfoAdded = true;
  const widget = node.addDOMWidget("avs_h3_info", "div", document.createElement("div"), {
    serialize: false,
    hideOnZoom: false,
  });
  const el = widget.element;
  Object.assign(el.style, {
    boxSizing: "border-box",
    width: "100%",
    padding: "11px 12px",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "10px",
    background: COLORS.panel,
    color: COLORS.text,
    fontSize: "12px",
    lineHeight: "1.55",
    marginBottom: "4px",
  });
  el.innerHTML = `
    <div style="font-weight:800;color:${COLORS.title};margin-bottom:4px">作用：把 @资源引用直接变成 H3 可用的生成条件</div>
    <div style="color:${COLORS.muted}">只会在执行时读取本次真正引用的素材，不会把整个永久资源库加载到显存。</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
      <span style="padding:3px 7px;border-radius:999px;background:#1e293b">自动识别 R2V / T2V</span>
      <span style="padding:3px 7px;border-radius:999px;background:#1e293b">图片≤9</span>
      <span style="padding:3px 7px;border-radius:999px;background:#1e293b">视频≤3</span>
      <span style="padding:3px 7px;border-radius:999px;background:#1e293b">音频≤3</span>
    </div>`;
  widget.computeSize = (width) => [width, 112];
}

function updateVisibility(node) {
  const byName = Object.fromEntries((node.widgets || []).map(w => [w.name, w]));
  const custom = byName.resolution?.value === "自定义";
  for (const name of ["custom_width", "custom_height"]) {
    const w = byName[name];
    if (!w) continue;
    w.hidden = !custom;
    w.type = custom ? (w.__avsOriginalType || w.type || "number") : "hidden";
    if (!w.__avsOriginalType && custom) w.__avsOriginalType = w.type;
  }
  node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "AI.Video.Studio.H3SmartGenerator",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== "AVSH3SmartGenerator") return;
    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = originalCreated?.apply(this, arguments);
      this.title = "AI视频工作室｜H3智能生成";
      this.size = [620, Math.max(this.size?.[1] || 420, 500)];
      addInfoPanel(this);
      const resolution = (this.widgets || []).find(w => w.name === "resolution");
      if (resolution) {
        const oldCb = resolution.callback;
        resolution.callback = (...args) => {
          oldCb?.apply(resolution, args);
          updateVisibility(this);
        };
      }
      setTimeout(() => updateVisibility(this), 0);
      return result;
    };
  },
});
