import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EXT = "AI.Video.Studio.TimelineDirector.v081";
const C = {
  bg:"#0a0d12", panel:"#111720", panel2:"#0e131b", border:"#303845", text:"#e8edf5",
  muted:"#8d98a8", accent:"#67d982", accent2:"#f2c94c", danger:"#ef6262", blue:"#5aa7ff",
};

const $ = (tag, text="") => { const e=document.createElement(tag); if(text)e.textContent=text; return e; };
const css = (e,o)=>{Object.assign(e.style,o); return e;};
const findW=(n,k)=>n.widgets?.find(w=>w.name===k);
const setW=(n,k,v)=>{const w=findW(n,k); if(!w)return; w.value=v; w.callback?.(v); n.graph?.setDirtyCanvas?.(true,true);};
const hideW=(w)=>{
  if(!w)return;
  if(!w.__avsHidden){
    w.__avsHidden=true;
    w.__avsOldType=w.type;
    w.__avsOldComputeSize=w.computeSize;
  }
  // Canvas widgets.
  w.hidden=true;
  w.type="hidden";
  w.computeSize=()=>[0,0];
  // Nodes 2.0 / DOM widgets. ComfyUI may recreate these wrappers on configure/resize,
  // so this function is intentionally safe to call repeatedly.
  const el=w.inputEl || w.element || w.el || null;
  const hosts=[];
  if(el){
    hosts.push(el);
    if(el.parentElement)hosts.push(el.parentElement);
    try{const h=el.closest?.(".dom-widget");if(h)hosts.push(h);}catch(_){ }
  }
  for(const h of hosts){
    if(!h?.style)continue;
    h.style.display="none";
    h.style.height="0px";
    h.style.minHeight="0px";
    h.style.maxHeight="0px";
    h.style.margin="0";
    h.style.padding="0";
    h.style.border="0";
    h.style.overflow="hidden";
    h.style.pointerEvents="none";
  }
};
function collapseNativeWidgets(node){
  for(const w of node.widgets||[]){
    if(w?.name==="avs_timeline_director_ui")continue;
    hideW(w);
  }
  // Extra fallback for multiline DOM hosts that ComfyUI Nodes 2.0 can recreate
  // after the widget object was already marked hidden.
  const candidates=[...document.querySelectorAll?.(".dom-widget")||[]];
  for(const host of candidates){
    const ta=host.querySelector?.("textarea");
    const inp=host.querySelector?.("input");
    const sel=host.querySelector?.("select");
    const field=ta||inp||sel;
    if(!field)continue;
    const raw=(field.value||"").toString();
    // Only collapse hosts that belong to our hidden state/settings widgets. The
    // timeline JSON has a distinctive JSON prefix and the old hidden fields live
    // in the same director node DOM stack. Widget-level hiding above remains the
    // primary path; this is only a Nodes 2.0 safety net.
    if(raw.startsWith('{"version"') || field.dataset?.avsHidden==="1"){
      host.style.display="none";
      host.style.height="0px";
      host.style.minHeight="0px";
      host.style.maxHeight="0px";
      host.style.margin="0";
      host.style.padding="0";
      host.style.overflow="hidden";
      host.style.pointerEvents="none";
    }
  }
}
const opts=(w)=>w?.options?.values || w?.options || [];
function mkInput(type="text"){const e=$("input");e.type=type;return css(e,{background:"#090d13",color:C.text,border:`1px solid ${C.border}`,borderRadius:"5px",padding:"5px 7px",fontSize:"11px",boxSizing:"border-box",minWidth:0});}
function mkSelect(){return css($("select"),{background:"#090d13",color:C.text,border:`1px solid ${C.border}`,borderRadius:"5px",padding:"5px 7px",fontSize:"11px",minWidth:0});}
function mkTa(rows=4){const e=$("textarea");e.rows=rows;return css(e,{background:"#090d13",color:C.text,border:`1px solid ${C.border}`,borderRadius:"5px",padding:"7px",fontSize:"11px",lineHeight:"1.4",resize:"vertical",boxSizing:"border-box",width:"100%"});}
function btn(text, kind="normal"){const e=$("button",text); const bg=kind==="primary"?"#174b29":kind==="danger"?"#471f25":"#171d26"; const border=kind==="primary"?"#3b9a58":kind==="danger"?"#9a3d48":C.border; return css(e,{background:bg,color:C.text,border:`1px solid ${border}`,borderRadius:"5px",padding:"5px 9px",fontSize:"11px",cursor:"pointer",fontWeight:"700"});}
function label(text,control){const l=$("label");css(l,{display:"flex",flexDirection:"column",gap:"3px",color:C.muted,fontSize:"10px",minWidth:0});l.append($("span",text),control);return l;}
function readJson(node){try{return JSON.parse(findW(node,"timeline_json")?.value||"");}catch{return null;}}
function defaultShot(i=1){return {id:`shot-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,name:`镜头${i}`,duration:5,prompt:"",story_goal:"",character_refs:"",scene_refs:"",prop_refs:"",motion_refs:"",audio_refs:"",start_state:"",action:"人物完成一个清楚、可读的主要动作",emotion:"自然",end_state:"动作自然收住，并保留下一镜可继续的姿态",shot_size:"全景",camera_angle:"正面",camera_move:"固定",continuity:i===1?"独立镜头":"自动",dialogue:"",sound_notes:"",seed_mode:"随机",seed:0,inherit_previous_audio:false};}
function ensureDoc(node){let d=readJson(node);if(!d||!Array.isArray(d.shots)||!d.shots.length)d={version:1,shots:[defaultShot(1)]};return d;}
function saveDoc(node,doc){setW(node,"timeline_json",JSON.stringify(doc));}
function selectedIndex(node,doc){return Math.max(0,Math.min(Number(findW(node,"selected_index")?.value||0),doc.shots.length-1));}
function bindNative(node,name,control,kind="text"){
  const w=findW(node,name); if(!w)return;
  if(control.tagName==="SELECT"){for(const v of opts(w)){const o=$("option",String(v));o.value=String(v);control.append(o);}control.value=String(w.value??"");}
  else if(kind==="checkbox")control.checked=!!w.value; else control.value=w.value??"";
  control.addEventListener(kind==="checkbox"?"change":"input",()=>{let v=kind==="checkbox"?control.checked:control.value;if(kind==="number")v=Number(v);setW(node,name,v);});
}
function fieldSelect(values,value,onchange){const s=mkSelect();for(const v of values){const o=$("option",v);o.value=v;s.append(o);}s.value=value||values[0];s.onchange=()=>onchange(s.value);return s;}
async function refPreview(refs){if(!refs.trim())return {images:[],videos:[],audios:[],references:[]};try{const r=await api.fetchApi("/avs/reference/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:refs,max_images:9,max_videos:3,max_audios:3})});const j=await r.json();return j?.context||{images:[],videos:[],audios:[],references:[]};}catch{return {images:[],videos:[],audios:[],references:[]};}}
function refsFromShot(s){return [s.character_refs,s.scene_refs,s.prop_refs,s.motion_refs,s.audio_refs,s.prompt].filter(Boolean).join(" ");}

function build(node){
  collapseNativeWidgets(node);
  node.title="AI视频工作室｜导演时间线";
  node.size=[1180,780];
  node.resizable=true;
  const root=css($("div"),{height:"720px",overflow:"hidden",padding:"4px",boxSizing:"border-box",fontFamily:"Inter,system-ui,sans-serif",color:C.text,background:C.bg});
  const state={doc:ensureDoc(node),thumbCache:new Map(),groups:null};

  // Top toolbar
  const top=css($("div"),{display:"grid",gridTemplateColumns:"190px 135px 130px 110px 95px 1fr auto",gap:"6px",alignItems:"end",padding:"6px",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",marginBottom:"6px"});
  const project=mkInput(),ptype=mkSelect(),ratio=mkSelect(),res=mkSelect(),audio=mkSelect();
  bindNative(node,"project_name",project);bindNative(node,"project_type",ptype);bindNative(node,"aspect_ratio",ratio);bindNative(node,"resolution",res);bindNative(node,"audio_mode",audio);
  const dur=$("div");css(dur,{fontSize:"11px",color:C.accent,fontWeight:"700",padding:"6px"});
  const advanced=btn("高级设置");
  top.append(label("项目",project),label("类型",ptype),label("画面比例",ratio),label("清晰度",res),label("声音",audio),dur,advanced);
  root.append(top);

  // Timeline toolbar
  const bar=css($("div"),{display:"flex",gap:"6px",alignItems:"center",padding:"5px 6px",background:C.panel2,border:`1px solid ${C.border}`,borderRadius:"6px 6px 0 0"});
  const add=btn("+ 添加镜头","primary"), dup=btn("复制"), del=btn("删除","danger"), prev=btn("← 上一镜"), next=btn("下一镜 →"), compile=btn("刷新引用");
  const hint=css($("div","每个卡片就是一个 H3 片段；点击卡片后在下方编辑。"),{color:C.muted,fontSize:"10px",marginLeft:"auto"});
  bar.append(add,dup,del,prev,next,compile,hint);root.append(bar);

  const timeline=css($("div"),{position:"relative",display:"flex",gap:"5px",overflowX:"auto",height:"150px",padding:"22px 8px 9px",background:"#080b10",border:`1px solid ${C.border}`,borderTop:"0",borderRadius:"0 0 6px 6px",boxSizing:"border-box"});
  root.append(timeline);

  // Editor body
  const editor=css($("div"),{display:"grid",gridTemplateColumns:"250px minmax(360px,1fr) 250px",gap:"7px",height:"465px",marginTop:"7px"});
  const left=css($("div"),{background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"7px",overflow:"auto"});
  const mid=css($("div"),{background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"7px",overflow:"auto"});
  const right=css($("div"),{background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"7px",overflow:"auto"});
  editor.append(left,mid,right);root.append(editor);

  // Advanced overlay, still inside the node (not H5)
  const advPanel=css($("div"),{display:"none",position:"absolute",zIndex:50,right:"16px",top:"58px",width:"430px",maxHeight:"600px",overflow:"auto",background:"#10151d",border:`1px solid ${C.border}`,borderRadius:"7px",padding:"9px",boxShadow:"0 12px 35px #000b"});
  root.append(advPanel);
  advanced.onclick=()=>{advPanel.style.display=advPanel.style.display==="none"?"block":"none";};
  const advNames=[["visual_style","统一视觉风格"],["default_character_refs","默认角色引用"],["default_scene_refs","默认场景引用"],["default_prop_refs","默认道具引用"],["consistency","一致性"],["quality_preset","生成质量"],["lora_name","LoRA"],["lora_strength","LoRA强度"],["steps_override","Steps(0=自动)"],["cfg","CFG"],["sampler","采样器"],["scheduler","调度器"],["fl2va_model","FL2VA"],["ref2va_model","REF2VA"],["clip_model","CLIP"],["video_vae_model","Video VAE"],["audio_vae_model","Audio VAE"]];
  const ah=css($("div","高级设置"),{fontWeight:"800",marginBottom:"7px"});advPanel.append(ah);
  for(const [n,l] of advNames){const w=findW(node,n);if(!w)continue;const v=opts(w);let c;if(v?.length){c=mkSelect();bindNative(node,n,c);}else if(w.type==="toggle"){c=mkInput("checkbox");bindNative(node,n,c,"checkbox");}else{c=mkInput(n.includes("strength")||n==="cfg"||n.includes("steps")?"number":"text");bindNative(node,n,c,c.type==="number"?"number":"text");}c.style.width="100%";const lab=label(l,c);lab.style.marginBottom="6px";advPanel.append(lab);}

  function save(){saveDoc(node,state.doc);renderTimeline();renderEditor();updateDuration();}
  function updateDuration(){const t=state.doc.shots.reduce((a,s)=>a+Number(s.duration||5),0);dur.textContent=`${state.doc.shots.length} 镜｜${t.toFixed(1)}s｜约 ${Math.round(t*24)} 帧时间线`;}
  function setSel(i){i=Math.max(0,Math.min(i,state.doc.shots.length-1));setW(node,"selected_index",i);renderTimeline();renderEditor();}
  function patchShot(obj){const i=selectedIndex(node,state.doc);Object.assign(state.doc.shots[i],obj);saveDoc(node,state.doc);renderTimeline();updateDuration();}

  async function hydrateCard(card,shot){const refs=refsFromShot(shot);if(!refs.trim())return;let ctx=state.thumbCache.get(refs);if(!ctx){ctx=await refPreview(refs);state.thumbCache.set(refs,ctx);}const a=ctx.images?.[0];if(a?.id){card.style.backgroundImage=`linear-gradient(180deg,transparent 30%,#05080dd8 100%),url('/avs/library/thumb/${encodeURIComponent(a.id)}')`;card.style.backgroundSize="cover";card.style.backgroundPosition="center";}}
  function renderTimeline(){timeline.innerHTML="";let at=0;const sel=selectedIndex(node,state.doc);state.doc.shots.forEach((s,i)=>{const start=at;at+=Number(s.duration||5);const card=css($("div"),{position:"relative",flex:"0 0 230px",height:"112px",border:`2px solid ${i===sel?C.accent:C.border}`,borderRadius:"5px",background:"linear-gradient(145deg,#1b222d,#10151c)",overflow:"hidden",cursor:"pointer",boxSizing:"border-box"});const ruler=css($("div",`${start.toFixed(1)}s  →  ${at.toFixed(1)}s`),{position:"absolute",top:"-19px",left:"2px",fontSize:"9px",color:C.muted});const ix=css($("div",`镜头 ${i+1}`),{position:"absolute",top:"6px",left:"7px",background:i===sel?"#153d21":"#171d25",border:`1px solid ${i===sel?"#4eaa67":C.border}`,borderRadius:"4px",padding:"2px 5px",fontSize:"9px",fontWeight:"800"});const name=css($("div",s.name||`镜头${i+1}`),{position:"absolute",left:"7px",bottom:"24px",right:"7px",fontSize:"12px",fontWeight:"800",textShadow:"0 1px 2px #000"});const meta=css($("div",`${Number(s.duration||5).toFixed(1)}s · ${s.shot_size||"全景"} · ${s.camera_move||"固定"}`),{position:"absolute",left:"7px",bottom:"6px",right:"7px",fontSize:"9px",color:"#c4cedb",textShadow:"0 1px 2px #000"});card.append(ix,name,meta);card.onclick=()=>setSel(i);timeline.append(ruler,card);hydrateCard(card,s);});}

  async function renderRefsPanel(shot){
    left.innerHTML="";const h=css($("div","参考素材"),{fontWeight:"800",fontSize:"12px",marginBottom:"6px"});left.append(h);
    const refs=refsFromShot(shot);const ctx=await refPreview(refs);const all=[...(ctx.images||[]).map(x=>[x,"图片"]),...(ctx.videos||[]).map(x=>[x,"视频"]),...(ctx.audios||[]).map(x=>[x,"音频"])];
    if(!all.length){left.append(css($("div","在镜头提示词或引用栏输入 @角色 / @场景 / @角色/单素材"),{fontSize:"10px",color:C.muted,lineHeight:"1.5"}));return;}
    for(const [a,t] of all){const box=css($("div"),{display:"grid",gridTemplateColumns:"70px 1fr",gap:"7px",padding:"5px",marginBottom:"5px",border:`1px solid ${C.border}`,borderRadius:"5px",background:C.panel2});const pv=css($("div"),{height:"54px",background:"#05070b",borderRadius:"4px",overflow:"hidden",display:"flex",alignItems:"center",justifyContent:"center",fontSize:"9px",color:C.muted});if(t==="图片"&&a.id){const im=$("img");im.src=`/avs/library/thumb/${encodeURIComponent(a.id)}`;css(im,{width:"100%",height:"100%",objectFit:"cover"});pv.append(im);}else pv.textContent=t;const tx=$("div");tx.append(css($("div",a.display_name||a.file_name||"素材"),{fontSize:"10px",fontWeight:"700",wordBreak:"break-all"}),css($("div",t),{fontSize:"9px",color:C.muted,marginTop:"3px"}));box.append(pv,tx);left.append(box);}
  }

  async function groups(){if(state.groups)return state.groups;try{const r=await api.fetchApi("/avs/library/groups");const j=await r.json();state.groups=j.groups||[];}catch{state.groups=[];}return state.groups;}
  function attachAtSuggest(textarea){
    const pop=css($("div"),{display:"none",position:"absolute",zIndex:30,left:"8px",right:"8px",top:"112px",maxHeight:"180px",overflow:"auto",background:"#0c1118",border:`1px solid ${C.border}`,borderRadius:"5px",boxShadow:"0 8px 22px #000a"});textarea.parentElement.style.position="relative";textarea.parentElement.append(pop);
    textarea.addEventListener("input",async()=>{const before=textarea.value.slice(0,textarea.selectionStart);const m=before.match(/@([^\s@，,；;]*)$/);if(!m){pop.style.display="none";return;}const q=(m[1]||"").toLowerCase();const gs=(await groups()).filter(g=>String(g.alias||g.name||"").toLowerCase().includes(q)).slice(0,10);pop.innerHTML="";for(const g of gs){const row=css($("div",`@${g.alias||g.name}   ·   ${g.category||"资源"}`),{padding:"7px",fontSize:"10px",cursor:"pointer",borderBottom:`1px solid ${C.border}`});row.onmousedown=(e)=>{e.preventDefault();const start=textarea.selectionStart-m[0].length;const token=`@${g.alias||g.name}`;textarea.value=textarea.value.slice(0,start)+token+textarea.value.slice(textarea.selectionStart);textarea.selectionStart=textarea.selectionEnd=start+token.length;textarea.dispatchEvent(new Event("input"));pop.style.display="none";};pop.append(row);}pop.style.display=gs.length?"block":"none";});textarea.addEventListener("blur",()=>setTimeout(()=>pop.style.display="none",150));
  }

  function renderEditor(){
    const i=selectedIndex(node,state.doc),s=state.doc.shots[i];mid.innerHTML="";right.innerHTML="";
    renderRefsPanel(s);
    const title=css($("div",`提示词组 ${i+1} ｜ ${s.name||`镜头${i+1}`}`),{fontSize:"12px",fontWeight:"800",marginBottom:"6px"});mid.append(title);
    const pr=mkTa(7);pr.placeholder="写这个镜头真正发生什么。输入 @ 可以引用永久资源库。";pr.value=s.prompt||"";pr.oninput=()=>{s.prompt=pr.value;saveDoc(node,state.doc);state.thumbCache.clear();};mid.append(label("镜头提示词",pr));attachAtSuggest(pr);
    const row=css($("div"),{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px",marginTop:"7px"});const act=mkTa(3),goal=mkTa(3);act.value=s.action||"";goal.value=s.story_goal||"";act.oninput=()=>{s.action=act.value;saveDoc(node,state.doc);};goal.oninput=()=>{s.story_goal=goal.value;saveDoc(node,state.doc);};row.append(label("主要动作",act),label("剧情目的",goal));mid.append(row);
    const exp=$("details");const sm=$("summary","动作衔接 / 对白 / 声音");css(sm,{cursor:"pointer",fontSize:"10px",color:"#cbd5e1",padding:"6px 0"});exp.append(sm);const st=mkTa(2),en=mkTa(2),dia=mkTa(2),snd=mkTa(2);st.value=s.start_state||"";en.value=s.end_state||"";dia.value=s.dialogue||"";snd.value=s.sound_notes||"";st.oninput=()=>{s.start_state=st.value;saveDoc(node,state.doc)};en.oninput=()=>{s.end_state=en.value;saveDoc(node,state.doc)};dia.oninput=()=>{s.dialogue=dia.value;saveDoc(node,state.doc)};snd.oninput=()=>{s.sound_notes=snd.value;saveDoc(node,state.doc)};exp.append(label("起始状态",st),label("结束状态",en),label("对白",dia),label("声音设计",snd));mid.append(exp);

    const rh=css($("div","当前镜头"),{fontWeight:"800",fontSize:"12px",marginBottom:"6px"});right.append(rh);
    const nm=mkInput(),duration=mkInput("number");nm.value=s.name||"";duration.value=Number(s.duration||5);nm.oninput=()=>{s.name=nm.value;saveDoc(node,state.doc);renderTimeline();};duration.oninput=()=>{s.duration=Math.max(.2,Math.min(15.1,Number(duration.value||5)));saveDoc(node,state.doc);renderTimeline();updateDuration();};right.append(label("镜头名称",nm),label("秒数",duration));
    const sz=fieldSelect(["远景","全景","中景","近景","特写"],s.shot_size,v=>{s.shot_size=v;saveDoc(node,state.doc);renderTimeline();});const ag=fieldSelect(["正面","侧面","背面","肩后","低机位","高机位","俯拍","仰拍"],s.camera_angle,v=>{s.camera_angle=v;saveDoc(node,state.doc);});const mv=fieldSelect(["固定","推近","拉远","跟拍","横移","轻微环绕"],s.camera_move,v=>{s.camera_move=v;saveDoc(node,state.doc);renderTimeline();});const ct=fieldSelect(["自动","续写上一镜","独立镜头"],s.continuity,v=>{s.continuity=v;saveDoc(node,state.doc);});right.append(label("景别",sz),label("机位",ag),label("运镜",mv),label("连续性",ct));
    const refsTitle=css($("div","资源引用"),{fontSize:"11px",fontWeight:"800",marginTop:"8px",marginBottom:"4px"});right.append(refsTitle);
    for(const [k,l] of [["character_refs","角色"],["scene_refs","场景"],["prop_refs","道具"],["motion_refs","动作视频"],["audio_refs","声音"]]){const x=mkInput();x.value=s[k]||"";x.placeholder="@资源";x.oninput=()=>{s[k]=x.value;saveDoc(node,state.doc);state.thumbCache.clear();};right.append(label(l,x));}
    const seed=mkInput("number");seed.value=Number(s.seed||0);seed.oninput=()=>{s.seed=Number(seed.value||0);saveDoc(node,state.doc);};right.append(label("Seed（随机模式可忽略）",seed));
    const status=css($("div","执行工作流时，下游“一键生成视频”只生成当前选中的这个镜头。"),{marginTop:"8px",padding:"7px",border:`1px solid #365743`,background:"#0e2316",borderRadius:"5px",fontSize:"9px",lineHeight:"1.45",color:"#b7e8c4"});right.append(status);
  }

  add.onclick=()=>{state.doc.shots.push(defaultShot(state.doc.shots.length+1));saveDoc(node,state.doc);setSel(state.doc.shots.length-1);};
  dup.onclick=()=>{const i=selectedIndex(node,state.doc),c=JSON.parse(JSON.stringify(state.doc.shots[i]));c.id=`shot-${Date.now()}`;c.name=`${c.name||`镜头${i+1}`} 复制`;state.doc.shots.splice(i+1,0,c);saveDoc(node,state.doc);setSel(i+1);};
  del.onclick=()=>{if(state.doc.shots.length<=1)return;const i=selectedIndex(node,state.doc);state.doc.shots.splice(i,1);saveDoc(node,state.doc);setSel(Math.min(i,state.doc.shots.length-1));};
  prev.onclick=()=>setSel(selectedIndex(node,state.doc)-1);next.onclick=()=>setSel(selectedIndex(node,state.doc)+1);compile.onclick=()=>{state.thumbCache.clear();renderTimeline();renderEditor();};

  renderTimeline();renderEditor();updateDuration();
  const dw=node.addDOMWidget("avs_timeline_director_ui","div",root,{
    serialize:false,
    hideOnZoom:false,
    getMinHeight:()=>735,
    getMaxHeight:()=>735,
  });
  dw.computeSize=(width)=>[Math.max(900,width||1180),735];

  // Keep the director itself compact and pinned immediately below the sockets.
  const enforceLayout=()=>{
    collapseNativeWidgets(node);
    if(root?.parentElement){
      root.parentElement.style.margin="0";
      root.parentElement.style.padding="0";
    }
    node.graph?.setDirtyCanvas?.(true,true);
  };
  const oldResize=node.onResize;
  node.onResize=function(size){
    oldResize?.call(this,size);
    root.style.height=Math.max(640,(size?.[1]||780)-45)+"px";
    setTimeout(enforceLayout,0);
    setTimeout(enforceLayout,80);
  };
  const oldConfigure=node.onConfigure;
  node.onConfigure=function(info){
    const r=oldConfigure?.call(this,info);
    setTimeout(enforceLayout,0);
    setTimeout(enforceLayout,80);
    setTimeout(enforceLayout,300);
    return r;
  };
  // Nodes 2.0 may rebuild DOM-widget wrappers shortly after creation.
  for(const ms of [0,50,200,600,1200])setTimeout(enforceLayout,ms);
}

app.registerExtension({name:EXT,async beforeRegisterNodeDef(nodeType,nodeData){if(nodeData?.name!=="AVSTimelineDirector")return;const old=nodeType.prototype.onNodeCreated;nodeType.prototype.onNodeCreated=function(){const r=old?.apply(this,arguments);setTimeout(()=>build(this),0);return r;};}});
