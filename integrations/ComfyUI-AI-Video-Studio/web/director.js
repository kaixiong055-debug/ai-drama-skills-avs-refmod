import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const C = {
  bg: "#10141d", panel: "#151b27", border: "#313a50", text: "#eef2ff",
  muted: "#94a3b8", accent: "#6474ff", green: "#34d399", orange: "#f59e0b"
};

function findWidget(node, name){ return node.widgets?.find(w=>w.name===name); }
function setW(node,name,value){ const w=findWidget(node,name); if(!w)return; w.value=value; w.callback?.(value); node.graph?.setDirtyCanvas?.(true,true); }
function hide(w){ if(!w||w.__avsDirectorHidden)return; w.__avsDirectorHidden=true; w.__oldType=w.type; w.type="hidden"; w.computeSize=()=>[0,-4]; }
function show(w){ if(!w)return; w.type=w.__oldType||w.type||"text"; delete w.computeSize; }
function el(tag, text=""){ const x=document.createElement(tag); if(text)x.textContent=text; return x; }
function style(x,o){ Object.assign(x.style,o); return x; }
function inp(type="text"){ return style(el("input"),{width:"100%",boxSizing:"border-box",background:"#0d1118",color:C.text,border:`1px solid ${C.border}`,borderRadius:"8px",padding:"8px 9px",fontSize:"12px"}); }
function sel(){ return style(el("select"),{width:"100%",boxSizing:"border-box",background:"#0d1118",color:C.text,border:`1px solid ${C.border}`,borderRadius:"8px",padding:"8px 9px",fontSize:"12px"}); }
function ta(rows=3){ const x=el("textarea"); x.rows=rows; return style(x,{width:"100%",resize:"vertical",boxSizing:"border-box",background:"#0d1118",color:C.text,border:`1px solid ${C.border}`,borderRadius:"8px",padding:"8px 9px",fontSize:"12px",lineHeight:"1.45"}); }
function label(text,control){ const w=el("label"); style(w,{display:"flex",flexDirection:"column",gap:"5px",fontSize:"11px",color:C.muted}); const t=el("span",text); w.append(t,control); return w; }
function section(title){ const box=el("div"); style(box,{background:C.panel,border:`1px solid ${C.border}`,borderRadius:"11px",padding:"10px",marginBottom:"9px"}); const h=el("div",title); style(h,{fontWeight:"800",color:C.text,fontSize:"12px",marginBottom:"8px"}); box.append(h); return box; }
function grid(cols=2){ const g=el("div"); style(g,{display:"grid",gridTemplateColumns:`repeat(${cols},minmax(0,1fr))`,gap:"8px"}); return g; }
function optionsFrom(w){ return w?.options?.values || w?.options || []; }
function bind(node,name,control,kind="text"){
  const w=findWidget(node,name); if(!w)return;
  if(control.tagName==="SELECT"){
    for(const v of optionsFrom(w)){ const o=el("option",String(v)); o.value=String(v); control.append(o); }
    control.value=String(w.value ?? "");
  }else if(kind==="checkbox") control.checked=!!w.value;
  else control.value=w.value ?? "";
  const evt=kind==="checkbox"?"change":"input";
  control.addEventListener(evt,()=>{
    let v=kind==="checkbox"?control.checked:control.value;
    if(kind==="number") v=Number(v);
    setW(node,name,v);
  });
}
function domWidget(node,name,root,height){ const w=node.addDOMWidget(name,"div",root,{serialize:false,hideOnZoom:false}); w.computeSize=(width)=>[width,height]; return w; }
function purpose(text){ const p=el("div"); style(p,{background:"linear-gradient(135deg,#172036,#111827)",border:"1px solid #334467",borderRadius:"11px",padding:"10px 12px",color:"#dbeafe",fontSize:"12px",lineHeight:"1.55",marginBottom:"9px"}); p.innerHTML=`<b>作用：</b>${text}`; return p; }

