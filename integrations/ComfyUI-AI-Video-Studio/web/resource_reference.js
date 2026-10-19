import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const EXTENSION_NAME = "ai_video_studio.resource_reference.v052";

const I18N = {
  "zh-CN": {
    title: "AI视频工作室｜资源引用",
    purposeLabel: "作用",
    purpose: "支持两种引用：@角色 = 引用整个资源组并自动挑选参考；@角色/某张图 = 只引用这一张图片（视频/音频同理）。系统只建立引用清单，不会把整个资源库加载到显存。",
    language: "界面语言",
    prompt: "镜头提示词",
    placeholder: "例如：@苏甜柠 在 @金色舞台 跳舞；只用正脸时可写 @苏甜柠/正脸",
    hint: "输入 @ 选择整个资源组；点击“展开素材”或输入 @资源组/ 可单独选择某一张图片、某段视频或某个音频。",
    referenced: "当前引用",
    none: "还没有引用资源。请在提示词中输入 @",
    inspect: "检查引用",
    advanced: "高级设置",
    imageLimit: "最多图片",
    videoLimit: "最多视频",
    audioLimit: "最多音频",
    loading: "正在读取资源库…",
    previewing: "正在解析 @资源…",
    previewFailed: (e) => `引用检查失败：${e}`,
    resourceDb: "资源库",
    outContext: "RESOURCE_CONTEXT",
    outPrompt: "PROMPT",
    outSummary: "引用摘要",
    missing: "未找到",
    selected: (i,v,a) => `本次将使用：图片 ${i}｜视频 ${v}｜音频 ${a}`,
    groups: (n) => `已引用 ${n} 个资源`,
    noGroups: "没有找到可引用内容。可以先创建资源组，或者检查 @ 后面的名称。",
    resolvingAssets: "正在读取实际引用素材…",
    noSelectedAssets: "这个资源组没有选中可用于本次生成的素材。",
    imageLabel: "图片",
    videoLabel: "视频",
    audioLabel: "音频",
    usingAssets: (i,v,a) => `实际使用：图片 ${i}｜视频 ${v}｜音频 ${a}`,
    wholeGroup: "整组引用",
    singleAsset: "单素材",
    expandAssets: "展开素材",
    backGroups: "返回资源组",
    chooseExact: "只引用这个素材",
    category: {"角色":"角色","场景":"场景","道具":"道具","动作":"动作","声音":"声音"},
  },
  "en-US": {
    title: "AI Video Studio | Resource Reference",
    purposeLabel: "Purpose",
    purpose: "Two reference modes are supported: @Character references a whole group with automatic selection; @Character/Asset references one exact image, video or audio file. The library is not loaded into VRAM.",
    language: "Language",
    prompt: "Shot Prompt",
    placeholder: "Example: @Hero dances on @GoldenStage; use @Hero/FrontFace for one exact image",
    hint: "Type @ for a whole group. Click Expand Assets or type @group/ to pick one exact image, video or audio file.",
    referenced: "Current References",
    none: "No resource references yet. Type @ in the prompt.",
    inspect: "Check References",
    advanced: "Advanced",
    imageLimit: "Max Images",
    videoLimit: "Max Videos",
    audioLimit: "Max Audio",
    loading: "Loading resource library…",
    previewing: "Resolving @resources…",
    previewFailed: (e) => `Reference check failed: ${e}`,
    resourceDb: "Resource Library",
    outContext: "RESOURCE_CONTEXT",
    outPrompt: "PROMPT",
    outSummary: "Reference Summary",
    missing: "Missing",
    selected: (i,v,a) => `Selected: ${i} images | ${v} videos | ${a} audio`,
    groups: (n) => `${n} resources referenced`,
    noGroups: "No matching references found. Create a resource group or check the text after @.",
    resolvingAssets: "Loading the actual referenced assets…",
    noSelectedAssets: "No assets from this group are selected for this generation.",
    imageLabel: "Image",
    videoLabel: "Video",
    audioLabel: "Audio",
    usingAssets: (i,v,a) => `Using: ${i} images | ${v} videos | ${a} audio`,
    wholeGroup: "Whole Group",
    singleAsset: "Single Asset",
    expandAssets: "Expand Assets",
    backGroups: "Back to Groups",
    chooseExact: "Use only this asset",
    category: {"角色":"Character","场景":"Scene","道具":"Prop","动作":"Motion","声音":"Voice"},
  }
};

