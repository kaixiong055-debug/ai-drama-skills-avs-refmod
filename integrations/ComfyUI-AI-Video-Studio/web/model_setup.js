// Check locally before submitting a GPU job. Downloads are opened only by a user click.
export async function checkModels(app, api, nodeId = null, scope = null) {
  const graph = (await app.graphToPrompt()).output;
  if (scope !== null && graph[String(nodeId)]) graph[String(nodeId)].inputs.generation_scope = scope;
  if (!Object.values(graph).some(n => n.class_type === "AVSDirectorStudio")) return {ready:true,nodes:[]};
  const response = await api.fetchApi("/avs/models/preflight", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify({prompt:graph,node_id:nodeId})
  });
  if (!response.ok) throw new Error("模型检查暂不可用，请重启ComfyUI加载更新插件后重新检测。");
  return response.json();
}

function text(tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
}

export function renderModelPlan(container, plan, refresh) {
  container.replaceChildren();
  container.style.display = "block";
  container.append(text("b", plan.ready ? "模型已就绪，可以生成" : "先补齐模型，再开始生成"));
  for (const issue of plan.issues || []) container.append(text("p", issue));
  for (const item of plan.missing || []) {
    const row = text("div", "");
    Object.assign(row.style,{marginTop:"10px",padding:"8px",border:"1px solid #665529",borderRadius:"5px"});
    row.append(text("b", `${item.label}${item.size_hint ? "（"+item.size_hint+"）" : ""}`));
    for (const value of [item.filename, "保存到："+item.directory,
                        item.selected && item.selected!==item.filename ? "当前选择的文件未找到："+item.selected : "", item.note]) {
      if (!value) continue;
      const line = text("div",value);
      Object.assign(line.style,{marginTop:"4px",overflowWrap:"anywhere",userSelect:"text"});
      row.append(line);
    }
    if (item.download_url) {
      const link = text("a","打开下载地址");
      link.href=item.download_url;link.target="_blank";link.rel="noopener noreferrer";
      Object.assign(link.style,{color:"#82baff",display:"inline-block",marginTop:"6px"});
      row.append(link);
      const copy = text("button","复制下载链接");
      copy.style.marginLeft="12px";
      copy.onclick=async()=>{
        try {await navigator.clipboard.writeText(item.download_url);copy.textContent="已复制";}
        catch {copy.textContent="请复制下方链接";row.append(text("div",item.download_url));}
      };
      row.append(copy);
    } else row.append(text("p","该自定义文件未收录下载链接，请从原作者发布页面获取。"));
    container.append(row);
  }
  const again=text("button","已放入模型目录，重新检测");
  again.style.marginTop="9px";
  again.onclick=refresh;
  container.append(again);
}

export function applyModelPlans(app, result) {
  for (const plan of result.nodes || []) {
    const node=app.graph?.getNodeById?.(plan.node_id);
    node?._avsModelSetup?.(plan);
  }
}

export function installModelPreflight(app, api) {
  if (app._avsModelPreflightInstalled) return;
  app._avsModelPreflightInstalled=true;
  const queue=app.queuePrompt;
  app.queuePrompt=async function(...args) {
    if (!(app.graph?._nodes || []).some(node => node.comfyClass==="AVSDirectorStudio" || node._avsModelSetup)) {
      return queue.apply(this,args);
    }
    let result;
    try {result=await checkModels(app,api);}
    catch (error) {
      for (const node of app.graph?._nodes || []) {
        if (node._avsModelSetup) node._avsModelSetup({ready:false,missing:[],issues:[error.message]});
      }
      return;
    }
    applyModelPlans(app,result);
    if (!result.ready) return;
    return queue.apply(this,args);
  };
}
