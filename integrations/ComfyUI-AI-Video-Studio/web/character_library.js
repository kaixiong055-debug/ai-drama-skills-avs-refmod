// Actor management is inside the director. GPU work is queued through ComfyUI.
const clone = value => JSON.parse(JSON.stringify(value));
const jobs = new Map();
const activePolls = new Set();
const key = "avs-character-preparation-jobs-v1";
try { for (const pair of JSON.parse(localStorage.getItem(key) || "[]")) jobs.set(...pair); } catch {}
function saveJobs() { try { localStorage.setItem(key, JSON.stringify([...jobs])); } catch {} }
const labels = {ready:"可使用", stale:"需要更新", pending:"未准备", empty:"未上传"};
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export function createCharacterLibrary({getDoc, getShot, persist, repaint, request, upload, notify}) {
  let records = [], vaes = [], available = true, overlay = null, disposed = false;
  let selected = "", draft = null, errorBox = null, panel = null, list = null, submitting = false;
  let globalWardrobes = [], globalWardrobeStatus = null, wardrobeOverlay = null;
  const el = (tag, text = "", style = {}) => {
    const n = document.createElement(tag); n.textContent = text;
    Object.assign(n.style, style); return n;
  };
  const button = (text, fn) => {
    const b = el("button", text, {background:"#173b61",color:"#eef3f8",border:"1px solid #3d7cc1",borderRadius:"6px",padding:"7px 10px",cursor:"pointer"});
    b.type = "button";
    b.onclick = async () => { b.disabled = true; try { await fn(); } catch(e) { message(e.message || e); } finally { b.disabled = false; } };
    return b;
  };
  const input = value => {
    const i = el("input", "", {background:"#0b111b",color:"#eef3f8",border:"1px solid #3b4656",borderRadius:"5px",padding:"7px",minWidth:"0"}); i.value = value; return i;
  };
  const select = (options, value, change) => {
    const s = el("select", "", {background:"#111b29",color:"#eef3f8",padding:"6px",border:"1px solid #3b4656",borderRadius:"5px",minWidth:"0"});
    for(const [v,label] of options) { const o = el("option",label); o.value=v; s.append(o); }
    s.value = value; s.onchange = () => { try { change(s.value); } catch(e) { message(e.message || e); repaint(); } }; return s;
  };
  function message(text) { if(errorBox) errorBox.textContent = String(text); else notify(String(text),"warn",7000); }
  function cast() { return getDoc().character_cast ||= []; }
  function actor(id) { return records.find(c => c.id === id); }
  function status(c) { return jobs.has(c.id) ? "排队 / 准备中" : labels[c.status] || "未准备"; }
  const imageUrl = r => `/view?${new URLSearchParams({filename:r.filename,subfolder:r.subfolder || "",type:"input"})}`;
  async function refresh() {
    const data = await request("/avs/characters");
    records=data.characters; vaes=data.vaes; available=data.refmod_available;
    repaint();
    return records;
  }
  async function refreshGlobalWardrobes() {
    const data = await request("/avs/wardrobes");
    globalWardrobes = data.wardrobes || []; globalWardrobeStatus = data.status || null;
    return globalWardrobes;
  }
  function globalCoverUrl(w) { return `/avs/wardrobes/image/${encodeURIComponent(w.id)}/0?v=${Number(w.revision||0)}`; }
  async function bindGlobalWardrobe(wid) {
    if(!draft) throw new Error("请先选择一个人物。");
    const data=await request("/avs/wardrobes/materialize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:wid})});
    const w=data.wardrobe;
    let local=(draft.wardrobes||[]).find(x=>x.global_wardrobe_id===w.id);
    if(local){local.name=w.name;local.refs=data.refs;local.global_revision=w.revision;}
    else{draft.wardrobes ||= [];draft.wardrobes.push({id:crypto.randomUUID().replaceAll("-",""),name:w.name,refs:data.refs,global_wardrobe_id:w.id,global_revision:w.revision});}
    drawEditor();
    message(`已把全局造型【${w.name}】绑定到 ${draft.name}。保存人物资料并准备参考后即可使用。`);
  }
  async function saveWardrobeToGlobal(w) {
    if(!w?.refs?.length) throw new Error("这个造型还没有图片，不能保存到全局造型库。");
    const payload={id:w.global_wardrobe_id||undefined,name:w.name,refs:w.refs};
    const data=await request("/avs/wardrobes/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
    w.global_wardrobe_id=data.wardrobe.id;w.global_revision=data.wardrobe.revision;
    await refreshGlobalWardrobes();drawEditor();
    message(`造型【${w.name}】已保存到全局造型库。`);
  }
  function closeWardrobeLibrary(){wardrobeOverlay?.remove();wardrobeOverlay=null;}
  async function openGlobalWardrobeLibrary(){
    closeWardrobeLibrary();
    await refreshGlobalWardrobes();
    wardrobeOverlay=el("div","",{position:"fixed",inset:"8vh 8vw",zIndex:"100010",background:"#0b1018",color:"#eef3f8",border:"1px solid #50647e",borderRadius:"10px",padding:"16px",boxShadow:"0 18px 90px #000e",display:"flex",flexDirection:"column"});
    const head=el("div","",{display:"flex",gap:"8px",alignItems:"center",flexWrap:"wrap"});
    head.append(el("b","全局造型库",{fontSize:"18px"}),button("刷新",async()=>{await refreshGlobalWardrobes();closeWardrobeLibrary();await openGlobalWardrobeLibrary();}),button("关闭",closeWardrobeLibrary));
    const pathRow=el("div","",{display:"grid",gridTemplateColumns:"1fr auto auto auto",gap:"7px",margin:"12px 0"});
    const pathInput=input(globalWardrobeStatus?.root||"");pathInput.placeholder="全局造型库目录（推荐 OneDrive / Dropbox / NAS / 同步盘）";
    const savePath=button("使用此目录",async()=>{const d=await request("/avs/wardrobes/root",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:pathInput.value})});globalWardrobeStatus=d.status;globalWardrobes=d.wardrobes||[];closeWardrobeLibrary();await openGlobalWardrobeLibrary();});
    const resourcePath=button("放到永久资源库",async()=>{const d=await request("/avs/wardrobes/use-resource-library",{method:"POST"});globalWardrobeStatus=d.status;globalWardrobes=d.wardrobes||[];closeWardrobeLibrary();await openGlobalWardrobeLibrary();});
    const choosePath=button("选择目录",async()=>{const st=await request("/avs/library/status");if(!st.native_picker)throw new Error("当前不是本机 Windows 访问，请直接在左侧填写服务器/同步盘目录。");const d=await request("/avs/library/pick-directory",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({initial_path:pathInput.value||st.config?.library_path||""})});if(!d.cancelled&&d.path)pathInput.value=d.path;});
    pathRow.append(pathInput,choosePath,savePath,resourcePath);
    const statusText=globalWardrobeStatus?.portable?"✓ 已使用独立/永久目录。若该目录位于 OneDrive / Dropbox / NAS / 共享盘，另一台电脑选择同一同步目录后即可继续绑定。":"⚠ 当前使用本机回退目录；跨电脑使用请把全局造型库切到 OneDrive / Dropbox / NAS / 共享盘。";
    const hint=el("div",statusText,{fontSize:"12px",color:globalWardrobeStatus?.portable?"#8fd5a6":"#f1c77a",marginBottom:"10px",lineHeight:"1.55"});
    const grid=el("div","",{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(210px,1fr))",gap:"10px",overflow:"auto",paddingRight:"4px"});
    if(!globalWardrobes.length)grid.append(el("div","全局造型库还是空的。可以先在人物里的某个造型点击“保存到全局库”，以后任何人物都能直接绑定。",{color:"#a0b1c5",fontSize:"13px",lineHeight:"1.6"}));
    for(const w of globalWardrobes){
      const card=el("div","",{border:"1px solid #33465f",borderRadius:"8px",padding:"8px",background:"#0e1723"});
      if(w.ref_count){const im=el("img","",{width:"100%",height:"150px",objectFit:"contain",background:"#070b11",borderRadius:"5px"});im.src=globalCoverUrl(w);card.append(im);}
      card.append(el("b",w.name,{display:"block",marginTop:"7px"}),el("div",`${w.ref_count||0} 张参考｜版本 ${w.revision||1}`,{fontSize:"11px",color:"#a0b1c5",margin:"4px 0 7px"}));
      const actions=el("div","",{display:"flex",gap:"6px",flexWrap:"wrap"});
      const bind=button(draft?`绑定给 ${draft.name}`:"先选择人物",async()=>{await bindGlobalWardrobe(w.id);closeWardrobeLibrary();});bind.disabled=!draft;actions.append(bind);
      const del=button("删除全局造型",async()=>{if(!confirm(`确定从全局造型库删除【${w.name}】？已经绑定到人物的本地副本不会被删除。`))return;await request(`/avs/wardrobes/${encodeURIComponent(w.id)}`,{method:"DELETE"});await refreshGlobalWardrobes();closeWardrobeLibrary();await openGlobalWardrobeLibrary();});del.style.background="#54262d";del.style.borderColor="#9d4a54";actions.append(del);card.append(actions);grid.append(card);
    }
    wardrobeOverlay.append(head,pathRow,hint,grid);document.body.append(wardrobeOverlay);
  }
  function close() { closeWardrobeLibrary();overlay?.remove(); overlay=null; errorBox=null; panel=null; list=null; draft=null; }
  function markChanged() { persist(); repaint(); }
  function assignToProject(id) {
    if (!cast().some(x => x.character_id === id)) cast().push({character_id:id,role:"配角"});
    markChanged(); drawList();
  }
  function removeFromProject(id) {
    // Do not leave invisible bindings on other shots.
    for (const shot of getDoc().shots || []) {
      for (const row of [...(shot.character_selections || [])]) if(row.character_id===id) release(shot,row);
      if (shot.character_selections) shot.character_selections=shot.character_selections.filter(r=>r.character_id!==id);
    }
    getDoc().character_cast=cast().filter(x=>x.character_id!==id);
    markChanged(); drawList();
  }
  function drawList() {
    if(!list) return; list.replaceChildren();
    list.append(el("b","人物库"),el("p","人物资料跨项目复用。本剧角色和每段出场名单分别保存。",{color:"#a0b1c5",fontSize:"12px",lineHeight:"1.6"}));
    for(const c of records) {
      const box=el("div","",{padding:"10px",marginBottom:"8px",border:`1px solid ${selected===c.id?"#62a8ff":"#303947"}`,borderRadius:"7px"});
      const name=button(`${c.name} · ${status(c)}`,()=>{selected=c.id;draft=clone(c);drawList();drawEditor();});
      box.append(name);
      const entry=cast().find(x=>x.character_id===c.id);
      if(entry) {
        const row=el("div","",{display:"flex",gap:"5px",marginTop:"8px",flexWrap:"wrap"});
        row.append(select(["男主","女主","配角","其他"].map(x=>[x,x]),entry.role,v=>{entry.role=v;markChanged();}),button("移出本剧",()=>removeFromProject(c.id))); box.append(row);
      } else box.append(button("＋ 加入本剧",()=>assignToProject(c.id)));
      list.append(box);
    }
    list.append(button("＋ 新建人物",async()=>{
      const r=await request("/avs/characters",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:"新人物",refs:[],wardrobes:[],resolution:512})});
      await refresh(); selected=r.character.id;draft=clone(r.character);assignToProject(selected);drawEditor();
    }));
  }
  async function saveDraft() {
    if(!draft) return;
    const r=await request("/avs/characters",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(draft)});
    draft=clone(r.character);await refresh();drawList(); return r.character;
  }
  function refsEditor(refs, identity=false) {
    const wrap=el("div","",{display:"grid",gridTemplateColumns:"repeat(4,minmax(90px,1fr))",gap:"9px",margin:"10px 0"});
    for(let index=0;index<4;index++) {
      const ref=refs[index], card=el("div","",{border:"1px solid #303947",borderRadius:"6px",padding:"6px",minHeight:"130px"});
      const identityLabels=["清晰正脸（必填）","补充角度（侧脸 / 3⁄4 / 四宫格）","表情参考 1（可选）","表情参考 2（可选）"];
      card.append(el("div",identity?identityLabels[index]:`补充参考 ${index + 1}`,{fontSize:"12px",marginBottom:"5px"}));
      if(ref) { const im=el("img","",{width:"100%",height:"110px",objectFit:"contain",background:"#070b11"});im.src=imageUrl(ref);card.append(im); }
      const choose=button(ref?"更换图片":"选择图片",async()=>{
        // upload invokes the native file picker directly; no library dialog.
        const r=await upload();if(!r)return;
        if(index>refs.length) { message("请先上传前面的参考图片。");return; }
        refs[index]=r;drawEditor();
      });
      choose.disabled=index>refs.length;card.append(choose);
      if(ref && (!identity || index>0 || refs.length===1)) card.append(button("移除",()=>{refs.splice(index,1);drawEditor();}));
      wrap.append(card);
    }
    return wrap;
  }
  async function pollJob(cid,promptId) {
    if(activePolls.has(promptId))return;
    activePolls.add(promptId);
    try {
      while(!disposed) {
        await sleep(1800);
        const history=await request(`/history/${encodeURIComponent(promptId)}`);
        const h=history[promptId];
        if(h) {
          jobs.delete(cid);saveJobs();
          if(h.status?.status_str!=="success") {
            const failure=h.status?.messages?.find(x=>x[0]==="execution_error");
            throw new Error(failure?.[1]?.exception_message || "人物准备已中断或失败，请检查队列后重试。");
          }
          await refresh();drawList();
          // Keep any unsaved editor changes. Only refresh cache metadata.
          if(draft?.id===cid) {draft.prepared=actor(cid)?.prepared;draft.component_status=actor(cid)?.component_status;draft.status=actor(cid)?.status;drawEditor();}
          notify("人物参考已准备，可以在镜头中选用。","info",5000);return;
        }
        const queue=await request("/queue");
        if(![...(queue.queue_running||[]),...(queue.queue_pending||[])].some(x=>x[1]===promptId)) {
          jobs.delete(cid);saveJobs();throw new Error("准备任务已取消或队列已重启，可重新点击准备。");
        }
      }
    } catch(e) {jobs.delete(cid);saveJobs();message(e.message);await refresh().catch(()=>{});drawList();}
    finally {activePolls.delete(promptId);}
  }
  function drawEditor() {
    if(!panel)return;panel.replaceChildren();
    if(!draft) {panel.append(el("p","选择或新建人物，然后上传你已有的图片。"));return;}
    const name=input(draft.name);name.placeholder="人物姓名";name.oninput=()=>draft.name=name.value;
    panel.append(el("b","人物资料"),el("p","先放一张清晰正脸，再按需要补充侧脸 / 3⁄4 / 四宫格。表情参考直接放在人物资料的第3、4槽，推荐使用同一人物的表情四宫格；服装不要放这里，仍放到下方对应造型中。修改后请保存并重新准备人物参考。",{color:"#a0b1c5",fontSize:"12px"}),name);
    panel.append(refsEditor(draft.refs,true));
    panel.append(el("div","参考精度"),select([[512,"标准 · 推荐起步"],[768,"清晰 · 较多参考占用"],[1024,"高精度 · 更占显存"]],draft.resolution,v=>draft.resolution=Number(v)));
    const wardrobeHead=el("div","",{display:"flex",alignItems:"center",gap:"8px",flexWrap:"wrap",marginTop:"12px"});
    wardrobeHead.append(el("h3","服装与造型",{margin:"0"}),button("全局造型库",openGlobalWardrobeLibrary),button("＋ 从全局造型库绑定",openGlobalWardrobeLibrary));panel.append(wardrobeHead);
    panel.append(el("p","常用造型保存一次即可跨人物、跨项目复用；把全局库目录放到 OneDrive / Dropbox / NAS / 同步盘后，换电脑也能重新绑定，不需要逐张选图。",{color:"#8fa7c1",fontSize:"12px",lineHeight:"1.6"}));
    for(const w of draft.wardrobes) {
      const group=el("div","",{padding:"10px",border:`1px solid ${w.global_wardrobe_id?"#496f9a":"#303947"}`,borderRadius:"8px",marginBottom:"10px"});
      const titleRow=el("div","",{display:"flex",gap:"7px",alignItems:"center",flexWrap:"wrap"});
      const title=input(w.name);title.placeholder="例如：西装 / 睡衣";title.oninput=()=>w.name=title.value;
      titleRow.append(title,el("span",`  ${labels[draft.component_status?.[w.id]] || "未准备"}`,{color:"#a0b1c5"}));
      if(w.global_wardrobe_id)titleRow.append(el("span","全局库",{fontSize:"10px",padding:"3px 6px",borderRadius:"10px",background:"#193553",color:"#8fc6ff"}));
      group.append(titleRow,refsEditor(w.refs));
      const actions=el("div","",{display:"flex",gap:"7px",flexWrap:"wrap"});
      actions.append(button(w.global_wardrobe_id?"更新到全局库":"保存到全局库",()=>saveWardrobeToGlobal(w)));
      actions.append(button("移除此造型",()=>{draft.wardrobes=draft.wardrobes.filter(x=>x.id!==w.id);drawEditor();}));group.append(actions);panel.append(group);
    }
    const wardrobeActions=el("div","",{display:"flex",gap:"8px",flexWrap:"wrap"});
    wardrobeActions.append(button("＋ 添加本地造型",()=>{draft.wardrobes.push({id:crypto.randomUUID().replaceAll("-",""),name:"新造型",refs:[]});drawEditor();}),button("＋ 从全局造型库绑定",openGlobalWardrobeLibrary));panel.append(wardrobeActions);
    const controls=el("div","",{display:"flex",gap:"8px",alignItems:"center",flexWrap:"wrap",marginTop:"20px"});
    let vae=vaes[0]||"";const vaeSelect=select(vaes.map(x=>[x,x]),vae,v=>vae=v);
    const enqueue=async(forceRebuild=false)=>{
      if(submitting)return;
      submitting=true;drawEditor();
      try {
        const c=await saveDraft();
        const r=await request("/avs/characters/prepare",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({character_id:c.id,vae_name:vae,force_rebuild:forceRebuild})});
        if(r.cached){message("参考未变化，已复用现有结果。");return;}
        const queued=await request("/prompt",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:r.prompt})});
        jobs.set(c.id,queued.prompt_id);saveJobs();drawList();
        message(forceRebuild?"已排队；任务开始时删除本人物旧参考，再重新生成。":"人物参考已进入准备队列。");
        void pollJob(c.id,queued.prompt_id);
      } finally {submitting=false;drawEditor();}
    };
    const prep=button(jobs.has(draft.id)?"正在准备…":"保存并准备人物参考",()=>enqueue());
    const rebuild=button("删除旧参考并重新生成",()=>enqueue(true));
    rebuild.style.background="#633c20";rebuild.style.borderColor="#b37c46";
    rebuild.title="清理当前人物全部旧身份与造型 RefMod，再按已保存资料重新准备；保留原始图片。";
    prep.disabled=rebuild.disabled=submitting||jobs.has(draft.id)||!available||!vae;
    controls.append(button("保存资料",async()=>{await saveDraft();message("已保存。更换的参考需重新准备，未变化的参考会复用。");drawEditor();}),vaeSelect,prep,rebuild);
    panel.append(el("p","重新生成会删除本人物的旧身份与造型参考文件，保留上传图片；若任务失败，可再次准备。",{color:"#d9b38a",fontSize:"12px"}));
    panel.append(controls,el("p",available?"准备任务进入 ComfyUI 队列；使用本地 H3 视频 VAE 编码上传图片。图片不变时复用缓存。":"缺少 RefMod 插件，请安装 ComfyUI-MiniMaxH3Mod 并重启。",{color:"#a0b1c5",fontSize:"12px",lineHeight:"1.7"}));
  }
  async function open() {
    close();
    overlay=el("div","",{position:"fixed",inset:"4vh 4vw",zIndex:"100000",background:"#0b1018",color:"#eef3f8",border:"1px solid #44536a",borderRadius:"10px",padding:"16px",fontFamily:"system-ui,sans-serif",display:"flex",flexDirection:"column",boxShadow:"0 15px 80px #000d"});
    const head=el("div","",{display:"flex",gap:"12px",alignItems:"center"});
    head.append(el("b","人物库与本剧演员",{fontSize:"18px"}),button("全局造型库",openGlobalWardrobeLibrary),button("刷新",async()=>{await refresh();drawList();}),button("关闭",close));
    errorBox=el("div","",{color:"#f5c675",whiteSpace:"pre-wrap",fontSize:"13px",padding:"10px 0"});
    const body=el("div","",{display:"grid",gridTemplateColumns:"260px minmax(400px,1fr)",gap:"18px",overflow:"auto",flex:"1"});
    list=el("div","",{overflow:"auto"});panel=el("div","",{overflow:"auto",paddingRight:"8px"});body.append(list,panel);overlay.append(head,errorBox,body);document.body.append(overlay);
    try {await refresh();selected=actor(selected)?.id || records[0]?.id || "";draft=actor(selected)?clone(actor(selected)):null;drawList();drawEditor();for(const [cid,pid] of jobs)void pollJob(cid,pid);}
    catch(e){message(`人物库暂不可用：${e.message}。更新插件后请重启ComfyUI后端。`);}
  }
  function release(shot,row) {
    const i=row.picture_slot-1;
    if(shot.image_slots?.[i]?.character_id===row.character_id) shot.image_slots[i]=row.previous_slot || {slot:i+1};
  }
  function claim(shot,row,slot) {
    const c=actor(row.character_id),ref=c?.refs?.[0];if(!ref)throw new Error("该人物还没有正脸图片，请先在人物库上传。");
    const old=shot.image_slots?.[slot-1] || {slot};row.previous_slot=clone(old);row.picture_slot=slot;
    shot.image_slots ||= [];shot.image_slots[slot-1]={slot,character_id:c.id,token:"",asset_id:"",name:`${c.name}｜脸部身份`,local_path:ref.path,local_filename:ref.filename,local_subfolder:ref.subfolder,local_type:"input",group_name:"人物库"};
  }
  function renderShot(container,shot) {
    const box=el("div","",{border:"1px solid #425c7b",background:"#101b2a",padding:"9px",borderRadius:"7px",marginBottom:"10px"});
    box.append(el("b","本段出场人物"),button("人物库 / 设置演员",open));
    const rows=shot.character_selections || [];
    for(const row of rows) {
      const c=actor(row.character_id), entry=cast().find(x=>x.character_id===row.character_id);
      const item=el("div","",{display:"grid",gap:"5px",marginTop:"10px",paddingTop:"8px",borderTop:"1px solid #303947"});
      item.append(el("span",`${entry?.role||"人物"} · ${c?.name||"人物资料缺失"} · ${c?status(c):"请检查人物库"}`));
      const wardrobeOptions=[["","服装按提示词（只用身份）"],...(c?.wardrobes||[]).map(w=>[w.id,w.name])];
      if(row.wardrobe_id && !wardrobeOptions.some(x=>x[0]===row.wardrobe_id))wardrobeOptions.push([row.wardrobe_id,"原造型已移除，请重选"]);
      item.append(select(wardrobeOptions,row.wardrobe_id||"",v=>{row.wardrobe_id=v;markChanged();}));
      item.append(select(Array.from({length:9},(_,i)=>[i+1,`绑定 Picture ${i+1}`]),row.picture_slot,v=>{
        if(rows.some(x=>x!==row&&x.picture_slot===Number(v))){message("该槽位已分配给另一人物。");repaint();return;}
        if(!c?.refs?.[0])throw new Error("该人物还没有正脸图片，请先在人物库上传。");
        release(shot,row);claim(shot,row,Number(v));markChanged();
      }),button("移出本段",()=>{release(shot,row);shot.character_selections=rows.filter(x=>x!==row);markChanged();}));box.append(item);
    }
    const candidates=cast().filter(x=>!rows.some(r=>r.character_id===x.character_id));
    if(candidates.length) {
      let cid=candidates[0].character_id;
      box.append(select(candidates.map(x=>[x.character_id,`${x.role} · ${actor(x.character_id)?.name||"资料缺失"}`]),cid,v=>cid=v),button("＋ 加入本段",()=>{
        if(rows.length>=4)throw new Error("单段最多4位人物。");
        const slot=Array.from({length:9},(_,i)=>i+1).find(n=>!rows.some(r=>r.picture_slot===n)&&!(shot.image_slots?.[n-1]?.local_path||shot.image_slots?.[n-1]?.asset_id||shot.image_slots?.[n-1]?.token));
        if(!slot)throw new Error("Picture槽位已满，请先清理一个人物槽位后再加入。");
        const row={character_id:cid,wardrobe_id:"",picture_slot:slot};claim(shot,row,slot);shot.character_selections=[...rows,row];markChanged();
      }));
    } else if(!cast().length)box.append(el("p","先在人物库上传参考图，并设置本剧男主、女主或配角。",{fontSize:"11px",color:"#a0b1c5"}));
    box.append(el("p","造型选择需与本段提示词一致。空镜不选择人物。",{fontSize:"10px",color:"#a0b1c5"}));container.append(box);
  }
  return {open,renderShot,refresh,dispose(){disposed=true;close();}};
}