function tr(lang){ return I18N[lang] || I18N["zh-CN"]; }
function elem(tag, attrs={}, ...children){
  const el=document.createElement(tag);
  for(const [k,v] of Object.entries(attrs)){
    if(k==="className") el.className=v;
    else if(k==="text") el.textContent=v;
    else if(k.startsWith("on") && typeof v==="function") el.addEventListener(k.slice(2).toLowerCase(),v);
    else if(v!==undefined && v!==null) el.setAttribute(k,v);
  }
  for(const c of children){ if(c!=null) el.append(c.nodeType?c:document.createTextNode(String(c))); }
  return el;
}
function css(el, styles){ Object.assign(el.style, styles); return el; }
function findWidget(node,name){ return node.widgets?.find(w=>w.name===name); }
function setWidget(node,name,value){ const w=findWidget(node,name); if(!w)return; w.value=value; w.callback?.(value); node.graph?.setDirtyCanvas?.(true,true); }
function hideWidget(w){ if(!w||w.__avsHidden)return; w.__avsHidden=true; w.computeSize=()=>[0,-4]; w.hidden=true; }
async function jsonFetch(url,options={}){
  const res=await api.fetchApi(url,options); let data={}; try{data=await res.json();}catch(_){ }
  if(!res.ok||data.ok===false) throw new Error(data.error||`${res.status} ${res.statusText}`);
  return data;
}
function toast(message,isError=false){
  const x=elem("div",{text:message}); css(x,{position:"fixed",right:"24px",bottom:"24px",zIndex:"100000",background:isError?"#8f2d2d":"#285f42",color:"#fff",padding:"11px 15px",borderRadius:"10px",boxShadow:"0 12px 35px #0008",fontSize:"13px",maxWidth:"520px"}); document.body.append(x); setTimeout(()=>x.remove(),3200);
}
function categoryIcon(c){ return c==="角色"?"👤":c==="场景"?"🏞️":c==="道具"?"🧰":c==="动作"?"🎬":c==="声音"?"🔊":"📦"; }
function displayToken(g){
  const value=(g.alias||g.name||"").trim();
  return /\s/.test(value) ? `@{${value}}` : `@${value}`;
}
function rawGroupKey(g){ return (g.alias||g.name||"").trim(); }
function rawAssetKey(a){
  const alias=(a.alias||"").trim();
  if(alias) return alias;
  const name=(a.display_name||a.file_name||"").trim();
  return name.replace(/\.[^.]+$/,"");
}
function exactAssetToken(g,a){
  const value=`${rawGroupKey(g)}/${rawAssetKey(a)}`;
  return /^[A-Za-z0-9_./\-\u3400-\u9fff]+$/.test(value) ? `@${value}` : `@{${value}}`;
}
function mediaIcon(t){ return t==="image"?"🖼️":t==="video"?"🎬":"🔊"; }
function currentAtQuery(text,caret){
  const before=text.slice(0,caret);
  const brace=before.match(/@\{([^{}]*)$/);
  if(brace) return {start:before.length-brace[0].length, end:caret, query:brace[1], braced:true};
  const plain=before.match(/@([^\s@{},，。！？；：]*)$/);
  if(plain) return {start:before.length-plain[0].length, end:caret, query:plain[1], braced:false};
  return null;
}
function promptRefs(text,groups){
  const found=[]; const lower=String(text||"").toLocaleLowerCase();
  for(const g of groups){
    const token=displayToken(g); const direct=`@${(g.alias||g.name||"").trim()}`;
    if(lower.includes(token.toLocaleLowerCase()) || lower.includes(direct.toLocaleLowerCase())) found.push(g);
  }
  return found;
}

function buildPanel(node){
  const wrap=elem("div"); css(wrap,{padding:"4px 2px 10px",color:"#ddd",fontFamily:"Inter,system-ui,sans-serif",position:"relative"});
  const purpose=elem("div"); css(purpose,{background:"#1b1f29",border:"1px solid #343b50",borderRadius:"10px",padding:"10px 12px",lineHeight:"1.45",marginBottom:"10px"});
  const purposeLabel=elem("strong"); const purposeText=elem("span"); purpose.append(purposeLabel,purposeText);

  const topRow=elem("div"); css(topRow,{display:"flex",gap:"8px",alignItems:"center",marginBottom:"8px"});
  const languageLabel=elem("span"); css(languageLabel,{color:"#aab0c0",fontSize:"12px",minWidth:"72px"});
  const language=elem("select"); css(language,{background:"#161922",color:"#eee",border:"1px solid #394158",borderRadius:"8px",padding:"6px 8px",flex:"1"}); language.innerHTML='<option value="zh-CN">中文</option><option value="en-US">English</option>'; topRow.append(languageLabel,language);

  const promptLabel=elem("div"); css(promptLabel,{fontWeight:"700",fontSize:"13px",margin:"4px 0 6px"});
  const editorWrap=elem("div"); css(editorWrap,{position:"relative"});
  const textarea=elem("textarea"); css(textarea,{width:"100%",height:"152px",resize:"vertical",boxSizing:"border-box",background:"#0e1118",color:"#f2f4f8",border:"1px solid #3a4257",borderRadius:"10px",padding:"11px 12px",fontSize:"13px",lineHeight:"1.55",outline:"none"});
  const popup=elem("div"); css(popup,{display:"none",position:"absolute",left:"8px",right:"8px",top:"100%",marginTop:"4px",maxHeight:"260px",overflow:"auto",zIndex:"9999",background:"#151923",border:"1px solid #3d4660",borderRadius:"10px",boxShadow:"0 14px 40px #000a",padding:"6px"});
  editorWrap.append(textarea,popup);
  const hint=elem("div"); css(hint,{fontSize:"11px",color:"#8f98ad",lineHeight:"1.45",margin:"6px 2px 10px"});

  const refHead=elem("div"); css(refHead,{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"6px"});
  const referencedLabel=elem("strong"); css(referencedLabel,{fontSize:"12px"});
  const inspect=elem("button"); css(inspect,{background:"#5868f2",color:"white",border:"0",borderRadius:"8px",padding:"7px 11px",fontWeight:"700",cursor:"pointer",fontSize:"12px"}); refHead.append(referencedLabel,inspect);
  const refs=elem("div"); css(refs,{minHeight:"54px",background:"#11141c",border:"1px solid #2d3446",borderRadius:"10px",padding:"8px",display:"flex",gap:"6px",flexWrap:"wrap",alignItems:"center"});
  const preview=elem("div"); css(preview,{fontSize:"11px",color:"#aab2c6",marginTop:"7px",minHeight:"18px"});

  const adv=elem("details"); css(adv,{marginTop:"9px",background:"#121620",border:"1px solid #2d3446",borderRadius:"9px",padding:"8px 10px"});
  const advSummary=elem("summary"); css(advSummary,{cursor:"pointer",fontWeight:"700",fontSize:"12px",color:"#bbc2d4"}); adv.append(advSummary);
  const advGrid=elem("div"); css(advGrid,{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:"8px",paddingTop:"9px"});
  function numBox(){ const i=elem("input",{type:"number",min:"0"}); css(i,{width:"100%",boxSizing:"border-box",background:"#0e1118",color:"#eee",border:"1px solid #384057",borderRadius:"7px",padding:"6px"}); return i; }
  const imgLimit=numBox(),vidLimit=numBox(),audLimit=numBox();
  const imgLbl=elem("label"),vidLbl=elem("label"),audLbl=elem("label"); for(const l of [imgLbl,vidLbl,audLbl]) css(l,{fontSize:"11px",color:"#9099ae"}); imgLbl.append(elem("div"),imgLimit); vidLbl.append(elem("div"),vidLimit); audLbl.append(elem("div"),audLimit); advGrid.append(imgLbl,vidLbl,audLbl); adv.append(advGrid);

  wrap.append(purpose,topRow,promptLabel,editorWrap,hint,refHead,refs,preview,adv);
  return {wrap,purposeLabel,purposeText,languageLabel,language,promptLabel,textarea,popup,hint,referencedLabel,inspect,refs,preview,advSummary,imgLimit,vidLimit,audLimit,imgLbl,vidLbl,audLbl};
}

function applyLanguage(node,ui,lang){
  const t=tr(lang); node.title=t.title;
  ui.purposeLabel.textContent=`${t.purposeLabel}：`; ui.purposeText.textContent=t.purpose;
  ui.languageLabel.textContent=t.language; ui.promptLabel.textContent=t.prompt; ui.textarea.placeholder=t.placeholder; ui.hint.textContent=t.hint; ui.referencedLabel.textContent=t.referenced; ui.inspect.textContent=t.inspect; ui.advSummary.textContent=t.advanced;
  ui.imgLbl.firstChild.textContent=t.imageLimit; ui.vidLbl.firstChild.textContent=t.videoLimit; ui.audLbl.firstChild.textContent=t.audioLimit;
  if(node.inputs?.[0]) node.inputs[0].name=t.resourceDb;
  if(node.outputs?.[0]) node.outputs[0].name=t.outContext; if(node.outputs?.[1]) node.outputs[1].name=t.outPrompt; if(node.outputs?.[2]) node.outputs[2].name=t.outSummary;
  node.graph?.setDirtyCanvas?.(true,true);
}

app.registerExtension({
  name:EXTENSION_NAME,
  async nodeCreated(node){
    if(node.comfyClass!=="AVSResourceReference") return;
    for(const name of ["language","prompt","max_images","max_videos","max_audios"]) hideWidget(findWidget(node,name));
    const ui=buildPanel(node); try{node.addDOMWidget("avs_reference_panel","avs_reference_panel",ui.wrap,{serialize:false});}catch(_){ }
    node.size=[610,585];

    let lang=findWidget(node,"language")?.value==="English"?"en-US":"zh-CN";
    let groups=[]; let previewTimer=null;
    ui.language.value=lang; ui.textarea.value=findWidget(node,"prompt")?.value||"";
    ui.imgLimit.value=findWidget(node,"max_images")?.value??9; ui.imgLimit.max=9;
    ui.vidLimit.value=findWidget(node,"max_videos")?.value??3; ui.vidLimit.max=3;
    ui.audLimit.value=findWidget(node,"max_audios")?.value??3; ui.audLimit.max=3;
    applyLanguage(node,ui,lang);

    async function loadGroups(){
      try{ const d=await jsonFetch("/avs/library/groups"); groups=d.groups||[]; renderRefs(); }
      catch(e){ ui.preview.textContent=tr(lang).previewFailed(e.message); }
    }
    function renderRefs(){
      const t=tr(lang); const found=promptRefs(ui.textarea.value,groups); ui.refs.innerHTML="";
      ui.refs.style.display="block";
      if(!groups.length){ const n=elem("div",{text:t.noGroups}); css(n,{color:"#aa8f73",fontSize:"11px",lineHeight:"1.4"}); ui.refs.append(n); return; }
      if(!found.length){ const n=elem("div",{text:t.none}); css(n,{color:"#697187",fontSize:"11px"}); ui.refs.append(n); return; }
      const wait=elem("div",{text:t.resolvingAssets}); css(wait,{color:"#8f98ad",fontSize:"11px",padding:"4px 2px"}); ui.refs.append(wait);
    }

    function assetThumb(asset, kind, index){
      const t=tr(lang);
      const card=elem("div");
      css(card,{width:"86px",minWidth:"86px",background:"#0d1119",border:"1px solid #30394d",borderRadius:"9px",overflow:"hidden"});
      const media=elem("div");
      css(media,{height:"72px",background:"#080b10",display:"flex",alignItems:"center",justifyContent:"center",position:"relative",overflow:"hidden"});
      if((kind==="image"||kind==="video") && asset?.id){
        const img=elem("img",{src:`/avs/library/thumb/${encodeURIComponent(asset.id)}`});
        css(img,{width:"100%",height:"100%",objectFit:"cover",display:"block"});
        img.onerror=()=>{img.remove();media.textContent=kind==="video"?"🎬":"🖼️";media.style.fontSize="24px";};
        media.append(img);
        if(kind==="video"){ const play=elem("div",{text:"▶"}); css(play,{position:"absolute",right:"5px",bottom:"4px",background:"#000b",color:"#fff",borderRadius:"999px",width:"20px",height:"20px",display:"flex",alignItems:"center",justifyContent:"center",fontSize:"9px"}); media.append(play); }
      }else{ media.textContent="🔊"; media.style.fontSize="25px"; }
      const typeText=kind==="image"?t.imageLabel:kind==="video"?t.videoLabel:t.audioLabel;
      const cap=elem("div"); css(cap,{padding:"5px 6px 6px"});
      const tag=elem("div",{text:`${typeText}${index}`}); css(tag,{fontSize:"9px",color:"#8fa1ff",fontWeight:"700",marginBottom:"2px"});
      const name=elem("div",{text:asset?.display_name||asset?.file_name||""}); css(name,{fontSize:"9px",color:"#d7dceb",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}); name.title=asset?.display_name||asset?.file_name||"";
      cap.append(tag,name); card.append(media,cap); return card;
    }

    function renderResolvedRefs(context){
      const t=tr(lang);
      const references=context?.references||[];
      const images=context?.images||[]; const videos=context?.videos||[]; const audios=context?.audios||[];
      ui.refs.innerHTML=""; ui.refs.style.display="block";
      if(!references.length){ const n=elem("div",{text:t.none}); css(n,{color:"#697187",fontSize:"11px"}); ui.refs.append(n); return; }
      const imageMap=new Map(images.map((a,i)=>[String(a.id),{asset:a,index:i+1}]));
      const videoMap=new Map(videos.map((a,i)=>[String(a.id),{asset:a,index:i+1}]));
      const audioMap=new Map(audios.map((a,i)=>[String(a.id),{asset:a,index:i+1}]));
      for(const ref of references){
        const box=elem("div"); css(box,{background:"#151a25",border:"1px solid #333d54",borderRadius:"10px",padding:"8px",marginBottom:"7px"});
        const head=elem("div"); css(head,{display:"flex",alignItems:"center",gap:"7px",marginBottom:"7px"});
        const icon=elem("div",{text:categoryIcon(ref.category)}); css(icon,{width:"24px",height:"24px",borderRadius:"7px",background:"#252d43",display:"flex",alignItems:"center",justifyContent:"center",fontSize:"13px"});
        const text=elem("div"); css(text,{minWidth:"0",flex:"1"});
        const titleRow=elem("div"); css(titleRow,{display:"flex",alignItems:"center",gap:"6px",minWidth:"0"});
        const title=elem("div",{text:`${ref.name||ref.alias||""}  ${ref.token||""}`}); css(title,{fontWeight:"700",fontSize:"11px",color:"#eef1ff",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",minWidth:"0"});
        const kindBadge=elem("span",{text:ref.kind==="asset"?t.singleAsset:t.wholeGroup}); css(kindBadge,{fontSize:"8px",padding:"2px 5px",borderRadius:"999px",background:ref.kind==="asset"?"#244f3c":"#283356",color:ref.kind==="asset"?"#a8f0cb":"#bec8ff",whiteSpace:"nowrap"});
        titleRow.append(title,kindBadge);
        const ids=ref.selected||{}; const ii=(ids.image||[]).length,vv=(ids.video||[]).length,aa=(ids.audio||[]).length;
        const sub=elem("div",{text:t.usingAssets(ii,vv,aa)}); css(sub,{fontSize:"9px",color:"#8e99b2",marginTop:"1px"}); text.append(titleRow,sub); head.append(icon,text); box.append(head);
        const assets=elem("div"); css(assets,{display:"flex",gap:"6px",overflowX:"auto",paddingBottom:"2px"});
        for(const id of ids.image||[]){ const x=imageMap.get(String(id)); if(x) assets.append(assetThumb(x.asset,"image",x.index)); }
        for(const id of ids.video||[]){ const x=videoMap.get(String(id)); if(x) assets.append(assetThumb(x.asset,"video",x.index)); }
        for(const id of ids.audio||[]){ const x=audioMap.get(String(id)); if(x) assets.append(assetThumb(x.asset,"audio",x.index)); }
        if(!assets.childNodes.length){ const empty=elem("div",{text:t.noSelectedAssets}); css(empty,{fontSize:"10px",color:"#777f93",padding:"3px"}); assets.append(empty); }
        box.append(assets); ui.refs.append(box);
      }
    }
    function insertReferenceToken(info, token){
      const start=info?.start ?? (ui.textarea.selectionStart||0);
      const end=info?.end ?? (ui.textarea.selectionStart||0);
      const before=ui.textarea.value.slice(0,start);
      const after=ui.textarea.value.slice(end);
      ui.textarea.value=before+token+" "+after;
      const pos=(before+token+" ").length;
      ui.textarea.focus();
      ui.textarea.setSelectionRange(pos,pos);
      syncPrompt();
      ui.popup.style.display="none";
    }

    async function loadGroupAssets(groupId){
      const d=await jsonFetch(`/avs/library/assets?group_id=${encodeURIComponent(groupId)}&limit=1000`);
      return d.assets||[];
    }

    async function showAssetSuggestions(g, filter, info){
      const t=tr(lang);
      ui.popup.innerHTML="";
      const header=elem("div"); css(header,{display:"flex",alignItems:"center",gap:"8px",padding:"5px 6px 8px",borderBottom:"1px solid #2e3548",marginBottom:"5px"});
      const back=elem("button",{text:"←"}); css(back,{width:"28px",height:"28px",border:"1px solid #384158",borderRadius:"7px",background:"#1c2230",color:"#fff",cursor:"pointer"});
      const hcopy=elem("div"); css(hcopy,{flex:"1",minWidth:"0"});
      const htitle=elem("div",{text:g.name}); css(htitle,{fontSize:"12px",fontWeight:"800",color:"#f2f4ff"});
      const hsub=elem("div",{text:`${displayToken(g)} · ${t.singleAsset}`}); css(hsub,{fontSize:"9px",color:"#8e98ae",marginTop:"1px"}); hcopy.append(htitle,hsub); header.append(back,hcopy); ui.popup.append(header);
      back.onclick=(ev)=>{ev.preventDefault();showSuggestions();};
      let assets=[];
      try{ assets=await loadGroupAssets(g.id); }
      catch(e){ const err=elem("div",{text:e.message}); css(err,{padding:"10px",color:"#ff9999",fontSize:"11px"});ui.popup.append(err);ui.popup.style.display="block";return; }
      const q=(filter||"").trim().toLocaleLowerCase();
      if(q) assets=assets.filter(a=>`${a.alias||""} ${a.display_name||""} ${a.file_name||""} ${(a.tags||[]).join(" ")}`.toLocaleLowerCase().includes(q));
      if(!assets.length){ const empty=elem("div",{text:t.noSelectedAssets}); css(empty,{padding:"10px",color:"#858ea2",fontSize:"11px"}); ui.popup.append(empty); ui.popup.style.display="block"; return; }
      for(const a of assets.slice(0,80)){
        const row=elem("button"); css(row,{width:"100%",display:"grid",gridTemplateColumns:"46px 1fr auto",gap:"9px",alignItems:"center",textAlign:"left",background:"transparent",border:"0",borderRadius:"8px",padding:"6px",color:"#eee",cursor:"pointer"}); row.onmouseenter=()=>row.style.background="#252b3a"; row.onmouseleave=()=>row.style.background="transparent";
        const thumb=elem("div"); css(thumb,{width:"46px",height:"46px",borderRadius:"7px",overflow:"hidden",background:"#0b0e14",display:"flex",alignItems:"center",justifyContent:"center",fontSize:"20px"});
        if((a.media_type==="image"||a.media_type==="video")&&a.id){ const img=elem("img",{src:`/avs/library/thumb/${encodeURIComponent(a.id)}`}); css(img,{width:"100%",height:"100%",objectFit:"cover"}); img.onerror=()=>{img.remove();thumb.textContent=mediaIcon(a.media_type)}; thumb.append(img); } else thumb.textContent=mediaIcon(a.media_type);
        const copy=elem("div"); css(copy,{minWidth:"0"}); const nm=elem("div",{text:a.display_name||a.file_name}); css(nm,{fontWeight:"700",fontSize:"11px",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}); const al=elem("div",{text:`${exactAssetToken(g,a)} · ${a.media_type||""}`}); css(al,{fontSize:"9px",color:"#8792aa",marginTop:"2px",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}); copy.append(nm,al);
        const badge=elem("span",{text:t.chooseExact}); css(badge,{fontSize:"8px",padding:"4px 6px",borderRadius:"999px",background:"#244f3c",color:"#b5f6d4",whiteSpace:"nowrap"}); row.append(thumb,copy,badge);
        row.onclick=(ev)=>{ev.preventDefault();insertReferenceToken(info,exactAssetToken(g,a));}; ui.popup.append(row);
      }
      ui.popup.style.display="block";
    }

    async function showSuggestions(){
      const info=currentAtQuery(ui.textarea.value,ui.textarea.selectionStart||0); if(!info){ui.popup.style.display="none"; return;}
      const t=tr(lang); const raw=String(info.query||""); const lower=raw.toLocaleLowerCase();
      // @group/... directly switches the popup into exact-asset mode.
      const groupCandidates=[...groups].sort((a,b)=>rawGroupKey(b).length-rawGroupKey(a).length);
      for(const g of groupCandidates){
        const key=rawGroupKey(g); if(!key)continue;
        const prefix=key.toLocaleLowerCase()+"/";
        if(lower.startsWith(prefix)){
          await showAssetSuggestions(g,raw.slice(key.length+1),info); return;
        }
      }
      const matches=groups.filter(g=>`${g.alias||""} ${g.name||""} ${g.category||""}`.toLocaleLowerCase().includes(lower)).slice(0,16);
      ui.popup.innerHTML="";
      if(!matches.length){ const x=elem("div",{text:t.noGroups}); css(x,{padding:"10px",fontSize:"11px",color:"#8d96aa"}); ui.popup.append(x); ui.popup.style.display="block"; return; }
      for(const g of matches){
        const row=elem("div"); css(row,{width:"100%",display:"grid",gridTemplateColumns:"42px 1fr auto",gap:"9px",alignItems:"center",background:"transparent",borderRadius:"8px",padding:"7px",color:"#eee"}); row.onmouseenter=()=>row.style.background="#252b3a"; row.onmouseleave=()=>row.style.background="transparent";
        const thumb=elem("div"); css(thumb,{width:"42px",height:"42px",borderRadius:"7px",overflow:"hidden",background:"#0c0f15",display:"flex",alignItems:"center",justifyContent:"center",fontSize:"20px"}); if(g.effective_cover_id){const img=elem("img",{src:`/avs/library/thumb/${encodeURIComponent(g.effective_cover_id)}`}); css(img,{width:"100%",height:"100%",objectFit:"cover"}); img.onerror=()=>{thumb.innerHTML=categoryIcon(g.category)}; thumb.append(img);}else thumb.textContent=categoryIcon(g.category);
        const main=elem("button"); css(main,{minWidth:"0",textAlign:"left",background:"transparent",border:"0",color:"#eee",cursor:"pointer",padding:"0"}); const nm=elem("div",{text:g.name}); css(nm,{fontWeight:"700",fontSize:"12px"}); const al=elem("div",{text:`${displayToken(g)} · ${t.wholeGroup} · ${g.member_count||0}`}); css(al,{fontSize:"10px",color:"#8993aa",marginTop:"2px"}); main.append(nm,al); main.onclick=(ev)=>{ev.preventDefault();insertReferenceToken(info,displayToken(g));};
        const actions=elem("div"); css(actions,{display:"flex",flexDirection:"column",alignItems:"stretch",gap:"4px"}); const expand=elem("button",{text:t.expandAssets}); css(expand,{border:"1px solid #3a4661",background:"#1c2433",color:"#cbd3e7",borderRadius:"7px",padding:"5px 7px",fontSize:"9px",cursor:"pointer",whiteSpace:"nowrap"}); expand.onclick=async(ev)=>{ev.preventDefault();ev.stopPropagation();await showAssetSuggestions(g,"",info);}; actions.append(expand); row.append(thumb,main,actions); ui.popup.append(row);
      }
      ui.popup.style.display="block";
    }
    function syncPrompt(){ setWidget(node,"prompt",ui.textarea.value); renderRefs(); clearTimeout(previewTimer); previewTimer=setTimeout(()=>previewReferences(false),550); }
    async function previewReferences(showToast=false){
      const t=tr(lang); ui.preview.textContent=t.previewing;
      try{
        const d=await jsonFetch("/avs/reference/preview",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:ui.textarea.value,max_images:Number(ui.imgLimit.value||9),max_videos:Number(ui.vidLimit.value||3),max_audios:Number(ui.audLimit.value||3)})});
        const c=d.context||{}; const refs=c.references||[]; const missing=c.missing||[]; ui.preview.innerHTML="";
        renderResolvedRefs(c);
        const line=elem("span",{text:`${t.groups(refs.length)}　${t.selected((c.images||[]).length,(c.videos||[]).length,(c.audios||[]).length)}`}); ui.preview.append(line);
        if(missing.length){ const bad=elem("div",{text:`${t.missing}：${missing.join("、")}`}); css(bad,{color:"#ff8f8f",marginTop:"3px"}); ui.preview.append(bad); }
        if(showToast) toast(d.summary||t.selected((c.images||[]).length,(c.videos||[]).length,(c.audios||[]).length),missing.length>0);
      }catch(e){ui.preview.textContent=t.previewFailed(e.message); if(showToast)toast(e.message,true);}
    }

    ui.textarea.addEventListener("input",()=>{syncPrompt();showSuggestions();}); ui.textarea.addEventListener("click",showSuggestions); ui.textarea.addEventListener("keyup",showSuggestions);
    ui.textarea.addEventListener("keydown",(e)=>{ if(e.key==="Escape")ui.popup.style.display="none"; });
    document.addEventListener("click",(e)=>{ if(!ui.popup.contains(e.target)&&e.target!==ui.textarea) ui.popup.style.display="none"; });
    ui.inspect.onclick=()=>previewReferences(true);
    for(const [input,name,max] of [[ui.imgLimit,"max_images",9],[ui.vidLimit,"max_videos",3],[ui.audLimit,"max_audios",3]]) input.onchange=()=>{let v=Math.max(0,Math.min(max,Number(input.value||0)));input.value=v;setWidget(node,name,v);previewReferences(false);};
    ui.language.onchange=async()=>{lang=ui.language.value;setWidget(node,"language",lang==="en-US"?"English":"中文");applyLanguage(node,ui,lang);renderRefs();try{await jsonFetch("/avs/settings/language",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({language:lang})});}catch(_){ } window.dispatchEvent(new CustomEvent("avs-language-change",{detail:{language:lang}}));};
    window.addEventListener("avs-language-change",(e)=>{const next=e.detail?.language;if(!next||next===lang)return;lang=next;ui.language.value=lang;setWidget(node,"language",lang==="en-US"?"English":"中文");applyLanguage(node,ui,lang);renderRefs();});

    try{const s=await jsonFetch("/avs/library/status"); if(s.config?.language){lang=s.config.language;ui.language.value=lang;setWidget(node,"language",lang==="en-US"?"English":"中文");applyLanguage(node,ui,lang);}}catch(_){ }
    await loadGroups(); renderRefs(); if(ui.textarea.value.trim()) previewReferences(false);
  }
});