function buildProjectUI(node){
  for(const w of node.widgets||[]) hide(w);
  node.size=[650,790]; node.title="AI视频工作室｜总控导演台";
  const root=el("div"); style(root,{padding:"3px 2px 8px",fontFamily:"Inter,system-ui,sans-serif",color:C.text});
  root.append(purpose("整个项目只需要一个。统一角色、场景、画风、比例、质量、声音和模型方案，后面的每个分镜都会继承这里的设置。"));

  const a=section("① 项目与统一风格"), ag=grid(2);
  const project=inp(), type=sel(), styleTa=ta(3), lang=sel();
  bind(node,"project_name",project); bind(node,"project_type",type); bind(node,"visual_style",styleTa); bind(node,"language",lang);
  ag.append(label("项目名称",project),label("项目类型",type),label("界面语言",lang));
  a.append(ag,label("统一视觉风格",styleTa)); root.append(a);

  const b=section("② 全局资源（支持 @资源组 / @资源组/单素材）"), bg=grid(3);
  const cr=inp(), sr=inp(), pr=inp(); bind(node,"default_character_refs",cr); bind(node,"default_scene_refs",sr); bind(node,"default_prop_refs",pr);
  bg.append(label("默认角色",cr),label("默认场景",sr),label("默认道具",pr)); b.append(bg); root.append(b);

  const c=section("③ 输出与一致性"), cg=grid(3);
  const ratio=sel(), res=sel(), sec=inp("number"), cons=sel(), audio=sel(), quality=sel();
  bind(node,"aspect_ratio",ratio); bind(node,"resolution",res); bind(node,"default_seconds",sec,"number"); bind(node,"consistency",cons); bind(node,"audio_mode",audio); bind(node,"quality_preset",quality);
  cg.append(label("画面比例",ratio),label("清晰度",res),label("默认时长(秒)",sec),label("一致性",cons),label("声音",audio),label("生成质量",quality)); c.append(cg); root.append(c);

  const d=section("④ 输出保存"), dg=grid(2); const save=inp("checkbox"), prefix=inp(); save.type="checkbox"; bind(node,"auto_save",save,"checkbox"); bind(node,"output_prefix",prefix); dg.append(label("自动保存MP4",save),label("输出目录前缀",prefix)); d.append(dg); root.append(d);

  const adv=el("details"); style(adv,{background:"#0e1420",border:`1px solid ${C.border}`,borderRadius:"10px",padding:"8px 10px"}); const sm=el("summary","高级设置（模型 / LoRA / 采样）"); style(sm,{cursor:"pointer",fontSize:"12px",fontWeight:"800",color:"#cbd5e1"}); adv.append(sm);
  const advancedNames=["fl2va_model","ref2va_model","clip_model","video_vae_model","audio_vae_model","lora_name","lora_strength","weight_dtype","steps_override","cfg","sampler","scheduler","denoise","shift_video","shift_audio","ref_image_size","max_images","max_videos","max_audios"];
  const advg=grid(2); style(advg,{marginTop:"10px"});
  const labels={fl2va_model:"基础/图生模型",ref2va_model:"多参考模型",clip_model:"文本编码器",video_vae_model:"视频VAE",audio_vae_model:"音频VAE",lora_name:"LoRA",lora_strength:"LoRA强度",weight_dtype:"权重类型",steps_override:"Steps覆盖(0=自动)",cfg:"CFG",sampler:"采样器",scheduler:"调度器",denoise:"Denoise",shift_video:"Video Shift",shift_audio:"Audio Shift",ref_image_size:"参考图尺寸",max_images:"最多图片",max_videos:"最多视频",max_audios:"最多音频"};
  for(const n of advancedNames){ const w=findWidget(node,n); if(!w)continue; let ctl; const vals=optionsFrom(w); if(vals?.length){ctl=sel();bind(node,n,ctl);}else{ctl=inp("number");bind(node,n,ctl,"number");} advg.append(label(labels[n]||n,ctl)); }
  adv.append(advg); root.append(adv);
  domWidget(node,"avs_project_director","div"&&root,760);
}

function buildShotUI(node){
  for(const w of node.widgets||[]) hide(w);
  node.size=[690,930]; node.title="AI视频工作室｜分镜导演台";
  const root=el("div"); style(root,{padding:"3px 2px 8px",fontFamily:"Inter,system-ui,sans-serif",color:C.text});
  root.append(purpose("一个导演台 = 一个镜头。复制这个节点即可做第2镜、第3镜……；连接上一镜 VIDEO 后可自动取尾部引导帧续写。"));

  const a=section("① 镜头信息"), ag=grid(3); const no=inp("number"), name=inp(), sec=inp("number"); bind(node,"shot_number",no,"number"); bind(node,"shot_name",name); bind(node,"seconds",sec,"number"); ag.append(label("镜头编号",no),label("镜头名称",name),label("时长(0=继承总控)",sec)); const goal=ta(2);bind(node,"story_goal",goal);a.append(ag,label("这一镜的剧情目的",goal));root.append(a);

  const b=section("② 本镜头资源引用"), bg=grid(2); const fields=[["character_refs","角色"],["scene_refs","场景"],["prop_refs","道具"],["motion_refs","动作参考视频"],["audio_refs","声音参考"]]; for(const [n,l] of fields){const x=inp();bind(node,n,x);bg.append(label(`${l}（输入 @）`,x));} b.append(bg);root.append(b);

  const c=section("③ 动作与表演"); const start=ta(2),action=ta(3),emotion=inp(),end=ta(2); bind(node,"start_state",start);bind(node,"action",action);bind(node,"emotion",emotion);bind(node,"end_state",end); c.append(label("起始状态",start),label("主要动作（建议只写一个主要动作链）",action),label("情绪/表演",emotion),label("结束状态 / 下一镜连接点",end));root.append(c);

  const d=section("④ 摄影"), dg=grid(3); const size=sel(),angle=sel(),move=sel();bind(node,"shot_size",size);bind(node,"camera_angle",angle);bind(node,"camera_move",move);dg.append(label("景别",size),label("机位",angle),label("运镜",move));d.append(dg);root.append(d);

  const e=section("⑤ 连续性与 Seed"), eg=grid(3); const cont=sel(),smode=sel(),seed=inp("number"),inherit=inp("checkbox");inherit.type="checkbox";bind(node,"continuity",cont);bind(node,"seed_mode",smode);bind(node,"seed",seed,"number");bind(node,"inherit_previous_audio",inherit,"checkbox");eg.append(label("上一镜处理",cont),label("Seed模式",smode),label("Seed",seed));e.append(eg,label("继承上一镜音频（默认关闭，避免声音重复）",inherit));root.append(e);

  const f=section("⑥ 对白 / 声音 / 导演补充"); const dia=ta(2),snd=ta(2),extra=ta(3);bind(node,"dialogue",dia);bind(node,"sound_notes",snd);bind(node,"extra_prompt",extra);f.append(label("对白",dia),label("声音设计",snd),label("补充要求",extra));root.append(f);
  domWidget(node,"avs_shot_director",root,900);
}

function buildGenerateUI(node){
  for(const w of node.widgets||[]) hide(w);
  node.size=[460,245]; node.title="AI视频工作室｜一键生成视频";
  const root=el("div"); style(root,{padding:"4px 3px",fontFamily:"Inter,system-ui,sans-serif",color:C.text});
  root.append(purpose("只需连接 SHOT_CONTEXT。执行工作流后会自动：选模型 → 加 LoRA → 编译 H3 → 上一镜尾部续写 → 采样 → 解码 → 创建视频 → 保存 MP4。"));
  const p=section("生成流程"); p.innerHTML += `<div style="font-size:12px;line-height:1.8;color:#cbd5e1">① 读取导演台<br>② 加载本镜头实际引用素材<br>③ 自动选择 T2V / R2V<br>④ 有上一镜时自动取尾部有效帧 AddGuide<br>⑤ H3 采样与音画解码<br>⑥ 输出 VIDEO，并按总控设置自动保存</div>`; root.append(p);
  const badge=el("div","现在不需要再手动连接 CLIP / VAE / UNet / KSampler"); style(badge,{background:"#10352d",border:"1px solid #1f6a56",color:"#a7f3d0",borderRadius:"9px",padding:"8px 10px",fontSize:"11px",fontWeight:"700"});root.append(badge);
  domWidget(node,"avs_one_click",root,220);
}

app.registerExtension({
  name:"AI.Video.Studio.Director.v070",
  async beforeRegisterNodeDef(nodeType,nodeData){
    const old=nodeType.prototype.onNodeCreated;
    if(nodeData?.name==="AVSProjectDirector") nodeType.prototype.onNodeCreated=function(){const r=old?.apply(this,arguments);setTimeout(()=>buildProjectUI(this),0);return r;};
    if(nodeData?.name==="AVSShotDirector") nodeType.prototype.onNodeCreated=function(){const r=old?.apply(this,arguments);setTimeout(()=>buildShotUI(this),0);return r;};
    if(nodeData?.name==="AVSOneClickGenerate") nodeType.prototype.onNodeCreated=function(){const r=old?.apply(this,arguments);setTimeout(()=>buildGenerateUI(this),0);return r;};
  }
});
