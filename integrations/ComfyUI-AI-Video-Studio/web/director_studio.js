import { app } from "../../scripts/app.js";
import { createCharacterLibrary } from "./character_library.js";
import { api } from "../../scripts/api.js";
import { checkModels, applyModelPlans, renderModelPlan, installModelPreflight } from "./model_setup.js";

const EXT = "AI.Video.Studio.DirectorWorkbench.v0183RuntimeErrors";
const C = {
  bg:"#080b10", panel:"#111720", panel2:"#0c121a", panel3:"#151d28",
  border:"#303947", text:"#eef3f8", muted:"#8d99aa", green:"#59db7a",
  blue:"#62a8ff", red:"#ef6262", gold:"#e7bd65", purple:"#9d8cff"
};
const $=(tag,text="")=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
const css=(e,o)=>{Object.assign(e.style,o);return e;};
const findW=(n,k)=>n.widgets?.find(w=>w.name===k);
const vals=(w)=>w?.options?.values||w?.options||[];
const setW=(n,k,v)=>{const w=findW(n,k);if(!w)return;w.value=v;w.callback?.(v);n.graph?.setDirtyCanvas?.(true,true);};
function hideW(w){if(!w)return;w.hidden=true;w.type="hidden";w.computeSize=()=>[0,0];const el=w.inputEl||w.element||w.el;for(const h of [el,el?.parentElement,el?.closest?.(".dom-widget")]){if(!h?.style)continue;Object.assign(h.style,{display:"none",height:"0",minHeight:"0",maxHeight:"0",margin:"0",padding:"0",border:"0",overflow:"hidden",pointerEvents:"none"});}}
function collapse(node){for(const w of node.widgets||[]){if(w?.name!=="avs_director_workbench_ui")hideW(w);}}
function inp(type="text"){const e=$("input");e.type=type;return css(e,{width:"100%",boxSizing:"border-box",background:"#080c12",color:C.text,border:`1px solid ${C.border}`,borderRadius:"5px",padding:"6px 7px",fontSize:"11px"});}
function sel(){return css($("select"),{width:"100%",boxSizing:"border-box",background:"#080c12",color:C.text,border:`1px solid ${C.border}`,borderRadius:"5px",padding:"6px 7px",fontSize:"11px"});}
function ta(rows=20){const e=$("textarea");e.rows=rows;return css(e,{width:"100%",height:"100%",boxSizing:"border-box",resize:"none",background:"#070b10",color:C.text,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"10px",fontSize:"11px",lineHeight:"1.48",fontFamily:"ui-monospace,SFMono-Regular,Consolas,monospace"});}
function btn(text,kind="normal"){const e=$("button",text);const bg=kind==="primary"?"#174d2a":kind==="blue"?"#173b61":kind==="danger"?"#4c2228":kind==="gold"?"#493a16":kind==="purple"?"#32245a":"#171e28";const bd=kind==="primary"?"#3ca05a":kind==="blue"?"#3d7cc1":kind==="danger"?"#a14853":kind==="gold"?"#8e742d":kind==="purple"?"#7457c7":C.border;return css(e,{background:bg,color:C.text,border:`1px solid ${bd}`,borderRadius:"5px",padding:"6px 10px",fontSize:"11px",cursor:"pointer",fontWeight:"800",whiteSpace:"nowrap"});}
function lab(name,el){const w=css($("label"),{display:"flex",flexDirection:"column",gap:"3px",fontSize:"10px",color:C.muted,minWidth:0});w.append($("span",name),el);return w;}
function nativeBind(node,name,el,kind="text"){const w=findW(node,name);if(!w)return;if(el.tagName==="SELECT"){for(const v of vals(w)){const o=$("option",String(v));o.value=String(v);el.append(o);}el.value=String(w.value??"");}else if(kind==="checkbox")el.checked=!!w.value;else el.value=w.value??"";el.addEventListener(kind==="checkbox"?"change":"input",()=>{let v=kind==="checkbox"?el.checked:el.value;if(kind==="number")v=Number(v);setW(node,name,v);});}
function fs(values,value,cb){const s=sel();for(const v of values){const o=$("option",v);o.value=v;s.append(o);}s.value=value||values[0];s.onchange=()=>cb(s.value);return s;}
async function jf(url,opts={}){const r=await api.fetchApi(url,opts);let j={};try{j=await r.json();}catch{}if(!r.ok||j.ok===false)throw new Error(j.error||`${r.status}`);return j;}
function rawGroupKey(g){return String(g.alias||g.name||"").trim();}
function rawAssetKey(a){const x=String(a.alias||a.display_name||a.file_name||"").trim();return x.replace(/\.[^.]+$/,"");}
function exactToken(g,a){const v=`${rawGroupKey(g)}/${rawAssetKey(a)}`;return /^[A-Za-z0-9_./\-\u3400-\u9fff]+$/.test(v)?`@${v}`:`@{${v}}`;}
function apiUrl(path){try{return api.apiURL(path);}catch{return path;}}
function outputVideoUrl(meta){if(!meta?.filename)return "";const q=new URLSearchParams({filename:meta.filename,subfolder:meta.subfolder||"",type:meta.type||"output"});return apiUrl(`/view?${q.toString()}`);}
function libraryVideoUrl(assetId){return assetId?apiUrl(`/avs/library/file/${encodeURIComponent(assetId)}`):"";}
function inputMediaUrl(filename,subfolder="",type="input"){if(!filename)return "";const q=new URLSearchParams({filename,subfolder:subfolder||"",type:type||"input"});return apiUrl(`/view?${q.toString()}`);}
function slotImageUrl(slot){if(slot?.local_filename)return inputMediaUrl(slot.local_filename,slot.local_subfolder||"",slot.local_type||"input");if(slot?.asset_id)return apiUrl(`/avs/library/thumb/${encodeURIComponent(slot.asset_id)}`);return "";}
async function uploadPickedLocal(kind,file){const fd=new FormData();fd.append("file",file,file.name);return await jf(`/avs/local/upload?kind=${encodeURIComponent(kind)}`,{method:"POST",body:fd});}
function pickLocalFile(kind,accept,onDone){const f=$("input");f.type="file";f.accept=accept;f.style.display="none";f.onchange=async()=>{const file=f.files?.[0];if(!file)return;try{const j=await uploadPickedLocal(kind,file);onDone?.(j);}catch(e){alert(`本地文件导入失败：${e.message||e}`);}finally{f.remove();}};document.body.append(f);f.click();}
function videoEl(src,controls=true){const v=$("video");v.src=src;v.preload="metadata";v.muted=!controls;v.controls=controls;v.playsInline=true;css(v,{width:"100%",height:"100%",objectFit:"cover",display:"block",background:"#05070a"});if(!controls){v.addEventListener("loadedmetadata",()=>{try{v.currentTime=Math.min(.12,Math.max(0,v.duration/20));}catch{}});}return v;}
function promptTemplate(){return `subject_definitions:\n<Subject 1> is defined by <Picture 1>.\n\nsummary:\n[reference generation] Describe the complete target video segment and its internal [Shot N] sequence.\n\nretention_analysis:\n<Subject 1>: fully_preserved - keep identity, appearance, clothing and fixed design unchanged.\n\ndetailed_description:\n[Shot 1] Describe the opening action, camera, spatial relationship and exact ending state.\n\noverall_soundscape:\nDiegetic sound only, synchronized to the picture.\n\nnon_diegetic_music:\nN/A`;}
const BULK_REF_SECTIONS=["subject_definitions:","summary:","retention_analysis:","detailed_description:","overall_soundscape:","non_diegetic_music:"];
const BULK_BASE_SECTIONS=["integrated_multimodal_description:","overall_soundscape:","non_diegetic_music:"];
function normalizeAssetName(v){return String(v||"").trim().replace(/\.[^.]+$/," ").replace(/[\s_\-—–·•（）()【】\[\]{}:：/\\]+/g,"").toLowerCase();}
function promptSectionIssues(prompt,h3Mode="REF2VA"){
  const raw=String(prompt||"").toLowerCase();
  const sections=(String(h3Mode||"").toUpperCase()==="REF2VA"||raw.includes("subject_definitions:"))?BULK_REF_SECTIONS:BULK_BASE_SECTIONS;
  const pos=sections.map(x=>raw.indexOf(x));const missing=sections.filter((_,i)=>pos[i]<0);let ordered=true,last=-1;for(const q of pos){if(q<0)continue;if(q<last){ordered=false;break;}last=q;}
  return{missing,ordered,sections};
}
function parsePictureBindingText(text){const out={};for(const part of String(text||"").split(/[；;,，]+/)){const m=part.trim().match(/^(?:picture\s*|p)\s*([1-9])\s*(?:=|:|：)\s*(.+)$/i);if(m)out[Number(m[1])]=m[2].trim();}return out;}
function parseSpeakerBindingText(text){const out={};for(const part of String(text||"").split(/[；;,，]+/)){const m=part.trim().match(/^(s\d+)\s*(?:=|:|：)\s*(.+)$/i);if(m)out[m[1].toUpperCase()]=m[2].trim();}return out;}
function groupId(prefix,value,fallback="01"){const raw=String(value||"").trim();const direct=raw.match(new RegExp(`^${prefix}\\s*[-_]?\\s*(\\d+)`,"i"));if(direct)return `${prefix}${String(Number(direct[1])).padStart(2,"0")}`;const numbered=raw.match(/(?:第\s*)?(\d+)\s*(?:集|场|幕|章)?/);if(numbered)return `${prefix}${String(Number(numbered[1])).padStart(2,"0")}`;const key=raw.replace(/[^0-9A-Za-z\u3400-\u9fff]+/g,"_").replace(/^_+|_+$/g,"").slice(0,28);return key?`${prefix}_${key}`:`${prefix}${fallback}`;}
function inferSceneName(name){const parts=String(name||"").split(/[｜|]/).map(x=>x.trim()).filter(Boolean);return parts.length>1?parts[0]:"未分场";}
function applyGroupDefaults(x,i=0){x.episode_name=String(x.episode_name||x.episode||"第1集").trim()||"第1集";x.episode_id=String(x.episode_id||groupId("EP",x.episode_name,"01")).trim();x.scene_name=String(x.scene_name||x.scene||inferSceneName(x.name)).trim()||"未分场";x.scene_id=String(x.scene_id||groupId("SC",x.scene_name,String(i+1).padStart(2,"0"))).trim();return x;}
function pictureRefsFromPrompt(prompt){const out=[];for(const m of String(prompt||"").matchAll(/<Picture\s+(\d+)>/gi))out.push(Number(m[1]));return [...new Set(out)].sort((a,b)=>a-b);}
function bulkBindingIssues(block){const errors=[],warnings=[];const refs=pictureRefsFromPrompt(block.prompt);const bound=Object.keys(block.bindings||{}).map(Number);for(const n of refs){if(n<1||n>9)errors.push(`Picture ${n} 超出1-9`);else if(!bound.includes(n))errors.push(`Picture ${n} 未绑定`);}for(const n of bound)if(!refs.includes(n))errors.push(`P${n} 已绑定但 Prompt 没有引用`);if(!["独立生成","续写上一段"].includes(block.continuity))errors.push("连续性缺失/非法");if(![true,false].includes(block.inherit_previous_audio))errors.push("继承尾音非法");return{errors,warnings};}
function parseBulkPromptText(text){
  const raw=String(text||"").replace(/\r\n?/g,"\n").replace(/^```(?:text|md|markdown)?\s*$/gmi,"").replace(/^```\s*$/gmi,"");
  const lines=raw.split("\n"),blocks=[];let cur=null,lastEpisodeId="EP01",lastEpisodeName="第1集";
  const push=()=>{if(!cur)return;applyGroupDefaults(cur,blocks.length);lastEpisodeId=cur.episode_id||lastEpisodeId;lastEpisodeName=cur.episode_name||lastEpisodeName;cur.prompt=cur.promptLines.join("\n").trim();delete cur.promptLines;cur.section_issues=promptSectionIssues(cur.prompt,cur.h3_mode);cur.binding_issues=bulkBindingIssues(cur);blocks.push(cur);cur=null;};
  for(const line of lines){
    const t=line.trim();
    const am=t.match(/^【(?:隐藏空间预热|空间预热|空间锁)\s*([^｜|】]*)\s*[｜|]\s*(?:时长\s*[:：]?\s*)?([0-9.]+)\s*(?:秒|s)(?:\s*[｜|]\s*(.*?))?】$/i);
    if(am){push();const lockId=String(am[1]||`LOCK_${blocks.length+1}`).trim()||`LOCK_${blocks.length+1}`,dur=Math.max(.2,Math.min(15.1,Number(am[2]||1))),name=(am[3]||`隐藏空间预热 ${lockId}`).trim();cur={index:blocks.length+1,duration:dur,name,h3_mode:"REF2VA",continuity:"独立生成",inherit_previous_audio:false,generation_mode:"single",segment_role:"hidden_anchor",include_in_final:false,spatial_lock_id:lockId,spatial_lock_source_id:"",episode_id:lastEpisodeId,episode_name:lastEpisodeName,scene_id:"",scene_name:inferSceneName(name),bindings:{},speaker_bindings:{},promptLines:[],promptStarted:false};continue;}
    const hm=t.match(/^【(?:(?:视频片段|视频段)\s*(\d+)|第\s*(\d+)\s*段)\s*[｜|]\s*(?:时长\s*[:：]?\s*)?([0-9.]+)\s*(?:秒|s)(?:\s*[｜|]\s*(.*?))?】$/i);
    if(hm){push();const idx=Number(hm[1]||hm[2]||blocks.length+1),dur=Math.max(.2,Math.min(15.1,Number(hm[3]||5))),name=(hm[4]||`视频段${idx}`).trim();cur={index:idx,duration:dur,name,h3_mode:"REF2VA",continuity:"",inherit_previous_audio:false,generation_mode:"single",segment_role:"content",include_in_final:true,spatial_lock_id:"",spatial_lock_source_id:"",episode_id:lastEpisodeId,episode_name:lastEpisodeName,scene_id:"",scene_name:inferSceneName(name),bindings:{},speaker_bindings:{},promptLines:[],promptStarted:false};continue;}
    if(!cur){if(!t)continue;let gm=t.match(/^【(?:集数|Episode|EP)】\s*(.+)$/i)||t.match(/^【第\s*(\d+)\s*集】$/);if(gm){const v=gm[2]?`第${gm[2]}集`:String(gm[1]||"").trim();lastEpisodeName=v;lastEpisodeId=groupId("EP",v,"01");continue;}if(/^(subject_definitions|integrated_multimodal_description)\s*:/i.test(t)||/^(For the target video|How the reference pictures align)/i.test(t)){cur={index:1,duration:5,name:"视频段1",h3_mode:/subject_definitions/i.test(t)?"REF2VA":"FL2VA",continuity:"独立生成",inherit_previous_audio:false,generation_mode:"single",episode_id:lastEpisodeId,episode_name:lastEpisodeName,scene_id:"SC01",scene_name:"未分场",bindings:{},speaker_bindings:{},promptLines:[line],promptStarted:true};}continue;}
    if(!cur.promptStarted&&(/^(subject_definitions|integrated_multimodal_description)\s*:/i.test(t)||/^(For the target video|How the reference pictures align)/i.test(t))){cur.promptStarted=true;cur.promptLines.push(line);continue;}
    if(!cur.promptStarted){
      let m=t.match(/^【(?:集数|Episode|EP)】\s*(.+)$/i);if(m){const v=String(m[1]||"").trim(),parts=v.split(/[｜|]/).map(x=>x.trim()).filter(Boolean);if(parts.length>1&&/^EP/i.test(parts[0])){cur.episode_id=groupId("EP",parts[0],"01");cur.episode_name=parts.slice(1).join("｜");}else{cur.episode_name=v;cur.episode_id=groupId("EP",v,"01");}continue;}
      m=t.match(/^【(?:场景|Scene)】\s*(.+)$/i);if(m){const v=String(m[1]||"").trim(),parts=v.split(/[｜|]/).map(x=>x.trim()).filter(Boolean);if(parts.length>1&&/^SC/i.test(parts[0])){cur.scene_id=groupId("SC",parts[0],"01");cur.scene_name=parts.slice(1).join("｜");}else{cur.scene_name=v;cur.scene_id=groupId("SC",v,"01");}continue;}
      m=t.match(/^【场景ID】\s*(.+)$/i);if(m){cur.scene_id=groupId("SC",String(m[1]||"").trim(),"01");continue;}
      m=t.match(/^【H3模式】\s*(.+)$/i);if(m){cur.h3_mode=String(m[1]||"REF2VA").trim().toUpperCase();continue;}
      m=t.match(/^【段类型】\s*(.+)$/);if(m){const v=String(m[1]||"");cur.segment_role=/隐藏|预热|空间锁|hidden|anchor|lock/i.test(v)?"hidden_anchor":"content";cur.include_in_final=cur.segment_role!=="hidden_anchor";continue;}
      m=t.match(/^【成片】\s*(.+)$/);if(m){cur.include_in_final=/^(是|true|1|保留|yes)$/i.test(String(m[1]||"").trim());if(!cur.include_in_final)cur.segment_role="hidden_anchor";continue;}
      m=t.match(/^【空间锁ID】\s*(.+)$/i);if(m){cur.spatial_lock_id=String(m[1]||"").trim();continue;}
      m=t.match(/^【空间锁来源】\s*(.+)$/i);if(m){cur.spatial_lock_source_id=String(m[1]||"").trim();continue;}
      m=t.match(/^【连续性】\s*(.+)$/);if(m){cur.continuity=/独立/.test(m[1])?"独立生成":"续写上一段";continue;}
      m=t.match(/^【继承(?:尾音|上一段音频)】\s*(.+)$/);if(m){cur.inherit_previous_audio=/^(是|true|1|开|开启|yes)$/i.test(m[1].trim());continue;}
      m=t.match(/^【生成模式】\s*(.+)$/);if(m){cur.generation_mode=/抽卡/.test(m[1])?"draw":"single";continue;}
      m=t.match(/^【Picture绑定】\s*(.+)$/i);if(m){Object.assign(cur.bindings,parsePictureBindingText(m[1]));continue;}
      m=t.match(/^【Speaker绑定】\s*(.+)$/i);if(m){Object.assign(cur.speaker_bindings,parseSpeakerBindingText(m[1]));continue;}
      if(/^(?:picture\s*|p)[1-9]\s*(?:=|:|：)/i.test(t)){Object.assign(cur.bindings,parsePictureBindingText(t));continue;}
      if(!t)continue;
    }
    if(cur.promptStarted)cur.promptLines.push(line);
  }
  push();return blocks.filter(x=>x.prompt);
}
function blankSlots(){return Array.from({length:9},(_,i)=>({slot:i+1,token:"",asset_id:"",name:"",group_name:"",local_path:"",local_filename:"",local_subfolder:"",local_type:""}));}
function sameStoryGroup(a,b){if(!a||!b)return false;const ae=String(a.episode_id||a.episode_name||"").trim(),be=String(b.episode_id||b.episode_name||"").trim(),as=String(a.scene_id||a.scene_name||"").trim(),bs=String(b.scene_id||b.scene_name||"").trim();if(ae&&be&&ae!==be)return false;if(as&&bs&&as!==bs)return false;return true;}
function isHiddenAnchor(s){return !!s&&(String(s.segment_role||"")==="hidden_anchor"||s.include_in_final===false);}
function segmentInFinal(s){return !!s&&!isHiddenAnchor(s)&&s.include_in_final!==false;}
function groupBoundaryAt(shots,i){return i<=0||!sameStoryGroup(shots?.[i],shots?.[i-1]);}
function normalizeGroupContinuity(shots){if(!Array.isArray(shots))return shots;for(let i=0;i<shots.length;i++){const s=shots[i];if(!s)continue;if(isHiddenAnchor(s)){s.segment_role="hidden_anchor";s.include_in_final=false;s.continuity="独立生成";s.inherit_previous_audio=false;s.generation_mode="single";continue;}const prev=i>0?shots[i-1]:null;if(prev&&isHiddenAnchor(prev)&&sameStoryGroup(s,prev)){s.continuity="续写上一段";s.inherit_previous_audio=false;if(!s.spatial_lock_source_id)s.spatial_lock_source_id=prev.spatial_lock_id||prev.id||"";continue;}if(groupBoundaryAt(shots,i)&&s.continuity==="续写上一段"){s.continuity="独立生成";s.inherit_previous_audio=false;}}return shots;}
function defaultSegment(i=0){return{id:`segment-${Date.now()}-${i}`,name:`视频段${i+1}`,episode_id:"EP01",episode_name:"第1集",scene_id:"SC01",scene_name:"未分场",segment_role:"content",include_in_final:true,spatial_lock_id:"",spatial_lock_source_id:"",duration:5,source_mode:"生成视频",full_prompt:promptTemplate(),image_slots:blankSlots(),picture_binding_labels:{},video_refs:"",local_video_refs:[],audio_refs:"",continuity:i===0?"独立生成":"续写上一段",guide_frames:22,guide_frame_idx:0,inherit_previous_audio:i>0,seed_mode:"随机",seed:0,existing_video_asset_id:"",existing_video_name:"",existing_video_path:"",existing_video_filename:"",existing_video_subfolder:"",existing_video_type:"",generation_mode:"single",draw_count:4,draw_seed_mode:"random",draw_rounds:[],selected_candidate_id:"",result_video:{},refined_video:{},result_status:"未生成",refine_status:"未二采",preview_variant:"best",generation_summary:"",generation_dims:[],refine_summary:"",refine_dims:[]};}
function sectionBody(prompt,name){const raw=String(prompt||"");const m=raw.match(new RegExp(`(?:^|\n)${name}\s*:\s*([\s\S]*?)(?=\n(?:subject_definitions|summary|retention_analysis|detailed_description|overall_soundscape|non_diegetic_music)\s*:|$)`,"i"));return String(m?.[1]||"").trim();}
function hiddenAnchorPrompt(base){const sd=sectionBody(base?.full_prompt,"subject_definitions")||"Keep the same named characters and their bound Picture references.";const ra=sectionBody(base?.full_prompt,"retention_analysis")||"All characters: fully_preserved - preserve identity, clothing and fixed design.";return `subject_definitions:
${sd}

summary:
[production-only hidden spatial lock] Establish the complete 2-5 person dialogue layout before editorial close-ups. This approximately one-second clip is not part of the final movie.

retention_analysis:
${ra}

detailed_description:
[Shot 1] Use a stable wide or medium-wide group shot showing every dialogue participant at the same time. Preserve the intended left-to-right order, foreground/midground/background depth, interpersonal distance, facing direction, eyelines, dialogue axis and key furniture/doors. Characters only breathe naturally with tiny head/eye motion. No important dialogue, no walking, no crossing, no position swap, no fast turn, no complex hand action, no camera orbit, no push/pull, no zoom, no action beat. End with a clean stable layout suitable for 22-frame AddGuide continuation.

overall_soundscape:
Room tone only. No important dialogue.

non_diegetic_music:
N/A`; }
function makeHiddenAnchorFrom(base,i){const a=defaultSegment(i);const lock=`LOCK_${String(base?.scene_id||"SC").replace(/[^0-9A-Za-z_\-]/g,"_")}_${Date.now().toString().slice(-6)}`;a.id=`anchor-${Date.now()}-${i}`;a.name=`空间预热｜${base?.scene_name||"当前场景"}`;a.episode_id=base?.episode_id||"EP01";a.episode_name=base?.episode_name||"第1集";a.scene_id=base?.scene_id||"SC01";a.scene_name=base?.scene_name||"未分场";a.segment_role="hidden_anchor";a.include_in_final=false;a.spatial_lock_id=lock;a.duration=1.0;a.source_mode="生成视频";a.full_prompt=hiddenAnchorPrompt(base);a.image_slots=JSON.parse(JSON.stringify(base?.image_slots||blankSlots()));a.picture_binding_labels={...(base?.picture_binding_labels||{})};if(Array.isArray(base?.character_selections))a.character_selections=JSON.parse(JSON.stringify(base.character_selections));a.video_refs="";a.local_video_refs=[];a.audio_refs="";a.continuity="独立生成";a.guide_frames=22;a.inherit_previous_audio=false;a.generation_mode="single";a.result_status="未生成";return a;}
function legacyFull(s){if(s?.full_prompt)return String(s.full_prompt);const parts=[];for(const [k,l] of [["subject_definitions","subject_definitions"],["summary","summary"],["retention_analysis","retention_analysis"],["detailed_description","detailed_description"],["overall_soundscape","overall_soundscape"],["non_diegetic_music","non_diegetic_music"]])parts.push(`${l}:\n${String(s?.[k]||"")}`);return parts.some(x=>x.trim().length>x.indexOf(":")+1)?parts.join("\n\n"):String(s?.prompt||promptTemplate());}
function migrate(s,i){const d=defaultSegment(i),x={...d,...(s||{})};x.name=x.name||`视频段${i+1}`;const role=String(s?.segment_role||s?.segment_type||"").toLowerCase();const vis=String(s?.editorial_visibility||"").toLowerCase();const hidden=["hidden_anchor","spatial_lock","anchor","lock","隐藏空间预热","空间预热","空间锁"].includes(role)||["discard","hidden","production_only"].includes(vis)||s?.counts_toward_final_runtime===false||s?.include_in_final===false;x.segment_role=hidden?"hidden_anchor":"content";x.include_in_final=!hidden;x.spatial_lock_id=String(s?.spatial_lock_id||(hidden?(s?.id||x.id):"")||"");x.spatial_lock_source_id=String(s?.spatial_lock_source_id||s?.inherit_spatial_lock_from||"");applyGroupDefaults(x,i);x.duration=Math.max(.2,Math.min(15.1,Number(x.duration||5)));x.source_mode=["已有视频","导入视频","existing"].includes(x.source_mode)?"已有视频":"生成视频";x.full_prompt=legacyFull(s||{});x.image_slots=blankSlots();if(Array.isArray(s?.image_slots))s.image_slots.slice(0,9).forEach((z,k)=>{if(typeof z==="string")x.image_slots[k].token=z;else if(z&&typeof z==="object")x.image_slots[k]={...x.image_slots[k],...z,slot:k+1};});x.picture_binding_labels=(s?.picture_binding_labels&&typeof s.picture_binding_labels==="object")?{...s.picture_binding_labels}:{};x.local_video_refs=Array.isArray(s?.local_video_refs)?s.local_video_refs.slice(0,3).filter(Boolean).map((v,k)=>({slot:k+1,name:String(v?.name||v?.filename||`参考视频${k+1}`),path:String(v?.path||""),filename:String(v?.filename||""),subfolder:String(v?.subfolder||""),type:String(v?.type||"input"),size:Number(v?.size||0)})):[];x.result_video=(s?.result_video&&typeof s.result_video==="object")?s.result_video:{};x.refined_video=(s?.refined_video&&typeof s.refined_video==="object")?s.refined_video:{};if(s?.inherit_previous_audio===undefined)x.inherit_previous_audio=i>0;else x.inherit_previous_audio=!!s.inherit_previous_audio;x.result_status=String(s?.result_status||x.result_status||"未生成");x.refine_status=String(s?.refine_status||x.refine_status||"未二采");if(!["best","source","hd","compare"].includes(String(x.preview_variant||"")))x.preview_variant="best";x.generation_mode=["single","draw"].includes(String(s?.generation_mode||""))?String(s.generation_mode):"single";x.draw_count=[2,4,6,8].includes(Number(s?.draw_count))?Number(s.draw_count):4;x.draw_seed_mode=["random","increment"].includes(String(s?.draw_seed_mode||""))?String(s.draw_seed_mode):"random";x.draw_rounds=Array.isArray(s?.draw_rounds)?s.draw_rounds:[];x.selected_candidate_id=String(s?.selected_candidate_id||"");for(const r of x.draw_rounds){if(!r||typeof r!=="object")continue;r.round_index=Number(r.round_index||1);r.candidates=Array.isArray(r.candidates)?r.candidates:[];for(const c of r.candidates){if(!c||typeof c!=="object")continue;c.candidate_id=String(c.candidate_id||`r${r.round_index}_c${r.candidates.indexOf(c)+1}`);c.seed=Number(c.seed||0);c.result_video=(c.result_video&&typeof c.result_video==="object")?c.result_video:{};c.refined_video=(c.refined_video&&typeof c.refined_video==="object")?c.refined_video:{};c.status=String(c.status||"未生成");c.refine_status=String(c.refine_status||"未二采");c.is_selected=String(c.candidate_id)===x.selected_candidate_id;}}if(isHiddenAnchor(x)){x.segment_role="hidden_anchor";x.include_in_final=false;x.duration=Math.max(.2,Math.min(15.1,Number(s?.duration||1)));x.source_mode="生成视频";x.continuity="独立生成";x.inherit_previous_audio=false;x.generation_mode="single";}return x;}
function readDoc(node){try{const d=JSON.parse(findW(node,"timeline_json")?.value||"");if(!Array.isArray(d.shots)||!d.shots.length)throw 0;d.shots=normalizeGroupContinuity(d.shots.map(migrate));d.timeline_edits=Array.isArray(d.timeline_edits)?d.timeline_edits:[];d.pending_edit=(d.pending_edit&&typeof d.pending_edit==="object")?d.pending_edit:{};d.version=9;return d;}catch{return{version:9,shots:[defaultSegment(0),defaultSegment(1)],timeline_edits:[],pending_edit:{}};}}
function saveDoc(node,d){d.version=9;d.timeline_edits=Array.isArray(d.timeline_edits)?d.timeline_edits:[];d.pending_edit=(d.pending_edit&&typeof d.pending_edit==="object")?d.pending_edit:{};setW(node,"timeline_json",JSON.stringify(d));}
function selIndex(node,d){return Math.max(0,Math.min(Number(findW(node,"selected_index")?.value||0),d.shots.length-1));}
function imgCount(s){return (s.image_slots||[]).filter(x=>x?.token||x?.asset_id||x?.local_path||x?.local_filename).length;}
function slotBound(x){return !!(x?.asset_id||x?.local_path||x?.local_filename);}
function pictureRefs(prompt){const out=[];for(const m of String(prompt||"").matchAll(/<Picture\s+(\d+)>/gi))out.push(Number(m[1]));return [...new Set(out)].sort((a,b)=>a-b);}
function compiledPictureItems(s){
  const refs=[];const seen=new Set();
  for(const m of String(s?.full_prompt||"").matchAll(/<Picture\s+(\d+)>/gi)){
    const n=Number(m[1]);if(seen.has(n))continue;seen.add(n);
    const slot=(s?.image_slots||[])[n-1]||null;
    refs.push({n,slot,bound:!!slot&&(!!slot.asset_id||!!slot.local_path||!!slot.local_filename)});
  }
  return refs;
}
function segmentIssues(s,index,shots){const errors=[],warnings=[];if(isHiddenAnchor(s)){if(s.source_mode!=="生成视频")errors.push("隐藏空间预热必须由H3生成，不能使用已有视频模式");if(Number(s.duration||1)>1.6)warnings.push("空间预热建议约0.8～1.5秒，只用于锁定位置，不进成片");if(s.continuity!=="独立生成")warnings.push("隐藏空间预热会自动按独立生成执行");}const refs=pictureRefs(s.full_prompt);for(const n of refs){if(n<1||n>9)errors.push(`Picture ${n} 超出 1-9`);else if(!slotBound((s.image_slots||[])[n-1]))errors.push(`提示词引用了 Picture ${n}，但还没选择图片`);}const bound=(s.image_slots||[]).map((x,i)=>slotBound(x)?i+1:null).filter(Boolean);if(bound.length){const max=Math.max(...bound);const gaps=[];for(let i=1;i<=max;i++)if(!bound.includes(i))gaps.push(i);if(gaps.length)warnings.push(`Picture 编号有空位（${gaps.map(x=>`P${x}`).join("、")}），生成时会自动映射；建议点“整理Picture编号”`);}if(s.source_mode==="已有视频"){if(!(s.existing_video_asset_id||s.existing_video_filename||s.existing_video_path))errors.push("当前段选择了已有视频，但还没有选视频");}else{if(!String(s.full_prompt||"").trim())errors.push("完整 H3 提示词为空");if(s.continuity==="续写上一段"){if(groupBoundaryAt(shots,index))warnings.push("当前段是新集/新场景首段，生成时会自动按独立生成处理");else{const prev=shots?.[index-1];const ok=prev&&!!segmentVideoUrl(prev);if(!ok)warnings.push("上一段还没有可用视频；点击生成当前一采时会自动从最近可用段开始补齐续写链");}}}return{errors,warnings};}
function compactPictures(s){const bound=[];const map={};(s.image_slots||[]).forEach((x,i)=>{if(slotBound(x)){map[i+1]=bound.length+1;bound.push({...x,slot:bound.length+1});}});const fresh=blankSlots();bound.forEach((x,i)=>fresh[i]={...fresh[i],...x,slot:i+1});let prompt=String(s.full_prompt||"");const tmp={};for(const [oldN,newN] of Object.entries(map)){const key=`__AVS_PIC_${oldN}__`;tmp[key]=`<Picture ${newN}>`;prompt=prompt.replace(new RegExp(`<Picture\\s+${oldN}>`,'gi'),key);}for(const [key,val] of Object.entries(tmp))prompt=prompt.replaceAll(key,val);for(const row of s.character_selections||[]){const next=map[row.picture_slot];if(next){row.picture_slot=next;if(row.previous_slot)row.previous_slot.slot=next;}}s.image_slots=fresh;s.full_prompt=prompt;return map;}
function allCandidates(s){return (s.draw_rounds||[]).flatMap(r=>Array.isArray(r?.candidates)?r.candidates:[]);}
function selectedCandidate(s){return allCandidates(s).find(c=>String(c?.candidate_id)===String(s.selected_candidate_id||""))||null;}
function candidateById(s,id){return allCandidates(s).find(c=>String(c?.candidate_id)===String(id||""))||null;}
function makeDrawRound(s){const roundIndex=(s.draw_rounds?.length||0)+1;const count=[2,4,6,8].includes(Number(s.draw_count))?Number(s.draw_count):4;const base=Number(s.seed||0);const candidates=Array.from({length:count},(_,i)=>({candidate_id:`r${roundIndex}_c${i+1}`,round_index:roundIndex,candidate_index:i+1,seed:s.draw_seed_mode==="increment"?base+i:0,result_video:{},refined_video:{},status:"等待生成",refine_status:"未二采",is_selected:false}));const round={round_index:roundIndex,candidates};s.draw_rounds=[...(s.draw_rounds||[]),round];return round;}
function chooseCandidate(s,id){s.selected_candidate_id=String(id||"");for(const c of allCandidates(s))c.is_selected=String(c.candidate_id)===s.selected_candidate_id;s.refined_video={};s.refine_status="未二采";s.preview_variant="source";}
function firstPassVideoUrl(s){if(s.source_mode==="已有视频"){if(s.existing_video_asset_id)return libraryVideoUrl(s.existing_video_asset_id);if(s.existing_video_filename)return inputMediaUrl(s.existing_video_filename,s.existing_video_subfolder||"",s.existing_video_type||"input");}const c=selectedCandidate(s);if(c?.result_video?.filename)return outputVideoUrl(c.result_video);if(s.result_video?.filename)return outputVideoUrl(s.result_video);return "";}
function refinedVideoUrl(s){const c=selectedCandidate(s);if(c?.refined_video?.filename)return outputVideoUrl(c.refined_video);return s.refined_video?.filename?outputVideoUrl(s.refined_video):"";}
function segmentVideoUrl(s){return refinedVideoUrl(s)||firstPassVideoUrl(s);}
function pictureToken(n){return `<Picture ${Number(n)}>`;}
function slotForPicture(s,n){return (s?.image_slots||[])[Number(n)-1]||{};}
function makePictureChip(s,n,onActivate){
  const slot=slotForPicture(s,n); const bound=!!(slot?.asset_id||slot?.local_path||slot?.local_filename);
  const chip=css($("span"),{display:"inline-flex",alignItems:"center",gap:"5px",verticalAlign:"middle",maxWidth:"245px",margin:"1px 3px",padding:"2px 6px 2px 3px",border:`1px solid ${bound?C.blue:"#6b3941"}`,borderRadius:"6px",background:bound?"#10243a":"#2b151a",color:C.text,cursor:"pointer",userSelect:"none",whiteSpace:"nowrap"});
  chip.contentEditable="false"; chip.dataset.picture=String(n); chip.title=bound?`${pictureToken(n)} · ${slot.name||"已绑定图片"}`:`${pictureToken(n)} · 尚未绑定图片`;
  if(bound){const im=$("img");im.src=slotImageUrl(slot);css(im,{width:"28px",height:"28px",objectFit:"cover",borderRadius:"4px",flex:"0 0 auto",background:"#05070a"});chip.append(im);}
  else chip.append(css($("span","!"),{display:"grid",placeItems:"center",width:"24px",height:"24px",borderRadius:"4px",background:"#3a1d23",color:"#ffb4b4",fontWeight:"900"}));
  const tx=css($("span"),{display:"flex",flexDirection:"column",minWidth:0,lineHeight:"1.12"});tx.append(css($("b",`Picture ${n}`),{fontSize:"10px",color:bound?"#a8d3ff":"#ffb4b4"}),css($("span",bound?(slot.name||"已绑定图片"):"未绑定图片"),{fontSize:"9px",maxWidth:"175px",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",color:bound?C.text:C.muted}));chip.append(tx);
  chip.onclick=(ev)=>{ev.preventDefault();ev.stopPropagation();onActivate?.(Number(n),chip);}; return chip;
}
function promptToRich(editor,text,s,onActivate){
  editor.innerHTML=""; const re=/<Picture\s+([1-9])>/gi; let last=0,m; const raw=String(text||"");
  const appendText=(t)=>{const parts=String(t).split("\n");parts.forEach((part,i)=>{if(part)editor.append(document.createTextNode(part));if(i<parts.length-1)editor.append($("br"));});};
  while((m=re.exec(raw))){appendText(raw.slice(last,m.index));editor.append(makePictureChip(s,Number(m[1]),onActivate));last=m.index+m[0].length;}appendText(raw.slice(last));
}
function richToPrompt(editor){
  function walk(n){if(n.nodeType===Node.TEXT_NODE)return n.nodeValue||"";if(n.nodeType!==Node.ELEMENT_NODE)return "";if(n.dataset?.picture)return pictureToken(n.dataset.picture);if(n.tagName==="BR")return "\n";let out="";for(const c of n.childNodes)out+=walk(c);if(["DIV","P"].includes(n.tagName)&&out&&!out.endsWith("\n"))out+="\n";return out;}
  let out="";for(const c of editor.childNodes)out+=walk(c);return out.replace(/\u00a0/g," ").replace(/\n{4,}/g,"\n\n\n").replace(/\n+$/," ").trimEnd();
}
function setCaretAfter(node){const r=document.createRange();r.setStartAfter(node);r.collapse(true);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);}
function insertNodeAtRange(editor,node,range){editor.focus();const sel=window.getSelection();let r=range;if(!r||!editor.contains(r.commonAncestorContainer)){r=document.createRange();r.selectNodeContents(editor);r.collapse(false);}r.deleteContents();r.insertNode(node);setCaretAfter(node);}

function removeUnusedResourceInput(node){
  const index=node.inputs?.findIndex(x=>x.name==="resource_db");if(index==null||index<0)return;
  let doc;try{doc=JSON.parse(findW(node,"timeline_json")?.value||"{}");}catch{return;}
  const needed=(doc.shots||[]).some(s=>(s.image_slots||[]).some(x=>x.asset_id&&!x.local_path)||s.existing_video_asset_id||String(s.video_refs||"").trim()||String(s.audio_refs||"").trim());
  if(needed)return;
  const link=node.graph?.links?.[node.inputs[index].link];const source=link?node.graph?.getNodeById(link.origin_id):null;
  if(link&&source?.type!=="AVSResourceLibrary")return;
  if(link)node.disconnectInput(index);
  node.removeInput?.(index);
  if(source&&(source.outputs||[]).every(o=>!o.links?.length))node.graph?.remove(source);
}

function build(node){
  collapse(node);node.title="AI视频工作室｜导演工作台";node.size=[1400,1465];node.resizable=true;
  const root=css($("div"),{height:"1400px",overflow:"visible",boxSizing:"border-box",padding:"5px",background:C.bg,color:C.text,fontFamily:"Inter,system-ui,sans-serif",position:"relative"});
  const st={doc:readDoc(node),groups:[],final_video:{},durationCache:{},durationPending:new Set(),batch:{active:false,text:"",mode:"",current:0,total:0,generated:0,skipped:0},ui:{episode:"全部",scene:"全部",status:"全部",search:"",page:1,pageSize:12}};
  let saveTimer=null;
  const isLinked=(name)=>node.inputs?.some(i=>i.name===name&&i.link!=null);
  const toastLayer=css($("div"),{position:"absolute",right:"12px",top:"58px",zIndex:500,display:"flex",flexDirection:"column",gap:"6px",pointerEvents:"none",maxWidth:"460px"});root.append(toastLayer);
  function toast(message,kind="info",ms=3200){const colors=kind==="error"?["#4c2228","#ef6262"]:kind==="warn"?["#493a16","#e7bd65"]:["#173b61","#62a8ff"];const t=css($("div",String(message||"")),{background:colors[0],border:`1px solid ${colors[1]}`,color:C.text,borderRadius:"6px",padding:"8px 10px",fontSize:"10px",lineHeight:"1.45",boxShadow:"0 8px 30px #0008",whiteSpace:"pre-wrap",pointerEvents:"auto"});toastLayer.append(t);setTimeout(()=>t.remove(),ms);}
  const persist=()=>{normalizeGroupContinuity(st.doc.shots);saveDoc(node,st.doc);updateInfo();clearTimeout(saveTimer);saveTimer=setTimeout(()=>{if(typeof saveState!=="undefined")saveState.textContent="已自动保存";},180);};
  const seg=()=>st.doc.shots[selIndex(node,st.doc)];

  const top=css($("div"),{display:"grid",gridTemplateColumns:"180px 100px 105px 115px 125px minmax(170px,1fr) auto auto auto auto",gap:"6px",alignItems:"end",padding:"6px",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px"});
  const pn=inp(),pt=sel(),ra=sel(),re=sel(),au=sel(),info=css($("div"),{fontSize:"10px",color:C.green,fontWeight:"800",padding:"7px"});
  nativeBind(node,"project_name",pn);nativeBind(node,"project_type",pt);nativeBind(node,"aspect_ratio",ra);nativeBind(node,"resolution",re);nativeBind(node,"audio_mode",au);
  const modelState=css($("div"),{display:"flex",gap:"5px",alignItems:"center",justifyContent:"flex-end",fontSize:"9px",color:C.muted});
  const modelChip=css($("span","一采模型：外接"),{padding:"5px 7px",border:`1px solid ${C.border}`,borderRadius:"5px",background:"#0d141d"});
  const refineChip=css($("span","二采：外接"),{padding:"5px 7px",border:`1px solid ${C.border}`,borderRadius:"5px",background:"#0d141d"});
  const saveState=css($("span","已自动保存"),{padding:"5px 7px",border:`1px solid ${C.border}`,borderRadius:"5px",background:"#0d141d",color:C.muted});modelState.append(modelChip,refineChip,saveState);
  const genCur=btn("生成当前一采","blue"),genToCur=btn("串行生成到当前","normal"),genAll=btn("串行生成全部一采","primary"),finalMix=btn("合成最终视频","purple");
  top.append(lab("项目",pn),lab("类型",pt),lab("画面比例",ra),lab("一采清晰度",re),lab("声音",au),info,modelState,genCur,genToCur,genAll,finalMix);root.append(top);
  function updateExternalState(){const first=node.inputs?.find(i=>i.name==="一采模型配置");const second=node.inputs?.find(i=>i.name==="二采模型配置");const refine=node.inputs?.find(i=>i.name==="二采高清设置");const ok1=first?.link!=null;const ok2=second?.link!=null;const okr=refine?.link!=null;modelChip.textContent=ok1?"一采模型 ✓":"一采模型 未接";modelChip.style.color=ok1?C.green:C.red;refineChip.textContent=okr?(ok2?"二采设置+模型 ✓":"二采设置 ✓（沿用一采模型）"):"二采设置 未接";refineChip.style.color=okr?C.gold:C.muted;}
  updateExternalState();

  const bar=css($("div"),{display:"flex",gap:"6px",alignItems:"center",padding:"6px",marginTop:"6px",background:C.panel2,border:`1px solid ${C.border}`,borderRadius:"6px 6px 0 0"});
  const add=btn("+ 视频段","primary"),addAnchor=btn("+ 空间预热","purple"),dup=btn("复制"),del=btn("删除","danger"),prev=btn("← 上一段"),next=btn("下一段 →"),bulkBtn=btn("批量导入提示词","blue"),assetPackBtn=btn("一键导入素材包","purple"),exportBtn=btn("导出项目"),importBtn=btn("导入项目");
  const peopleBtn=btn("人物库 / 本剧演员","purple");peopleBtn.onclick=()=>characterUI.open();
  bar.append(add,addAnchor,dup,del,prev,next,bulkBtn,assetPackBtn,peopleBtn,exportBtn,importBtn,css($("div","提示词导入后，可一次选择整个图片素材文件夹，按 Picture绑定 自动导入并绑定全部图片。"),{marginLeft:"auto",fontSize:"10px",color:C.muted}));root.append(bar);
  exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify(st.doc,null,2)],{type:"application/json"});const a=$("a");a.href=URL.createObjectURL(blob);a.download=`${String(pn.value||"AVS_Project").replace(/[\/:*?"<>|]/g,"_")}_director.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);toast("项目配置已导出");};
  importBtn.onclick=()=>{const f=$("input");f.type="file";f.accept="application/json,.json";f.onchange=async()=>{try{const raw=await f.files?.[0]?.text();const d=JSON.parse(raw||"");if(!Array.isArray(d.shots)||!d.shots.length)throw new Error("项目文件里没有视频段");d.shots=d.shots.map(migrate);st.doc=d;st.ui.episode="全部";st.ui.scene="全部";st.ui.status="全部";st.ui.search="";st.ui.page=1;persist();setW(node,"selected_index",0);renderAll();toast("项目配置已导入");}catch(e){toast(`导入失败：${e.message||e}`,"error",5000);}finally{f.remove();}};f.style.display="none";document.body.append(f);f.click();};

  const health=css($("div"),{display:"flex",gap:"8px",alignItems:"center",padding:"6px 9px",background:"#0b1118",border:`1px solid ${C.border}`,borderTop:"0",fontSize:"10px",minHeight:"30px",boxSizing:"border-box"});root.append(health);
  const modelNotice=css($("div"),{display:"none",maxHeight:"260px",overflow:"auto",padding:"10px",fontSize:"11px",lineHeight:"1.5",background:"#231e12",border:"1px solid #8e742d",borderRadius:"6px",marginTop:"6px"});root.append(modelNotice);
  const runtimeErrorPanel=css($("div"),{display:"none",marginTop:"6px",padding:"10px 12px",background:"#2a1116",border:`1px solid ${C.red}`,borderRadius:"7px",boxShadow:"0 10px 30px #0007"});
  const runtimeErrorHead=css($("div"),{display:"flex",alignItems:"center",gap:"8px"});
  const runtimeErrorTitle=css($("b","运行失败"),{color:"#ff8f98",fontSize:"12px"});
  const runtimeErrorClose=btn("关闭");css(runtimeErrorClose,{marginLeft:"auto",padding:"3px 7px",fontSize:"9px"});
  runtimeErrorHead.append(runtimeErrorTitle,runtimeErrorClose);
  const runtimeErrorMessage=css($("div"),{marginTop:"7px",whiteSpace:"pre-wrap",fontSize:"11px",lineHeight:"1.55",color:C.text,fontWeight:"750"});
  const runtimeErrorHint=css($("div"),{marginTop:"6px",whiteSpace:"pre-wrap",fontSize:"10px",lineHeight:"1.5",color:"#ffc5ca"});
  const runtimeErrorMeta=css($("div"),{marginTop:"6px",fontSize:"9px",color:C.muted});
  const runtimeErrorActions=css($("div"),{display:"flex",gap:"6px",marginTop:"8px",flexWrap:"wrap"});
  runtimeErrorPanel.append(runtimeErrorHead,runtimeErrorMessage,runtimeErrorHint,runtimeErrorMeta,runtimeErrorActions);root.append(runtimeErrorPanel);
  let lastRuntimeErrorKey="",lastRuntimeErrorAt=0;
  function clearRuntimeError(){runtimeErrorPanel.style.display="none";runtimeErrorMessage.textContent="";runtimeErrorHint.textContent="";runtimeErrorMeta.textContent="";runtimeErrorActions.replaceChildren();}
  runtimeErrorClose.onclick=clearRuntimeError;
  function friendlyRuntimeError(raw){
    const m=String(raw||"运行失败").replace(/^ValueError:\s*/i,"").replace(/^RuntimeError:\s*/i,"");
    if(/还没有一采完成|没有可用于二采的源视频|正式版候选可用于二采/.test(m))return{message:m,hint:"请先生成当前视频的一采；确认一采完成后，再点击“二采高清”。",recovery:"generate_first_pass"};
    if(/Turbo LoRA 与任务不匹配/.test(m))return{message:m,hint:"当前任务是 REF2VA 参考模式，但加载了不匹配的 Turbo LoRA。请关闭“匹配Turbo参数”，或换成 REF2VA 专用 Turbo。",recovery:"fix_turbo_lora"};
    if(/没有连接.*二采高清设置/.test(m))return{message:m,hint:"请把“AI视频工作室｜二采高清设置”连接到导演工作台。",recovery:"connect_refine"};
    if(/Picture/.test(m)&&/未绑定|没有选择/.test(m))return{message:m,hint:"检查当前视频段的 Picture 引用，并补齐缺失的参考图。",recovery:"bind_picture"};
    if(/cuda/i.test(m)&&/out of memory|oom/i.test(m))return{message:m,hint:"显存不足。降低分辨率、参考精度或批量大小后重试。",recovery:"oom"};
    return{message:m,hint:"请根据错误信息修改设置后重试；完整 Traceback 仍保留在 ComfyUI 日志中。",recovery:""};
  }
  function showRuntimeError(detail={}){
    const info=friendlyRuntimeError(detail.message||detail.exception_message||detail.error||"运行失败");
    const recovery=String(detail.recovery||info.recovery||"");
    const hint=String(detail.hint||info.hint||"");
    const scope=String(detail.scope||findW(node,"generation_scope")?.value||"");
    const index=Number.isInteger(Number(detail.index))?Number(detail.index):selIndex(node,st.doc);
    const key=`${info.message}|${scope}|${index}`,now=Date.now();if(key===lastRuntimeErrorKey&&now-lastRuntimeErrorAt<1200)return;lastRuntimeErrorKey=key;lastRuntimeErrorAt=now;
    runtimeErrorTitle.textContent=scope?`${scope}失败`:`运行失败`;
    runtimeErrorMessage.textContent=info.message;
    runtimeErrorHint.textContent=hint;
    runtimeErrorMeta.textContent=`视频段：${Number.isFinite(index)?`视频${index+1}`:"当前段"}${detail.exception_type?` ｜ ${detail.exception_type}`:""}`;
    runtimeErrorActions.replaceChildren();
    if(recovery==="generate_first_pass"){
      const go=btn("生成当前一采","primary");go.onclick=()=>{clearRuntimeError();setW(node,"generation_scope","当前视频段");queue("当前视频段");};runtimeErrorActions.append(go);
    }
    const dismiss=btn("知道了");dismiss.onclick=clearRuntimeError;runtimeErrorActions.append(dismiss);
    runtimeErrorPanel.style.display="block";
    const cur=st.doc.shots?.[index];if(cur){cur.last_error={message:info.message,scope,time:Date.now()};if(/二采/.test(scope))cur.refine_status="二采失败";else if(scope&&scope!=="合成最终视频")cur.result_status="生成失败";saveDoc(node,st.doc);}
    toast(info.message,"error",8000);
    renderHealth();
  }
  // v0.18.0 — 剪映式连续时间轴局部重绘。用户只拖选时间，不需要知道是否跨原始5秒段。
  const editPanel=css($("div"),{marginTop:"6px",background:"#090d13",border:`1px solid ${C.border}`,borderRadius:"6px",overflow:"hidden"});root.append(editPanel);
  const editHead=css($("div"),{display:"flex",alignItems:"center",gap:"8px",padding:"7px 9px",background:"#101720",borderBottom:`1px solid ${C.border}`});
  editHead.append(css($("b","时间轴局部重绘"),{fontSize:"12px",color:C.text}),css($("span","像剪映一样直接拖选任意已生成范围；可以跨视频段。"),{fontSize:"10px",color:C.muted}));
  const editReady=css($("span","可编辑 0.00s"),{marginLeft:"auto",fontSize:"10px",color:C.green,fontWeight:"800"});editHead.append(editReady);editPanel.append(editHead);
  const editScroller=css($("div"),{overflowX:"auto",overflowY:"hidden",padding:"10px 10px 6px",background:"#05080c"});
  const editTrack=css($("div"),{height:"82px",position:"relative",minWidth:"100%",cursor:"crosshair",userSelect:"none"});editScroller.append(editTrack);editPanel.append(editScroller);
  const editControls=css($("div"),{display:"grid",gridTemplateColumns:"115px 115px 140px 100px minmax(280px,1fr) 132px",gap:"7px",alignItems:"end",padding:"8px 9px",borderTop:`1px solid ${C.border}`,background:"#0c1219"});
  const editStart=inp(),editEnd=inp(),editMode=sel(),editContext=inp(),editPrompt=ta(),editRun=btn("生成选中区域","purple");
  editStart.type="number";editStart.step="0.04";editStart.min="0";editEnd.type="number";editEnd.step="0.04";editEnd.min="0";editContext.type="number";editContext.step="0.05";editContext.min="0.35";editContext.max="2.5";
  for(const x of ["局部修补","动作重绘","剧情重生成"]){const o=$("option",x);o.value=x;editMode.append(o);}editPrompt.rows=2;editPrompt.placeholder="只写你想改什么。例如：9–11秒女主不要坐下，改为停在桌边回头看向男主。";
  editControls.append(lab("开始时间 / s",editStart),lab("结束时间 / s",editEnd),lab("修改模式",editMode),lab("前后上下文 / s",editContext),lab("修改内容",editPrompt),editRun);editPanel.append(editControls);
  const editList=css($("div"),{display:"flex",gap:"6px",alignItems:"center",overflowX:"auto",minHeight:"34px",padding:"5px 9px",borderTop:`1px solid ${C.border}`,background:"#080d12",fontSize:"9px"});editPanel.append(editList);

  function editorialEntries(){
    let cursor=0;const out=[];
    st.doc.shots.forEach((s,i)=>{if(!segmentInFinal(s))return;const url=segmentVideoUrl(s);let dur=Number(s.duration||5);if(url&&Number.isFinite(st.durationCache[url]))dur=st.durationCache[url];out.push({s,i,url,start:cursor,end:cursor+Math.max(.04,dur),duration:Math.max(.04,dur),ready:!!url});cursor+=Math.max(.04,dur);});
    return out;
  }
  function readyTimelineEnd(){let end=0;for(const x of editorialEntries()){if(!x.ready)break;end=x.end;}return end;}
  function probeDeliveredDuration(entry){
    const url=entry.url;if(!url||st.durationCache[url]!==undefined||st.durationPending.has(url))return;st.durationPending.add(url);const v=$("video");v.preload="metadata";v.muted=true;v.onloadedmetadata=()=>{let d=Number(v.duration||entry.duration);const shot=entry.s;if(shot?.source_mode==="生成视频"&&shot?.continuity==="续写上一段"&&!groupBoundaryAt(st.doc.shots,entry.i))d=Math.max(.04,d-Number(shot.guide_frames||22)/24);st.durationCache[url]=d;st.durationPending.delete(url);v.remove();renderTimelineEditor();};v.onerror=()=>{st.durationCache[url]=Number(entry.s.duration||5);st.durationPending.delete(url);v.remove();renderTimelineEditor();};v.src=url;
  }
  function ensurePendingEdit(){if(!st.doc.pending_edit||typeof st.doc.pending_edit!=="object")st.doc.pending_edit={};return st.doc.pending_edit;}
  function setEditRange(a,b,save=false){const ready=readyTimelineEnd();a=Math.max(0,Math.min(Number(a||0),ready));b=Math.max(0,Math.min(Number(b||0),ready));if(b<a)[a,b]=[b,a];const p=ensurePendingEdit();p.start=Math.round(a*1000)/1000;p.end=Math.round(b*1000)/1000;p.mode=editMode.value||p.mode||"动作重绘";p.context=Number(editContext.value||p.context||.85);p.prompt=editPrompt.value??p.prompt??"";editStart.value=p.start.toFixed(3);editEnd.value=p.end.toFixed(3);if(save)persist();renderTimelineEditor(false);}
  function syncEditFields(){const p=ensurePendingEdit();if(!Number.isFinite(Number(p.start)))p.start=0;if(!Number.isFinite(Number(p.end)))p.end=0;editStart.value=Number(p.start||0).toFixed(3);editEnd.value=Number(p.end||0).toFixed(3);editMode.value=p.mode||"动作重绘";editContext.value=Number(p.context||.85).toFixed(2);editPrompt.value=p.prompt||"";}
  function renderTimelineEditor(probe=true){
    const entries=editorialEntries(),total=entries.length?entries.at(-1).end:0,ready=readyTimelineEnd(),px=82,width=Math.max(980,total*px);editTrack.style.width=`${width}px`;editTrack.innerHTML="";editReady.textContent=`连续可编辑 0–${ready.toFixed(2)}s`;
    if(probe)entries.forEach(probeDeliveredDuration);
    const ruler=css($("div"),{position:"absolute",left:"0",right:"0",top:"0",height:"20px",borderBottom:`1px solid ${C.border}`,pointerEvents:"none"});for(let t=0;t<=Math.ceil(total);t++){const tick=css($("div"),{position:"absolute",left:`${t*px}px`,top:"0",height:t%5===0?"18px":"9px",borderLeft:`1px solid ${t%5===0?"#6e7f91":"#35414d"}`});if(t%5===0)tick.append(css($("span",`${t}s`),{position:"absolute",left:"3px",top:"1px",fontSize:"8px",color:C.muted,whiteSpace:"nowrap"}));ruler.append(tick);}editTrack.append(ruler);
    for(const x of entries){const block=css($("div"),{position:"absolute",left:`${x.start*px}px`,top:"24px",width:`${Math.max(3,x.duration*px-2)}px`,height:"47px",boxSizing:"border-box",border:`1px solid ${x.ready?C.blue:C.border}`,background:x.ready?"#102237":"#11151a",borderRadius:"4px",overflow:"hidden",opacity:x.ready?1:.48,pointerEvents:"none"});block.append(css($("b",`${x.i+1} · ${x.s.name||`视频段${x.i+1}`}`),{display:"block",fontSize:"9px",padding:"5px 6px 1px",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",color:x.ready?C.text:C.muted}),css($("span",`${x.start.toFixed(2)}–${x.end.toFixed(2)}s${x.ready?"":" · 未生成"}`),{fontSize:"8px",padding:"0 6px",color:C.muted}));editTrack.append(block);}
    for(const e of st.doc.timeline_edits||[]){if(e?.enabled===false)continue;const a=Number(e.start||0),b=Number(e.end||0);if(!(b>a))continue;const patch=css($("div"),{position:"absolute",left:`${a*px}px`,top:"61px",width:`${Math.max(3,(b-a)*px)}px`,height:"10px",background:C.purple,borderRadius:"3px",opacity:.9,pointerEvents:"none"});patch.title=`已重绘 ${a.toFixed(2)}–${b.toFixed(2)}s`;editTrack.append(patch);}
    const p=ensurePendingEdit(),a=Math.max(0,Number(p.start||0)),b=Math.min(ready,Number(p.end||0));if(b>a){const selection=css($("div"),{position:"absolute",left:`${a*px}px`,top:"20px",width:`${Math.max(4,(b-a)*px)}px`,height:"55px",background:"#a864ff33",border:`2px solid ${C.purple}`,boxSizing:"border-box",borderRadius:"4px",pointerEvents:"none",zIndex:20});selection.append(css($("span",`${a.toFixed(2)} → ${b.toFixed(2)}s`),{position:"absolute",top:"2px",left:"4px",fontSize:"9px",fontWeight:"900",color:"#d8baff",whiteSpace:"nowrap"}));editTrack.append(selection);}
    editRun.disabled=!(b>a&&b<=ready+1e-6);editRun.style.opacity=editRun.disabled?.45:1;
    editList.innerHTML="";editList.append(css($("span","修改记录："),{color:C.muted,flex:"0 0 auto"}));const edits=st.doc.timeline_edits||[];if(!edits.length)editList.append(css($("span","暂无。每次生成都会保留为非破坏补丁，可单独撤销。"),{color:C.muted}));for(const e of edits){const chip=css($("div"),{display:"flex",alignItems:"center",gap:"5px",padding:"3px 5px",border:`1px solid ${C.border}`,borderRadius:"5px",background:"#101720",flex:"0 0 auto"});chip.append(css($("span",`${Number(e.start||0).toFixed(2)}–${Number(e.end||0).toFixed(2)}s · ${e.mode||"重绘"}`),{color:e.enabled===false?C.muted:C.text}));const patchUrl=outputVideoUrl(e.result_video||{});if(patchUrl){const pv=btn("预览","blue");css(pv,{padding:"2px 6px",fontSize:"8px"});pv.onclick=()=>window.open(patchUrl,"_blank","noopener");chip.append(pv);}const undo=btn(e.enabled===false?"恢复":"撤销",e.enabled===false?"normal":"danger");css(undo,{padding:"2px 6px",fontSize:"8px"});undo.onclick=()=>{e.enabled=e.enabled===false?true:false;persist();renderTimelineEditor();toast(e.enabled===false?"已撤销该局部补丁；原视频会重新露出。":"已恢复该局部补丁。","info");};chip.append(undo);editList.append(chip);}
  }
  // v0.18.1 — 鼠标坐标必须先从屏幕坐标换算到时间轴自身的 CSS 坐标。
  // ComfyUI 会对 DOM Widget 跟随画布做 transform: scale(...)；getBoundingClientRect()
  // 返回的是缩放后的屏幕尺寸，而 left/top/width 样式仍然使用未缩放的本地 CSS 像素。
  // 旧版直接 (clientX - rect.left) / 82，会在 115%、150% 等画布缩放下产生时间偏移。
  const EDIT_PX_PER_SECOND=82;
  function editPointerToTime(ev){
    const ready=readyTimelineEnd();
    const r=editTrack.getBoundingClientRect();
    if(!r || r.width<=0)return 0;
    // offsetWidth/clientWidth 是时间轴未经过 transform 缩放的逻辑宽度。
    const logicalWidth=Number(editTrack.offsetWidth||editTrack.clientWidth||parseFloat(editTrack.style.width)||r.width);
    const scaleX=logicalWidth/Math.max(1,r.width);
    const localX=(Number(ev.clientX)-r.left)*scaleX;
    return Math.max(0,Math.min(ready,localX/EDIT_PX_PER_SECOND));
  }
  let dragStart=null;
  editTrack.addEventListener("pointerdown",ev=>{if(ev.button!==0)return;const ready=readyTimelineEnd();if(ready<=0){toast("请先从第一段开始生成视频，再使用时间轴局部重绘。","warn");return;}dragStart=editPointerToTime(ev);setEditRange(dragStart,dragStart,false);editTrack.setPointerCapture?.(ev.pointerId);ev.preventDefault();});
  editTrack.addEventListener("pointermove",ev=>{if(dragStart==null)return;const cur=editPointerToTime(ev);setEditRange(dragStart,cur,false);});
  const finishDrag=ev=>{if(dragStart==null)return;dragStart=null;persist();renderTimelineEditor();};editTrack.addEventListener("pointerup",finishDrag);editTrack.addEventListener("pointercancel",finishDrag);
  editStart.onchange=()=>setEditRange(Number(editStart.value),Number(editEnd.value),true);editEnd.onchange=()=>setEditRange(Number(editStart.value),Number(editEnd.value),true);editMode.onchange=()=>{ensurePendingEdit().mode=editMode.value;persist();};editContext.onchange=()=>{ensurePendingEdit().context=Math.max(.35,Math.min(2.5,Number(editContext.value||.85)));persist();};editPrompt.oninput=()=>{ensurePendingEdit().prompt=editPrompt.value;clearTimeout(saveTimer);saveTimer=setTimeout(persist,220);};editRun.onclick=()=>queue("时间轴局部重绘");
  syncEditFields();
  async function inspectModels(scope=null){
    try{const result=await checkModels(app,api,String(node.id),scope);applyModelPlans(app,result);return result.ready;}
    catch(error){node._avsModelSetup({ready:false,missing:[],issues:[error.message]});return false;}
  }
  node._avsModelSetup=(plan)=>{
    renderModelPlan(modelNotice,plan,()=>inspectModels(plan.scope||null));
    const s=seg();
    if(!plan.ready){if(String(s.result_status).includes("排队"))s.result_status="待下载模型";if(String(s.refine_status).includes("排队"))s.refine_status="待下载模型";persist();renderAll();}
    else if(s.result_status==="待下载模型"||s.refine_status==="待下载模型"){if(s.result_status==="待下载模型")s.result_status=s.result_video?.filename?"一采完成":"未生成";if(s.refine_status==="待下载模型")s.refine_status=s.refined_video?.filename?"二采完成":"未二采";persist();renderAll();}
  };
  function renderHealth(){const i=selIndex(node,st.doc),s=seg(),v=segmentIssues(s,i,st.doc.shots);health.innerHTML="";const main=css($("b",v.errors.length?`当前段有 ${v.errors.length} 个问题`:v.warnings.length?`当前段可生成，但有 ${v.warnings.length} 个提醒`:"当前段检查通过 ✓"),{color:v.errors.length?C.red:v.warnings.length?C.gold:C.green});health.append(main);const msg=[...v.errors,...v.warnings].slice(0,3).join(" ｜ ");if(msg)health.append(css($("span",msg),{color:C.muted,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}));if(!isLinked("一采模型配置"))health.append(css($("span","一采模型未接"),{color:C.red,marginLeft:"auto"}));}

  const body=css($("div"),{display:"grid",gridTemplateColumns:"310px minmax(560px,1fr) 320px",gap:"7px",minHeight:"700px",height:"auto",alignItems:"start",marginTop:"7px"});
  const left=css($("div"),{overflow:"visible",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"8px"});
  const mid=css($("div"),{overflow:"hidden",display:"flex",flexDirection:"column",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"8px"});
  const right=css($("div"),{overflow:"visible",background:C.panel,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"8px"});body.append(left,mid,right);root.append(body);
  const modal=css($("div"),{display:"none",position:"absolute",inset:"12px",zIndex:200,padding:"10px",background:"#0b1018f5",border:`1px solid ${C.border}`,borderRadius:"8px",boxShadow:"0 20px 60px #000e",overflow:"auto"});root.append(modal);

  const characterUI=createCharacterLibrary({getDoc:()=>st.doc,getShot:seg,persist,repaint:()=>renderAll(),request:jf,notify:toast,upload:()=>new Promise((resolve,reject)=>{
    const file=document.createElement("input");file.type="file";file.accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff";file.style.display="none";
    file.oncancel=()=>{file.remove();resolve(null);};
    file.onchange=async()=>{try{resolve(file.files?.[0]?await uploadPickedLocal("image",file.files[0]):null);}catch(e){reject(e);}finally{file.remove();}};
    document.body.append(file);file.click();
  })});

  function updateInfo(){const formal=st.doc.shots.filter(segmentInFinal),anchors=st.doc.shots.filter(isHiddenAnchor);const sec=formal.reduce((a,s)=>a+Number(s.duration||0),0);const done=st.doc.shots.filter(s=>s.source_mode==="已有视频"||selectedCandidate(s)?.result_video?.filename||s.result_video?.filename).length;const refined=formal.filter(s=>selectedCandidate(s)?.refined_video?.filename||s.refined_video?.filename).length;info.textContent=`正式 ${formal.length} 段 · 空间预热 ${anchors.length} 段｜生产就绪 ${done}/${st.doc.shots.length}｜正式二采 ${refined} 段｜成片目标约 ${sec.toFixed(1)}s`;}
  function statusBucket(s,i){const status=`${s.result_status||""} ${s.refine_status||""}`;if(/失败|错误|error/i.test(status))return "失败";if(/处理中|排队|生成中|待下载模型/.test(status))return "生成中";const refs=pictureRefs(s.full_prompt);if(s.source_mode==="生成视频"&&refs.some(n=>n<1||n>9||!slotBound((s.image_slots||[])[n-1])))return "素材未绑定";const official=selectedCandidate(s),hasDraw=allCandidates(s).some(c=>c.result_video?.filename),hasExisting=s.source_mode==="已有视频"&&!!(s.existing_video_asset_id||s.existing_video_filename||s.existing_video_path),hasReady=hasExisting||!!official?.result_video?.filename||!!s.result_video?.filename;if(s.generation_mode==="draw"&&hasDraw&&!official)return "候选待选择";if(hasReady)return "已完成";return "待生成";}
  function filteredEntries(){const q=String(st.ui.search||"").trim().toLowerCase();return st.doc.shots.map((s,i)=>({s,i})).filter(({s,i})=>{if(st.ui.episode!=="全部"&&String(s.episode_id)!==String(st.ui.episode))return false;if(st.ui.scene!=="全部"&&String(s.scene_id)!==String(st.ui.scene))return false;if(st.ui.status!=="全部"&&statusBucket(s,i)!==st.ui.status)return false;if(q&&!`${i+1} ${s.name||""} ${s.episode_name||""} ${s.scene_name||""} ${s.full_prompt||""}`.toLowerCase().includes(q))return false;return true;});}
  function ensurePage(){const total=filteredEntries().length,pages=Math.max(1,Math.ceil(total/Number(st.ui.pageSize||12)));st.ui.page=Math.max(1,Math.min(Number(st.ui.page||1),pages));return{total,pages};}
  function syncPageForIndex(i){const rows=filteredEntries(),pos=rows.findIndex(x=>x.i===i);if(pos>=0)st.ui.page=Math.floor(pos/Number(st.ui.pageSize||12))+1;else ensurePage();}
  function setSeg(i){i=Math.max(0,Math.min(i,st.doc.shots.length-1));syncPageForIndex(i);setW(node,"selected_index",i);const target=st.doc.shots[i];if(findW(node,"generation_scope")?.value==="二采当前视频段"&&!firstPassVideoUrl(target))setW(node,"generation_scope","当前视频段");renderAll();}

  const manager=css($("div"),{padding:"7px 9px",background:"#0b1118",border:`1px solid ${C.border}`,borderTop:"0",boxSizing:"border-box"});root.append(manager);
  function tab(text,active,onClick,count=null){const b=btn(count===null?text:`${text} ${count}`,active?"blue":"normal");css(b,{padding:"4px 8px",fontSize:"9px",fontWeight:active?"900":"700"});b.onclick=onClick;return b;}
  function renderManager(){manager.innerHTML="";const title=css($("div"),{display:"flex",alignItems:"center",gap:"7px",marginBottom:"6px",flexWrap:"wrap"});title.append(css($("b","视频段管理"),{fontSize:"11px",color:C.text}),css($("span","按集数 → 场景 → 状态筛选；再配合分页，只显示当前需要处理的视频段。"),{fontSize:"9px",color:C.muted}));manager.append(title);if(st.batch?.text){manager.append(css($("div",st.batch.text),{marginBottom:"6px",padding:"6px 8px",background:"#102235",border:"1px solid #2f5f8f",borderRadius:"6px",fontSize:"10px",fontWeight:"800",color:"#9fd0ff"}));}
    const episodes=[...new Map(st.doc.shots.map(s=>[String(s.episode_id||"EP01"),{id:String(s.episode_id||"EP01"),name:String(s.episode_name||"第1集")}])).values()];const epRow=css($("div"),{display:"flex",gap:"5px",alignItems:"center",flexWrap:"wrap",marginBottom:"5px"});epRow.append(css($("span","集数"),{width:"34px",fontSize:"9px",color:C.muted,fontWeight:"900"}),tab("全部",st.ui.episode==="全部",()=>{st.ui.episode="全部";st.ui.scene="全部";st.ui.page=1;renderAll();},st.doc.shots.length));for(const e of episodes){const n=st.doc.shots.filter(s=>String(s.episode_id)===e.id).length;epRow.append(tab(e.name,st.ui.episode===e.id,()=>{st.ui.episode=e.id;st.ui.scene="全部";st.ui.page=1;renderAll();},n));}manager.append(epRow);
    const sceneSource=st.doc.shots.filter(s=>st.ui.episode==="全部"||String(s.episode_id)===String(st.ui.episode)),showScenes=st.ui.episode!=="全部"||episodes.length<=1;const scenes=showScenes?[...new Map(sceneSource.map(s=>[String(s.scene_id||"SC01"),{id:String(s.scene_id||"SC01"),name:String(s.scene_name||"未分场")}])).values()]:[];const scRow=css($("div"),{display:"flex",gap:"5px",alignItems:"center",flexWrap:"wrap",marginBottom:"5px"});scRow.append(css($("span","场景"),{width:"34px",fontSize:"9px",color:C.muted,fontWeight:"900"}),tab("全部",st.ui.scene==="全部",()=>{st.ui.scene="全部";st.ui.page=1;renderAll();},sceneSource.length));if(showScenes){for(const sc of scenes){const n=sceneSource.filter(s=>String(s.scene_id)===sc.id).length;scRow.append(tab(sc.name,st.ui.scene===sc.id,()=>{st.ui.scene=sc.id;st.ui.page=1;renderAll();},n));}}else scRow.append(css($("span","先选择具体集数，再显示该集场景"),{fontSize:"9px",color:C.muted,padding:"4px 6px"}));manager.append(scRow);
    const statBase=st.doc.shots.map((s,i)=>({s,i})).filter(({s})=>(st.ui.episode==="全部"||String(s.episode_id)===String(st.ui.episode))&&(st.ui.scene==="全部"||String(s.scene_id)===String(st.ui.scene)));const statusNames=["待生成","素材未绑定","生成中","候选待选择","已完成","失败"];const stRow=css($("div"),{display:"flex",gap:"5px",alignItems:"center",flexWrap:"wrap"});stRow.append(css($("span","状态"),{width:"34px",fontSize:"9px",color:C.muted,fontWeight:"900"}),tab("全部",st.ui.status==="全部",()=>{st.ui.status="全部";st.ui.page=1;renderAll();},statBase.length));for(const k of statusNames){const n=statBase.filter(({s,i})=>statusBucket(s,i)===k).length;if(n||st.ui.status===k)stRow.append(tab(k,st.ui.status===k,()=>{st.ui.status=k;st.ui.page=1;renderAll();},n));}manager.append(stRow);}
  const pageTools=css($("div"),{display:"grid",gridTemplateColumns:"minmax(260px,1fr) 110px 185px 190px",gap:"7px",alignItems:"end",padding:"7px 9px",background:"#0b1118",border:`1px solid ${C.border}`,borderTop:"0",boxSizing:"border-box"});
  const pageSearch=inp();pageSearch.placeholder="搜索段号 / 名称 / 场景 / Prompt";pageSearch.value=st.ui.search||"";
  const applySearch=()=>{st.ui.search=pageSearch.value;st.ui.page=1;renderTimeline();renderManager();};pageSearch.oninput=applySearch;pageSearch.onkeydown=e=>{if(e.key==="Escape"){pageSearch.value="";applySearch();}};
  const pageSizeSelect=fs(["12","24","48"],String(st.ui.pageSize||12),v=>{st.ui.pageSize=Number(v);st.ui.page=1;renderTimeline();});
  const jumpInput=inp("number");jumpInput.min="1";jumpInput.placeholder="视频段编号";const jumpBtn=btn("跳转","blue");const jumpWrap=css($("div"),{display:"grid",gridTemplateColumns:"1fr auto",gap:"5px"});jumpWrap.append(jumpInput,jumpBtn);
  const pageInfo=css($("div"),{fontSize:"10px",color:C.muted,padding:"7px 4px",textAlign:"right",whiteSpace:"nowrap"});
  const doJump=()=>{const n=Number(jumpInput.value);if(!Number.isInteger(n)||n<1||n>st.doc.shots.length){toast(`请输入 1-${st.doc.shots.length} 的有效视频段编号`,"warn");return;}st.ui.episode="全部";st.ui.scene="全部";st.ui.status="全部";st.ui.search="";pageSearch.value="";st.ui.page=Math.ceil(n/Number(st.ui.pageSize||12));setW(node,"selected_index",n-1);renderAll();};jumpBtn.onclick=doJump;jumpInput.onkeydown=e=>{if(e.key==="Enter")doJump();};
  pageTools.append(lab("搜索",pageSearch),lab("每页显示",pageSizeSelect),lab("快速跳转",jumpWrap),pageInfo);root.append(pageTools);

  const timeline=css($("div"),{display:"grid",gridTemplateColumns:"repeat(4,minmax(0,1fr))",alignContent:"start",gap:"8px",overflow:"visible",minHeight:"178px",padding:"9px",background:"#070a0f",border:`1px solid ${C.border}`,borderTop:"0",borderRadius:"0",boxSizing:"border-box"});root.append(timeline);
  const pager=css($("div"),{display:"flex",justifyContent:"center",alignItems:"center",gap:"6px",padding:"7px",background:"#0b1118",border:`1px solid ${C.border}`,borderTop:"0",borderRadius:"0 0 6px 6px",minHeight:"42px",boxSizing:"border-box"});root.append(pager);root.insertBefore(manager,body);root.insertBefore(pageTools,body);root.insertBefore(timeline,body);root.insertBefore(pager,body);
  function pageButton(text,active=false){const b=btn(String(text),active?"blue":"normal");css(b,{minWidth:"36px",padding:"5px 8px"});return b;}
  function renderPager(){pager.innerHTML="";const {total,pages}=ensurePage(),p=st.ui.page;pageInfo.textContent=`当前筛选 ${total} 段｜第 ${p}/${pages} 页`;jumpInput.max=String(st.doc.shots.length);const prevPage=pageButton("← 上一页");prevPage.disabled=p<=1;prevPage.style.opacity=p<=1?".45":"1";prevPage.onclick=()=>{st.ui.page=Math.max(1,p-1);renderTimeline();};pager.append(prevPage);const start=Math.max(1,Math.min(p-2,Math.max(1,pages-4))),end=Math.min(pages,start+4);for(let x=start;x<=end;x++){const b=pageButton(x,x===p);b.onclick=()=>{st.ui.page=x;renderTimeline();};pager.append(b);}const nextPage=pageButton("下一页 →");nextPage.disabled=p>=pages;nextPage.style.opacity=p>=pages?".45":"1";nextPage.onclick=()=>{st.ui.page=Math.min(pages,p+1);renderTimeline();};pager.append(nextPage,css($("span",`${total} 段`),{fontSize:"9px",color:C.muted,marginLeft:"5px"}));}

  function renderTimeline(){timeline.innerHTML="";const all=filteredEntries(),{total}=ensurePage(),start=(st.ui.page-1)*Number(st.ui.pageSize||12),pageItems=all.slice(start,start+Number(st.ui.pageSize||12));const rows=Math.max(1,Math.ceil(pageItems.length/4));timeline.style.height=`${rows*178+18}px`;if(!pageItems.length){timeline.append(css($("div",total?"这一页没有视频段。":"当前搜索没有匹配的视频段。"),{gridColumn:"1/-1",display:"grid",placeItems:"center",minHeight:"140px",fontSize:"11px",color:C.muted}));renderPager();return;}pageItems.forEach(({s,i})=>{const active=i===selIndex(node,st.doc),hidden=isHiddenAnchor(s);const card=css($("div"),{width:"100%",minWidth:"0",height:"170px",position:"relative",overflow:"hidden",border:`2px solid ${hidden?C.purple:(active?C.green:C.border)}`,borderRadius:"7px",background:C.panel3,cursor:"pointer",boxSizing:"border-box"});card.draggable=true;card.ondragstart=e=>{e.dataTransfer.setData("text/plain",String(i));e.dataTransfer.effectAllowed="move";card.style.opacity=".55";};card.ondragend=()=>{card.style.opacity="1";};card.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect="move";card.style.outline=`2px dashed ${C.blue}`;};card.ondragleave=()=>{card.style.outline="";};card.ondrop=e=>{e.preventDefault();card.style.outline="";const from=Number(e.dataTransfer.getData("text/plain"));if(!Number.isInteger(from)||from===i||from<0||from>=st.doc.shots.length)return;const [moved]=st.doc.shots.splice(from,1);st.doc.shots.splice(i,0,moved);persist();setW(node,"selected_index",i);syncPageForIndex(i);renderAll();toast(`已把视频段移动到第 ${i+1} 位`);};
      const url=segmentVideoUrl(s);const preview=css($("div"),{height:"118px",background:"#06080c",position:"relative",overflow:"hidden"});if(url)preview.append(videoEl(url,false));else{const first=(s.image_slots||[]).find(slotBound),imUrl=first?slotImageUrl(first):"";if(imUrl){const im=$("img");im.src=imUrl;css(im,{width:"100%",height:"100%",objectFit:"cover",display:"block",opacity:".85"});preview.append(im);}else preview.append(css($("div",s.source_mode==="已有视频"?"选择已有视频":"等待生成"),{display:"grid",placeItems:"center",height:"100%",fontSize:"12px",color:C.muted}));}
      const badge=css($("div",hidden?"LOCK":`视频${i+1}`),{position:"absolute",left:"7px",top:"7px",zIndex:4,fontSize:"9px",fontWeight:"900",background:hidden?"#2b1d4bdd":"#0a1018dd",border:`1px solid ${hidden?C.purple:(active?C.green:C.border)}`,borderRadius:"4px",padding:"3px 5px"});preview.append(badge);
      const official=selectedCandidate(s);const hasHd=!!(official?.refined_video?.filename||s.refined_video?.filename);const hasFp=!!(official?.result_video?.filename||s.result_video?.filename);const hasDraw=allCandidates(s).some(c=>c.result_video?.filename);const stat=hasHd?"二采高清":(s.source_mode==="已有视频"?"已有视频":(official?.result_video?.filename?"抽卡正式版":(s.generation_mode==="draw"&&hasDraw?"候选待选择":(hasFp?"一采完成":s.result_status||"未生成"))));const sb=css($("div",stat),{position:"absolute",right:"7px",top:"7px",zIndex:4,fontSize:"8px",fontWeight:"800",background:hasHd?"#463713dd":((hasFp||s.source_mode==="已有视频"||hasDraw)?"#113a22dd":"#252b34dd"),color:hasHd?C.gold:((hasFp||s.source_mode==="已有视频"||hasDraw)?C.green:C.muted),borderRadius:"4px",padding:"3px 5px"});preview.append(sb);
      const foot=css($("div"),{height:"52px",padding:"6px 8px",boxSizing:"border-box"});foot.append(css($("div",s.name||`视频段${i+1}`),{fontSize:"12px",fontWeight:"900",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}),css($("div",`${s.episode_name||"第1集"} · ${s.scene_name||"未分场"} · ${hidden?`隐藏预热 ${Number(s.duration||1).toFixed(1)}s · 不进成片 · `:(s.source_mode==="生成视频"?`${Number(s.duration||5).toFixed(1)}s · `:"")}P${imgCount(s)} · ${statusBucket(s,i)}`),{fontSize:"9px",color:C.muted,marginTop:"2px",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}));card.append(preview,foot);card.onclick=()=>setSeg(i);timeline.append(card);});renderPager();}

  async function loadGroups(){try{const j=await jf("/avs/library/groups");st.groups=j.groups||[];}catch{st.groups=[];}}
  function openImagePicker(slotIndex){
    const selectedShot=seg();
    pickLocalFile("image","image/png,image/jpeg,image/webp,image/bmp,image/tiff",j=>{
      const s=selectedShot;
      if(Array.isArray(s.character_selections))s.character_selections=s.character_selections.filter(r=>r.picture_slot!==slotIndex+1);
      s.image_slots[slotIndex]={slot:slotIndex+1,token:"",asset_id:"",name:j.name||j.filename||"本地图片",group_name:"本地文件",local_path:j.path||"",local_filename:j.filename||"",local_subfolder:j.subfolder||"",local_type:j.type||"input"};
      persist();renderAll();
    });
  }
  function openVideoPicker(){
    const selectedShot=seg();
    pickLocalFile("video","video/*,.mp4,.mov,.mkv,.webm,.avi,.m4v",j=>{
      const s=selectedShot;s.source_mode="已有视频";s.existing_video_asset_id="";s.existing_video_name=j.name||j.filename||"本地视频";s.existing_video_path=j.path||"";s.existing_video_filename=j.filename||"";s.existing_video_subfolder=j.subfolder||"";s.existing_video_type=j.type||"input";s.result_video={};s.refined_video={};s.refine_status="未二采";s.preview_variant="source";s.result_status="已有视频";persist();renderAll();
    });
  }

  async function buildImageAssetIndex(){
    await loadGroups();const rows=[];
    for(const g of st.groups){
      let j;try{j=await jf(`/avs/library/assets?group_id=${encodeURIComponent(g.id)}&type=image&limit=1000`);}catch{continue;}
      for(const a of (j.assets||[])){if(a.media_type&&a.media_type!=="image")continue;const names=[a.alias,a.display_name,a.file_name,`${g.alias||g.name||""}/${a.alias||a.display_name||a.file_name||""}`].filter(Boolean);rows.push({g,a,keys:[...new Set(names.map(normalizeAssetName).filter(Boolean))]});}
    }
    return rows;
  }
  function manifestNames(label,manifest){const out=[label];if(!manifest?.assets)return out;const hit=manifest.assets.find(x=>String(x?.asset_id||"")===String(label));if(!hit)return out;if(hit.output_filename)out.push(hit.output_filename);for(const a of (hit.aliases||[]))out.push(a);return [...new Set(out.filter(Boolean))];}
  function matchImageAssetStrict(index,label,manifest){const keys=manifestNames(label,manifest).map(normalizeAssetName).filter(Boolean);const hits=index.filter(x=>x.keys.some(k=>keys.includes(k)));if(hits.length===1)return hits[0];return null;}
  function suggestImageAssets(index,label,manifest){const keys=manifestNames(label,manifest).map(normalizeAssetName).filter(Boolean);const hits=index.filter(x=>x.keys.some(k=>keys.some(q=>q&&k&&(k.includes(q)||q.includes(k)))));return hits.slice(0,5);}
  async function applyBulkBindings(segments,blocks,manifest){const names=[...new Set(blocks.flatMap(b=>Object.values(b.bindings||{})).filter(Boolean))];if(!names.length)return{bound:0,missing:[],suggestions:[]};const index=await buildImageAssetIndex();let bound=0;const missing=[],suggestions=[];for(let i=0;i<segments.length;i++){const s=segments[i],b=blocks[i];for(const [slotRaw,label] of Object.entries(b.bindings||{})){const slot=Number(slotRaw);if(slot<1||slot>9)continue;const hit=matchImageAssetStrict(index,label,manifest);if(!hit){missing.push(`视频${i+1} P${slot}=${label}`);const cand=suggestImageAssets(index,label,manifest).map(x=>x.a.display_name||x.a.file_name||x.a.alias||"").filter(Boolean);if(cand.length)suggestions.push(`视频${i+1} P${slot}=${label} → 候选：${cand.join(" / ")}`);continue;}const {g,a}=hit;s.image_slots[slot-1]={slot,token:exactToken(g,a),asset_id:String(a.id||""),name:a.display_name||a.file_name||a.alias||String(label),group_name:g.name||g.alias||"",local_path:"",local_filename:"",local_subfolder:"",local_type:""};bound++;}}return{bound,missing,suggestions};}
  function imageFileSupported(file){return /\.(png|jpe?g|webp|bmp|gif|tiff?)$/i.test(String(file?.name||""));}
  function localFileRel(file){return String(file?.webkitRelativePath||file?.name||"").replace(/\\/g,"/").replace(/^\/+/,"");}
  function buildLocalFileIndex(files){const rows=[];for(const file of (files||[])){if(!imageFileSupported(file))continue;const rel=localFileRel(file),base=String(file.name||"");const names=[base,base.replace(/\.[^.]+$/,""),rel,rel.replace(/\.[^.]+$/,""),rel.split("/").slice(-2).join("/")].filter(Boolean);rows.push({file,rel,keys:[...new Set(names.map(normalizeAssetName).filter(Boolean))]});}return rows;}
  function manifestAssetForLabel(label,manifest){return manifest?.assets?.find(x=>String(x?.asset_id||"")===String(label))||null;}
  function localHitScore(row,label,manifest){
    const rel=String(row?.rel||localFileRel(row?.file)).toLowerCase(),base=String(row?.file?.name||"").toLowerCase();let score=0;
    const asset=manifestAssetForLabel(label,manifest);
    if(asset){
      const output=String(asset.output_filename||"").replace(/\\/g,"/").split("/").pop().toLowerCase();
      const dir=String(asset.relative_dir||"").replace(/\\/g,"/").replace(/^\/+|\/+$/g,"").toLowerCase();
      if(output&&base===output)score+=200;
      if(output&&dir&&rel.endsWith(`${dir}/${output}`))score+=2000;
    }
    const canonical=normalizeAssetName(label),stem=normalizeAssetName(String(row?.file?.name||"").replace(/\.[^.]+$/,""));
    if(canonical&&stem===canonical)score+=500;
    if(/\/assets\/characters\/h3\//.test(`/${rel}`)||/\/assets\/scenes\//.test(`/${rel}`)||/\/assets\/props\//.test(`/${rel}`))score+=25;
    if(/\/backup|\/backups\//.test(`/${rel}`))score-=500;
    score-=rel.split("/").length;
    return score;
  }
  function resolveLocalFileStrict(index,label,manifest){
    const keys=manifestNames(label,manifest).map(normalizeAssetName).filter(Boolean),hits=index.filter(x=>x.keys.some(k=>keys.includes(k)));
    if(hits.length===0)return{hit:null,hits,reason:"missing"};
    if(hits.length===1)return{hit:hits[0],hits,reason:"exact"};
    const ranked=[...hits].sort((a,b)=>localHitScore(b,label,manifest)-localHitScore(a,label,manifest)||String(a.rel||"").localeCompare(String(b.rel||"")));
    const topScore=localHitScore(ranked[0],label,manifest),secondScore=localHitScore(ranked[1],label,manifest);
    if(topScore>secondScore)return{hit:ranked[0],hits,reason:"preferred_path"};
    const sameName=ranked.every(x=>String(x.file?.name||"").toLowerCase()===String(ranked[0].file?.name||"").toLowerCase());
    const sameSize=ranked.every(x=>Number(x.file?.size||0)===Number(ranked[0].file?.size||0));
    if(sameName&&sameSize)return{hit:ranked[0],hits,reason:"duplicate_copy"};
    return{hit:null,hits,reason:"ambiguous"};
  }
  function matchLocalFileStrict(index,label,manifest){return resolveLocalFileStrict(index,label,manifest).hit;}
  function bindingLabelsFromSegments(segments){const out=[];for(const [i,s] of (segments||[]).entries())for(const [slot,label] of Object.entries(s.picture_binding_labels||{}))out.push({segment:i,slot:Number(slot),label:String(label||"").trim()});return out.filter(x=>x.slot>=1&&x.slot<=9&&x.label);}
  async function applyLocalFolderBindings(segments,files,manifest,onProgress=()=>{}){
    const refs=bindingLabelsFromSegments(segments);if(!refs.length)return{bound:0,missing:[],uploaded:0,duplicates:[],deduplicated:[],mode:"local"};
    const index=buildLocalFileIndex(files),matches=new Map(),missing=[],duplicates=[],deduplicated=[];
    for(const ref of refs){const resolved=resolveLocalFileStrict(index,ref.label,manifest);if(resolved.hit){matches.set(`${ref.segment}:${ref.slot}`,resolved.hit.file);if(resolved.hits.length>1)deduplicated.push(`视频${ref.segment+1} P${ref.slot}=${ref.label} → 自动选用 ${resolved.hit.rel||resolved.hit.file.name}`);}else if(resolved.reason==="missing")missing.push(`视频${ref.segment+1} P${ref.slot}=${ref.label}`);else duplicates.push(`视频${ref.segment+1} P${ref.slot}=${ref.label} → ${resolved.hits.map(x=>x.rel||x.file.name).join(" / ")}`);}
    const uniqueFiles=[...new Set(matches.values())],uploaded=new Map();let done=0;
    for(const file of uniqueFiles){onProgress(`正在导入图片 ${done+1}/${uniqueFiles.length}：${file.name}`);const j=await uploadPickedLocal("image",file);uploaded.set(file,j);done++;}
    let bound=0;
    for(const ref of refs){const file=matches.get(`${ref.segment}:${ref.slot}`),j=file?uploaded.get(file):null;if(!j)continue;const s=segments[ref.segment];s.image_slots[ref.slot-1]={slot:ref.slot,token:`@local/${String(ref.label).replace(/\s+/g,"_")}`,asset_id:"",name:ref.label,group_name:"本项目素材包",local_path:j.path||"",local_filename:j.filename||"",local_subfolder:j.subfolder||"",local_type:j.type||"input"};bound++;}
    if(deduplicated.length)console.info("AVS 素材重复副本已自动去重",deduplicated);
    return{bound,missing,uploaded:uniqueFiles.length,duplicates,deduplicated,mode:"local"};
  }
  function pickAssetFolder(onPicked){const f=$("input");f.type="file";f.multiple=true;f.accept="image/*,.png,.jpg,.jpeg,.webp,.bmp,.gif,.tif,.tiff";f.setAttribute("webkitdirectory","");f.webkitdirectory=true;f.style.display="none";f.onchange=()=>{const files=Array.from(f.files||[]).filter(imageFileSupported);try{onPicked?.(files);}finally{f.remove();}};document.body.append(f);f.click();}
  async function importAssetFolderIntoCurrentTimeline(){const refs=bindingLabelsFromSegments(st.doc.shots);if(!refs.length){toast("当前视频段没有保存 Picture绑定 标签。请用新版‘批量导入提示词’重新导入一次，然后再一键导入素材包。","warn",7000);return;}pickAssetFolder(async files=>{if(!files.length){toast("所选文件夹里没有可用图片。","warn");return;}const oldText=assetPackBtn.textContent;assetPackBtn.disabled=true;try{assetPackBtn.textContent="正在导入素材…";const manifest=st.doc.asset_manifest||null;const result=await applyLocalFolderBindings(st.doc.shots,files,manifest,msg=>{assetPackBtn.textContent=msg.length>18?"正在导入素材…":msg;});persist();renderAll();const extra=result.missing.length?`；缺少 ${result.missing.length} 个绑定`:"";const dup=result.duplicates.length?`；冲突 ${result.duplicates.length} 个`:"";toast(`素材包导入完成：上传 ${result.uploaded} 张，自动绑定 ${result.bound} 个 Picture${extra}${dup}`,result.missing.length||result.duplicates.length?"warn":"info",10000);if(result.missing.length)console.warn("AVS 素材包缺失",result.missing);if(result.duplicates.length)console.warn("AVS 素材包重名冲突",result.duplicates);}catch(e){toast(`素材包导入失败：${e.message||e}`,"error",8000);}finally{assetPackBtn.disabled=false;assetPackBtn.textContent=oldText;}});}
  function importedSegment(block,i){const s=defaultSegment(i);s.name=block.name||`视频段${i+1}`;s.episode_id=block.episode_id||"EP01";s.episode_name=block.episode_name||"第1集";s.scene_id=block.scene_id||groupId("SC",block.scene_name||inferSceneName(s.name),String(i+1).padStart(2,"0"));s.scene_name=block.scene_name||inferSceneName(s.name);s.segment_role=block.segment_role==="hidden_anchor"?"hidden_anchor":"content";s.include_in_final=s.segment_role!=="hidden_anchor"&&block.include_in_final!==false;s.spatial_lock_id=String(block.spatial_lock_id||(s.segment_role==="hidden_anchor"?s.id:"")||"");s.spatial_lock_source_id=String(block.spatial_lock_source_id||"");s.duration=Number(block.duration||(s.segment_role==="hidden_anchor"?1:5));s.full_prompt=String(block.prompt||"").trim();s.picture_binding_labels={...(block.bindings||{})};s.continuity=s.segment_role==="hidden_anchor"?"独立生成":block.continuity||(i===0?"独立生成":"续写上一段");s.inherit_previous_audio=s.segment_role==="hidden_anchor"?false:!!block.inherit_previous_audio;s.generation_mode=s.segment_role==="hidden_anchor"?"single":(block.generation_mode==="draw"?"draw":"single");s.result_status="未生成";s.refine_status="未二采";return s;}
  function openBulkPromptImporter(){
    modal.innerHTML="";modal.style.display="block";
    const head=css($("div"),{display:"flex",alignItems:"center",gap:"8px",marginBottom:"8px"});head.append(css($("div","批量导入 H3 提示词 V2 → 自动创建视频段"),{fontWeight:"900",fontSize:"15px"}));
    const fileBtn=btn("选择 H3 MD / TXT","blue"),manifestBtn=btn("选择 asset_manifest.json","purple"),folderBtn=btn("选择图片素材文件夹","gold"),manifestStat=css($("span","未加载 manifest"),{fontSize:"9px",color:C.muted}),folderStat=css($("span","未选择素材文件夹"),{fontSize:"9px",color:C.muted}),close=btn("关闭");css(close,{marginLeft:"auto"});head.append(fileBtn,manifestBtn,folderBtn,manifestStat,folderStat,close);modal.append(head);
    const guide=css($("pre",`V2 支持：
【视频片段 1｜5秒｜雨夜天台｜林野独站】
【集数】第1集
【场景】SC01｜雨夜天台
【H3模式】REF2VA
【连续性】独立生成
【继承尾音】否
【生成模式】单张生成
【Picture绑定】P1=01_人物_林野_H3主参考；P2=05_场景_学校天台_雨夜
【Speaker绑定】S1=林野
subject_definitions:
...
non_diegetic_music:
N/A

V2.5 推荐：同时选择 H3 MD、asset_manifest.json 和整个图片素材文件夹。创建视频段时，会按 Picture绑定 + 文件名/manifest 精确匹配，一次性上传并绑定全部图片。无需逐张选择。未选择素材文件夹时，才回退到永久资源库精确匹配。模糊相似项不会自动绑定。导入只创建卡片，不会立即生成视频。`),{whiteSpace:"pre-wrap",fontSize:"10px",lineHeight:"1.45",padding:"9px",background:"#0b1420",border:`1px solid ${C.blue}`,borderRadius:"6px",color:"#b9d9ff"});modal.append(guide);
    const area=ta(24);css(area,{height:"500px",marginTop:"8px"});area.placeholder="把整套 V2 H3 批量提示词粘贴到这里……";modal.append(area);
    const controls=css($("div"),{display:"grid",gridTemplateColumns:"170px 245px 1fr auto auto",gap:"8px",alignItems:"end",marginTop:"8px"});
    const mode=fs(["替换当前时间线","追加到时间线"],"替换当前时间线",()=>{});const bindBox=$("input");bindBox.type="checkbox";bindBox.checked=true;const bindWrap=css($("label"),{display:"flex",gap:"7px",alignItems:"center",fontSize:"10px",color:C.text,padding:"7px",border:`1px solid ${C.border}`,borderRadius:"5px",background:"#0b1017"});bindWrap.append(bindBox,$("span","严格按 Picture绑定 自动匹配永久资源库"));const preview=css($("div","尚未解析"),{fontSize:"10px",color:C.muted,padding:"7px"});const parseBtn=btn("解析预览","blue"),createBtn=btn("创建视频段","primary");controls.append(lab("导入方式",mode),bindWrap,preview,parseBtn,createBtn);modal.append(controls);
    let parsed=[],manifestData=null,selectedAssetFiles=[];
    const doParse=()=>{parsed=parseBulkPromptText(area.value);if(!parsed.length){preview.textContent="没有识别到视频段。检查【视频片段 N｜5秒｜名称】和 H3 Prompt 起始字段。";preview.style.color=C.red;return parsed;}const sectionBad=parsed.filter(x=>x.section_issues.missing.length||!x.section_issues.ordered);const bindingBad=parsed.filter(x=>x.binding_issues.errors.length);const picCount=parsed.reduce((n,x)=>n+Object.keys(x.bindings||{}).length,0);const speakerCount=parsed.reduce((n,x)=>n+Object.keys(x.speaker_bindings||{}).length,0);const modes=[...new Set(parsed.map(x=>x.h3_mode||"REF2VA"))].join("/");preview.textContent=`识别 ${parsed.length} 段｜H3 ${modes}｜Picture ${picCount}｜Speaker ${speakerCount}｜结构异常 ${sectionBad.length}｜绑定协议异常 ${bindingBad.length}`;preview.style.color=(sectionBad.length||bindingBad.length)?C.gold:C.green;return parsed;};
    parseBtn.onclick=doParse;area.oninput=()=>{preview.textContent="文本已修改，点击“解析预览”";preview.style.color=C.muted;};
    fileBtn.onclick=()=>{const f=$("input");f.type="file";f.accept=".txt,.md,text/plain,text/markdown";f.style.display="none";f.onchange=async()=>{try{area.value=await f.files?.[0]?.text()||"";doParse();}finally{f.remove();}};document.body.append(f);f.click();};
    manifestBtn.onclick=()=>{const f=$("input");f.type="file";f.accept=".json,application/json";f.style.display="none";f.onchange=async()=>{try{const d=JSON.parse(await f.files?.[0]?.text()||"{}");if(!Array.isArray(d.assets))throw new Error("manifest 没有 assets 数组");manifestData=d;manifestStat.textContent=`manifest：${d.assets.length} 个素材`;manifestStat.style.color=C.green;}catch(e){manifestData=null;manifestStat.textContent=`manifest错误：${e.message||e}`;manifestStat.style.color=C.red;}finally{f.remove();}};document.body.append(f);f.click();};
    folderBtn.onclick=()=>pickAssetFolder(files=>{selectedAssetFiles=files;folderStat.textContent=files.length?`素材文件夹：${files.length} 张图片`:"素材文件夹里没有可用图片";folderStat.style.color=files.length?C.green:C.red;});
    close.onclick=()=>{modal.style.display="none";};
    createBtn.onclick=async()=>{const blocks=doParse();if(!blocks.length)return;const bad=blocks.filter(x=>x.section_issues.missing.length||!x.section_issues.ordered||x.binding_issues.errors.length);if(bad.length&&!confirm(`有 ${bad.length} 段存在 H3 结构或 Picture绑定协议异常。仍然导入吗？`))return;createBtn.disabled=true;createBtn.textContent="正在创建…";try{const offset=mode.value==="追加到时间线"?st.doc.shots.length:0;const segments=blocks.map((b,i)=>importedSegment(b,offset+i));const continuityContext=mode.value==="追加到时间线"?[...st.doc.shots,...segments]:segments;normalizeGroupContinuity(continuityContext);let binding={bound:0,missing:[],suggestions:[],duplicates:[],uploaded:0};if(bindBox.checked){if(selectedAssetFiles.length){createBtn.textContent="正在导入并绑定图片…";binding=await applyLocalFolderBindings(segments,selectedAssetFiles,manifestData,msg=>{createBtn.textContent="正在导入并绑定图片…";preview.textContent=msg;preview.style.color=C.gold;});}else binding=await applyBulkBindings(segments,blocks,manifestData);}if(manifestData)st.doc.asset_manifest=manifestData;st.ui.episode="全部";st.ui.scene="全部";st.ui.status="全部";if(mode.value==="追加到时间线"){st.doc.shots.push(...segments);st.ui.search="";st.ui.page=Math.floor(offset/Number(st.ui.pageSize||12))+1;}else{st.doc.shots=segments;st.ui.search="";st.ui.page=1;}pageSearch.value="";persist();setW(node,"selected_index",mode.value==="追加到时间线"?offset:0);modal.style.display="none";renderAll();const miss=binding.missing.length?`；未精确匹配 ${binding.missing.length} 项`:"";const sug=(binding.suggestions||[]).length?`；其中 ${binding.suggestions.length} 项有候选`:"";const dup=(binding.duplicates||[]).length?`；重名冲突 ${binding.duplicates.length} 项`:"";const upl=binding.uploaded?`；已上传 ${binding.uploaded} 张素材`:"";toast(`V2.5 已创建 ${segments.length} 个视频段，自动绑定 ${binding.bound} 个 Picture${upl}${miss}${sug}${dup}`,(binding.missing.length||(binding.duplicates||[]).length)?"warn":"info",10000);if((binding.suggestions||[]).length)console.warn("AVS Picture候选（未自动绑定）",binding.suggestions);if((binding.duplicates||[]).length)console.warn("AVS 素材重名冲突",binding.duplicates);}catch(e){toast(`批量导入失败：${e.message||e}`,"error",7000);}finally{createBtn.disabled=false;createBtn.textContent="创建视频段";}};
  }
  bulkBtn.onclick=openBulkPromptImporter;
  assetPackBtn.onclick=importAssetFolderIntoCurrentTimeline;

  let promptEditor=null, promptRange=null, slotCards=[];
  let pictureMentionMenu=null, pictureMentionState=null, pictureMentionIndex=0;
  function savePromptRange(){const sel=window.getSelection();if(!promptEditor||!sel?.rangeCount)return;const r=sel.getRangeAt(0);if(promptEditor.contains(r.commonAncestorContainer))promptRange=r.cloneRange();}
  function closePictureMention(){if(pictureMentionMenu){pictureMentionMenu.remove();pictureMentionMenu=null;}pictureMentionState=null;pictureMentionIndex=0;}
  function pictureMentionContext(){
    const selection=window.getSelection();
    if(!promptEditor||!selection?.rangeCount)return null;
    const range=selection.getRangeAt(0);
    if(!range.collapsed||!promptEditor.contains(range.startContainer))return null;
    const node=range.startContainer;
    if(node.nodeType!==Node.TEXT_NODE)return null;
    const offset=range.startOffset;
    const before=String(node.nodeValue||"").slice(0,offset);
    const at=before.lastIndexOf("@");
    if(at<0)return null;
    const prefix=at>0?before[at-1]:"";
    if(prefix && !/[\s([{（【，。；：,:;]/.test(prefix))return null;
    const query=before.slice(at+1);
    if(/[\s<>\[\]{}()（）【】，。；：,:;]/.test(query))return null;
    return {node,start:at,end:offset,query};
  }
  function mentionItems(s,query=""){
    const q=String(query||"").trim().toLowerCase();
    const out=[];
    for(let i=0;i<9;i++){
      const slot=slotForPicture(s,i+1);
      if(!slotBound(slot))continue;
      const label=`Picture ${i+1} ${slot.name||"图片"} ${slot.group_name||""}`.toLowerCase();
      if(q && !label.includes(q) && !`p${i+1}`.includes(q))continue;
      out.push({n:i+1,slot});
    }
    return out;
  }
  function positionPictureMention(menu){
    const selection=window.getSelection();let rect=null;
    try{if(selection?.rangeCount){const r=selection.getRangeAt(0).cloneRange();r.collapse(true);rect=r.getBoundingClientRect();}}catch{}
    if(!rect||(!rect.width&&!rect.height)){rect=promptEditor?.getBoundingClientRect?.();}
    const vw=window.innerWidth||1600,vh=window.innerHeight||900;
    let left=Math.max(8,Math.min((rect?.left||100),vw-340));
    let top=(rect?.bottom||120)+7;
    if(top+300>vh)top=Math.max(8,(rect?.top||120)-305);
    Object.assign(menu.style,{left:`${left}px`,top:`${top}px`});
  }
  function refreshMentionActive(){
    if(!pictureMentionMenu)return;
    const rows=[...pictureMentionMenu.querySelectorAll('[data-avs-mention-row="1"]')];
    rows.forEach((r,i)=>Object.assign(r.style,{background:i===pictureMentionIndex?"#173b61":"#0d141d",borderColor:i===pictureMentionIndex?C.blue:C.border}));
  }
  function insertMentionPicture(item){
    const s=seg(),ctx=pictureMentionState;
    if(!ctx||!ctx.node?.isConnected){closePictureMention();return;}
    const r=document.createRange();
    try{r.setStart(ctx.node,ctx.start);r.setEnd(ctx.node,ctx.end);}catch{closePictureMention();return;}
    r.deleteContents();
    const chip=makePictureChip(s,item.n,(idx)=>highlightSlot(idx));
    r.insertNode(chip);
    const spacer=document.createTextNode(" ");chip.after(spacer);
    const after=document.createRange();after.setStartAfter(spacer);after.collapse(true);
    const selection=window.getSelection();selection.removeAllRanges();selection.addRange(after);promptRange=after.cloneRange();
    closePictureMention();
    s.full_prompt=richToPrompt(promptEditor);s.result_status=s.result_video?.filename?"提示词已修改":"未生成";persist();renderTimeline();
    promptEditor.focus();
  }
  function showPictureMention(ctx){
    const s=seg(),items=mentionItems(s,ctx.query);
    closePictureMention();pictureMentionState=ctx;pictureMentionIndex=0;
    const menu=css($("div"),{position:"fixed",zIndex:"999999",width:"325px",maxHeight:"290px",overflowY:"auto",padding:"6px",border:`1px solid ${C.blue}`,borderRadius:"8px",background:"#080d14",boxShadow:"0 12px 40px #000c",color:C.text,fontFamily:"Inter,system-ui,sans-serif"});
    pictureMentionMenu=menu;
    menu.append(css($("div",ctx.query?`选择图片｜搜索：${ctx.query}`:"@ 选择参考图片"),{fontSize:"10px",fontWeight:"900",color:"#a8d3ff",padding:"4px 6px 7px"}));
    if(!items.length){menu.append(css($("div",ctx.query?"没有匹配的已选图片。可继续修改关键词，或先在左侧 Picture 1–9 选择图片。":"当前还没有已选图片。请先在左侧 Picture 1–9 选择图片。"),{fontSize:"10px",lineHeight:"1.5",color:C.muted,padding:"10px",border:`1px dashed ${C.border}`,borderRadius:"6px"}));}
    items.forEach((item,i)=>{
      const row=css($("div"),{display:"grid",gridTemplateColumns:"48px 1fr auto",gap:"8px",alignItems:"center",padding:"6px",margin:"3px 0",border:`1px solid ${C.border}`,borderRadius:"6px",background:"#0d141d",cursor:"pointer"});
      row.dataset.avsMentionRow="1";
      const im=$("img");im.src=slotImageUrl(item.slot);css(im,{width:"48px",height:"48px",objectFit:"cover",borderRadius:"5px",background:"#05070a"});
      const tx=css($("div"),{minWidth:0});tx.append(css($("div",`Picture ${item.n}`),{fontSize:"10px",fontWeight:"900",color:C.blue}),css($("div",item.slot.name||"已选择图片"),{fontSize:"10px",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}),css($("div",item.slot.group_name||""),{fontSize:"8px",color:C.muted,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}));
      row.append(im,tx,css($("div","Enter"),{fontSize:"8px",color:C.muted}));
      row.onmouseenter=()=>{pictureMentionIndex=i;refreshMentionActive();};
      row.onpointerdown=e=>{e.preventDefault();e.stopPropagation();};
      row.onclick=e=>{e.preventDefault();e.stopPropagation();insertMentionPicture(item);};
      menu.append(row);
    });
    document.body.append(menu);positionPictureMention(menu);refreshMentionActive();
  }
  function maybeShowPictureMention(){const ctx=pictureMentionContext();if(ctx)showPictureMention(ctx);else closePictureMention();}
  function highlightSlot(n){const c=slotCards[Number(n)-1];if(!c)return;c.animate?.([{boxShadow:"0 0 0 0 #62a8ff"},{boxShadow:"0 0 0 3px #62a8ff"},{boxShadow:"0 0 0 0 #62a8ff"}],{duration:850});c.scrollIntoView?.({block:"nearest",behavior:"smooth"});}
  function insertPictureIntoPrompt(n){const s=seg();if(!promptEditor)return;const chip=makePictureChip(s,n,(idx)=>highlightSlot(idx));insertNodeAtRange(promptEditor,chip,promptRange);promptEditor.appendChild(document.createTextNode(" "));s.full_prompt=richToPrompt(promptEditor);s.result_status=s.result_video?.filename?"提示词已修改":"未生成";persist();renderTimeline();savePromptRange();}

  function renderImages(s){left.innerHTML="";characterUI.renderShot(left,s);slotCards=[];left.append(css($("div","参考图片｜Picture 1–9"),{fontWeight:"900",fontSize:"12px",marginBottom:"4px"}),css($("div","点击选择或更换图片，直接从电脑选文件。人物可在上方按角色绑定，场景与道具继续放在 Picture 槽位。"),{fontSize:"9px",color:C.muted,lineHeight:"1.45",marginBottom:"8px"}));const grid=css($("div"),{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"6px"});s.image_slots=blankSlots().map((x,i)=>({...x,...(s.image_slots?.[i]||{}),slot:i+1}));s.image_slots.forEach((slot,i)=>{const c=css($("div"),{height:"112px",position:"relative",border:`1px solid ${slotBound(slot)?C.blue:C.border}`,borderRadius:"6px",background:"#080c12",overflow:"hidden"});slotCards[i]=c;c.append(css($("div",`Picture ${i+1}`),{position:"absolute",left:"4px",top:"4px",zIndex:3,fontSize:"8px",fontWeight:"900",padding:"2px 4px",borderRadius:"3px",background:"#090d13dd",color:slotBound(slot)?C.blue:C.muted}));if(slot.asset_id||slot.local_path){const im=$("img");im.src=slotImageUrl(slot);css(im,{width:"100%",height:"76px",objectFit:"cover",display:"block",cursor:"pointer"});im.title="点击把这张图插入提示词";im.onclick=()=>insertPictureIntoPrompt(i+1);c.append(im,css($("div",slot.name||"已选择"),{position:"absolute",left:"4px",right:"52px",bottom:"7px",fontSize:"8px",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}));const ins=css($("button","↳"),{position:"absolute",right:"27px",bottom:"4px",width:"21px",height:"21px",padding:"0",borderRadius:"4px",border:`1px solid #3d7cc1`,background:"#173b61",color:"#fff",cursor:"pointer",fontWeight:"900"});ins.title="插入到完整 H3 提示词当前光标位置";ins.onclick=e=>{e.stopPropagation();insertPictureIntoPrompt(i+1);};const rep=css($("button","换"),{position:"absolute",right:"4px",top:"4px",zIndex:3,width:"22px",height:"20px",padding:"0",borderRadius:"4px",border:`1px solid ${C.border}`,background:"#111a25dd",color:"#fff",cursor:"pointer",fontSize:"8px"});rep.title="更换 Picture 图片";rep.onclick=e=>{e.stopPropagation();openImagePicker(i);};const x=css($("button","×"),{position:"absolute",right:"3px",bottom:"4px",width:"21px",height:"21px",padding:"0",borderRadius:"4px",border:`1px solid #81424a`,background:"#301b20",color:"#fff",cursor:"pointer"});x.title="移除 Picture 图片";x.onclick=e=>{e.stopPropagation();s.image_slots[i]={slot:i+1,token:"",asset_id:"",name:"",group_name:"",local_path:"",local_filename:"",local_subfolder:"",local_type:""};if(Array.isArray(s.character_selections))s.character_selections=s.character_selections.filter(r=>r.picture_slot!==i+1);persist();renderAll();};c.append(ins,rep,x);}else{const empty=css($("button","＋\n选择图片"),{width:"100%",height:"100%",whiteSpace:"pre-line",textAlign:"center",paddingTop:"24px",fontSize:"9px",color:C.muted,background:"transparent",border:"0",cursor:"pointer"});empty.onclick=()=>openImagePicker(i);c.append(empty);}grid.append(c);});left.append(grid);const compact=btn("整理 Picture 编号","blue");css(compact,{width:"100%",marginTop:"7px"});compact.title="把已选图片向前整理，并同步修改提示词里的 <Picture N> 编号";compact.onclick=()=>{const before=JSON.stringify(s.image_slots);compactPictures(s);persist();renderAll();toast(before===JSON.stringify(s.image_slots)?"Picture 编号已经连续":"Picture 已整理，提示词编号已同步更新");};left.append(compact);
    const hint=css($("div","提示：现在有两种插图方式：① 在提示词里直接输入 @，从弹出的图片列表选择；② 先把光标放到目标位置，再点左侧图片或 ↳。插入后显示缩略图卡片，发送 H3 时自动编译回 <Picture N>。"),{fontSize:"9px",lineHeight:"1.45",color:"#a9c9ef",padding:"8px",marginTop:"7px",border:"1px solid #294b70",borderRadius:"5px",background:"#0d1a28"});left.append(hint);
    // v0.16.8 — 额外参考视频支持直接从电脑点击上传。
    // 上传后保存在 ComfyUI/input/AI_Video_Studio/local_media，并直接进入 H3 ref_video。
    if(!Array.isArray(s.local_video_refs))s.local_video_refs=[];
    const videoBox=css($("div"),{marginTop:"9px",padding:"8px",border:`1px solid ${C.border}`,borderRadius:"7px",background:"#0a1018"});
    const videoHead=css($("div"),{display:"flex",alignItems:"center",justifyContent:"space-between",gap:"6px",marginBottom:"6px"});
    videoHead.append(css($("div","额外参考视频｜最多 3 条"),{fontSize:"10px",fontWeight:"900",color:"#b9d9ff"}));
    const addVideo=btn("＋ 选择/上传视频","blue");
    addVideo.disabled=s.local_video_refs.length>=3;
    addVideo.title=s.local_video_refs.length>=3?"H3 最多使用 3 条参考视频":"从电脑直接选择 MP4 / MOV / MKV / WEBM";
    addVideo.onclick=()=>{
      if(s.local_video_refs.length>=3){toast("最多只能绑定 3 条额外参考视频。","warn");return;}
      pickLocalFile("video","video/*,.mp4,.mov,.mkv,.webm",j=>{
        s.local_video_refs.push({slot:s.local_video_refs.length+1,name:j.name||j.filename||"参考视频",path:j.path||"",filename:j.filename||"",subfolder:j.subfolder||"",type:j.type||"input",size:Number(j.size||0)});
        persist();renderAll();toast(`参考视频已上传并绑定：${j.name||j.filename||"video"}`);
      });
    };
    videoHead.append(addVideo);videoBox.append(videoHead);
    if(!s.local_video_refs.length){
      const drop=css($("button","＋ 点击选择本地视频\n直接作为 H3 动作 / 镜头参考"),{width:"100%",minHeight:"64px",whiteSpace:"pre-line",background:"#08111c",color:"#9ecaff",border:"1px dashed #356897",borderRadius:"6px",cursor:"pointer",fontSize:"10px",lineHeight:"1.55"});
      drop.onclick=()=>addVideo.click();videoBox.append(drop);
    }else{
      s.local_video_refs.forEach((v,i)=>{
        const row=css($("div"),{display:"grid",gridTemplateColumns:"92px 1fr auto",gap:"7px",alignItems:"center",padding:"6px",marginTop:i?"6px":"0",border:`1px solid ${C.border}`,borderRadius:"6px",background:"#080d14"});
        const src=inputMediaUrl(v.filename||"",v.subfolder||"",v.type||"input");
        const pv=videoEl(src,true);css(pv,{width:"92px",height:"58px",borderRadius:"5px",objectFit:"cover"});
        const meta=css($("div"),{minWidth:0});
        meta.append(css($("div",`Video ${i+1}｜${v.name||v.filename||"参考视频"}`),{fontSize:"9px",fontWeight:"900",color:C.blue,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}),css($("div",v.filename||"已上传到本地媒体目录"),{fontSize:"8px",color:C.muted,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",marginTop:"3px"}));
        const remove=btn("删除","danger");remove.onclick=()=>{s.local_video_refs.splice(i,1);s.local_video_refs.forEach((x,k)=>x.slot=k+1);persist();renderAll();};
        row.append(pv,meta,remove);videoBox.append(row);
      });
    }
    const videoHint=css($("div","上传的视频会直接进入 MiniMax H3 的 ref_video，不需要先导入素材库，也不需要写 @引用。白模/动作参考视频建议放这里。"),{fontSize:"8px",lineHeight:"1.45",color:C.muted,marginTop:"6px"});videoBox.append(videoHint);
    left.append(videoBox);

    // 保留旧版 @素材库引用入口，兼容已有项目。
    const vr=inp();vr.value=s.video_refs||"";vr.placeholder="可选：@动作视频/某段视频（素材库引用）";vr.oninput=()=>{s.video_refs=vr.value;persist();};
    const ar=inp();ar.value=s.audio_refs||"";ar.placeholder="可选：@声音/某段音频";ar.oninput=()=>{s.audio_refs=ar.value;persist();};
    left.append(lab("素材库视频 @引用（可选）",vr),lab("额外参考音频",ar));
  }

  function renderPrompt(s){mid.innerHTML="";const head=css($("div"),{display:"flex",gap:"6px",alignItems:"center",marginBottom:"7px"});head.append(css($("div","完整 H3 提示词｜可视化 Picture 引用"),{fontWeight:"900",fontSize:"13px"}));const cp=btn("复制"),tpl=btn("插入完整模板","blue"),rawBtn=btn("查看实际文本");head.append(cp,tpl,rawBtn,css($("div","在提示词里输入 @ 或直接写 <Picture N>；编译时自动收集实际引用的图片并真正传给 H3。"),{fontSize:"9px",color:C.muted,marginLeft:"4px"}));mid.append(head);
    promptEditor=css($("div"),{width:"100%",flex:"1 1 auto",minHeight:"430px",overflow:"auto",boxSizing:"border-box",background:"#070b10",color:C.text,border:`1px solid ${C.border}`,borderRadius:"6px",padding:"11px",fontSize:"11px",lineHeight:"1.55",fontFamily:"ui-monospace,SFMono-Regular,Consolas,monospace",whiteSpace:"pre-wrap",wordBreak:"break-word",outline:"none",caretColor:"#fff"});promptEditor.contentEditable="true";promptEditor.spellcheck=false;promptToRich(promptEditor,s.full_prompt||"",s,(idx)=>highlightSlot(idx));
    let promptTimelineTimer=null;
    const sync=()=>{
      s.full_prompt=richToPrompt(promptEditor);
      s.result_status=s.result_video?.filename?"提示词已修改":"未生成";
      persist();
      savePromptRange();
      // Prompt 编辑时不要同步重绘整条时间线。长提示词/批量粘贴时，
      // renderTimeline() 会反复扫描所有段落和 Picture 引用，容易阻塞浏览器主线程。
      clearTimeout(promptTimelineTimer);
      promptTimelineTimer=setTimeout(()=>renderTimeline(),220);
    };
    promptEditor.addEventListener("paste",(e)=>{
      // 提示词编辑器的粘贴必须完全由这里接管：
      // 1) 只读取 text/plain，绝不接收 HTML / 图片 / 文件；
      // 2) 阻止事件继续冒泡到 ComfyUI 画布，避免触发其全局“粘贴图片/节点”逻辑；
      // 3) 本编辑器只保留这一处 paste 处理，避免同一次粘贴执行两遍。
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      closePictureMention();
      const text=(e.clipboardData||window.clipboardData)?.getData("text/plain")||"";
      const sel=window.getSelection();
      let r=sel?.rangeCount?sel.getRangeAt(0):null;
      if(!r||!promptEditor.contains(r.commonAncestorContainer)){
        r=document.createRange();
        r.selectNodeContents(promptEditor);
        r.collapse(false);
      }
      r.deleteContents();
      const node=document.createTextNode(text);
      r.insertNode(node);
      r.setStartAfter(node);r.collapse(true);
      sel?.removeAllRanges();sel?.addRange(r);
      promptRange=r.cloneRange();
      promptEditor.dispatchEvent(new Event("input",{bubbles:true}));
    });
    promptEditor.addEventListener("input",()=>{sync();maybeShowPictureMention();});
    promptEditor.addEventListener("keyup",()=>{savePromptRange();if(pictureMentionMenu)maybeShowPictureMention();});
    promptEditor.addEventListener("mouseup",()=>{savePromptRange();closePictureMention();});
    promptEditor.addEventListener("focus",savePromptRange);
    promptEditor.addEventListener("keydown",ev=>{
      if(pictureMentionMenu){
        const items=mentionItems(s,pictureMentionState?.query||"");
        if(ev.key==="ArrowDown"){ev.preventDefault();if(items.length){pictureMentionIndex=(pictureMentionIndex+1)%items.length;refreshMentionActive();}return;}
        if(ev.key==="ArrowUp"){ev.preventDefault();if(items.length){pictureMentionIndex=(pictureMentionIndex-1+items.length)%items.length;refreshMentionActive();}return;}
        if((ev.key==="Enter"||ev.key==="Tab")&&items.length){ev.preventDefault();insertMentionPicture(items[pictureMentionIndex]||items[0]);return;}
        if(ev.key==="Escape"){ev.preventDefault();closePictureMention();return;}
      }
      if(ev.key==="Enter"){ev.preventDefault();document.execCommand?.("insertLineBreak");sync();closePictureMention();}
    });
    mid.append(promptEditor);setTimeout(()=>{promptEditor.scrollTop=0;},0);
    const legend=css($("div"),{display:"flex",gap:"6px",alignItems:"center",marginTop:"6px",fontSize:"9px",color:C.muted});legend.append($("span","已选 Picture："));for(let i=0;i<9;i++){const sl=slotForPicture(s,i+1);if(!slotBound(sl))continue;const b=btn(`P${i+1}`);css(b,{padding:"3px 6px",fontSize:"9px"});b.title=`插入 ${pictureToken(i+1)} · ${sl.name||"图片"}`;b.onclick=()=>insertPictureIntoPrompt(i+1);legend.append(b);}mid.append(legend);
    const compiled=compiledPictureItems(s);
    const refBox=css($("div"),{marginTop:"6px",padding:"8px",border:`1px solid ${compiled.length?"#285e3b":C.border}`,borderRadius:"6px",background:compiled.length?"#0b1810":"#0b1017",fontSize:"9px",lineHeight:"1.5"});
    refBox.append(css($("div","编译时自动收集 Picture 真引用"),{fontWeight:"900",fontSize:"10px",color:compiled.length?C.green:C.muted,marginBottom:"4px"}));
    if(!compiled.length){refBox.append(css($("div","当前 Prompt 没有 <Picture N> 引用，因此生成时不会向 H3 传入 Picture 图片。直接输入 <Picture 1> 或输入 @ 选择图片都可以触发自动收集。"),{color:C.muted}));}
    else{
      for(const item of compiled){
        const name=item.slot?.name||item.slot?.local_filename||"未绑定图片";
        const row=css($("div",`${item.bound?"✓":"✕"} Picture ${item.n} → ${name}`),{color:item.bound?"#bfeccc":C.red,fontWeight:item.bound?"700":"900"});
        refBox.append(row);
      }
      refBox.append(css($("div","生成时只会加载上面这些被 Prompt 实际引用的图片；未引用的 Picture 槽位不会送入 H3。"),{color:C.muted,marginTop:"3px"}));
    }
    mid.append(refBox);
    cp.onclick=async()=>{try{const raw=richToPrompt(promptEditor);s.full_prompt=raw;persist();await navigator.clipboard.writeText(raw);cp.textContent="已复制";setTimeout(()=>cp.textContent="复制",1000);}catch{}};tpl.onclick=()=>{s.full_prompt=promptTemplate();persist();renderPrompt(s);};rawBtn.onclick=()=>{const raw=richToPrompt(promptEditor);alert(raw);};
    const note=css($("details"),{marginTop:"7px",fontSize:"10px"});note.append($("summary","续写时实际发送给 H3 的规则"));note.append(css($("pre",s.continuity==="续写上一段"?`你的完整提示词保持不变，后台额外追加：\n\ncontinuation_rule:\n- 使用上一视频段最后 ${Number(s.guide_frames||22)} 帧\n- AddGuide frame_idx = ${Number(s.guide_frame_idx||0)}\n- 上一段决定开场姿势、位置、方向和镜头连续性\n- Picture 只锁身份/武器/场景\n- ${s.inherit_previous_audio?`同时取对应尾部音频约 ${(Number(s.guide_frames||22)/24).toFixed(2)} 秒 → AddGuide.audio，延续人物音色、说话语气、呼吸和环境声，不重复上一整句台词`:`不延续上一段音频`}\n- 禁止重置姿势、瞬移、换位、突然反向`:"独立生成：不会注入上一段视频规则。"),{whiteSpace:"pre-wrap",background:"#070a0e",border:`1px solid ${C.border}`,borderRadius:"5px",padding:"8px",fontSize:"9px",color:C.muted}));mid.append(note);
  }

  function renderVideoPreview(box,s){
    box.innerHTML="";
    const hd=refinedVideoUrl(s),fp=firstPassVideoUrl(s);
    if(!hd&&!fp){
      box.append(css($("div",s.source_mode==="已有视频"?"尚未选择已有视频":"当前还没有生成完成的一采视频"),{height:"150px",display:"grid",placeItems:"center",border:`1px dashed ${C.border}`,borderRadius:"6px",color:C.muted,fontSize:"11px"}));
      return;
    }
    let mode=String(s.preview_variant||"best");
    if(mode==="best")mode=hd?"hd":"source";
    if(mode==="hd"&&!hd)mode="source";
    if(mode==="source"&&!fp)mode="hd";
    if(mode==="compare"&&!(fp&&hd))mode=hd?"hd":"source";
    const tabs=css($("div"),{display:"flex",gap:"5px",marginBottom:"6px",alignItems:"center",flexWrap:"wrap"});
    const stop=(ev)=>{ev.preventDefault();ev.stopPropagation();};
    const choose=(m)=>{s.preview_variant=m;persist();renderVideoPreview(box,s);};
    if(fp){const b=btn(s.source_mode==="已有视频"?"A｜源视频":"A｜一采",mode==="source"?"blue":"normal");b.title="查看未二采的源视频";b.onpointerdown=e=>e.stopPropagation();b.onclick=e=>{stop(e);choose("source");};tabs.append(b);}
    if(hd){const b=btn("B｜二采高清",mode==="hd"?"gold":"normal");b.title="查看二采高清结果";b.onpointerdown=e=>e.stopPropagation();b.onclick=e=>{stop(e);choose("hd");};tabs.append(b);}
    if(fp&&hd){const b=btn("A/B 同屏对比",mode==="compare"?"purple":"normal");b.title="同时播放源视频和二采高清，方便比较";b.onpointerdown=e=>e.stopPropagation();b.onclick=e=>{stop(e);choose("compare");};tabs.append(b);}
    const current=mode==="compare"?"正在查看：A/B 对比":mode==="hd"?"正在查看：B 二采高清":`正在查看：A ${s.source_mode==="已有视频"?"源视频":"一采"}`;
    tabs.append(css($("div",current),{marginLeft:"auto",fontSize:"9px",fontWeight:"800",color:mode==="hd"?C.gold:mode==="compare"?C.purple:C.blue}));
    box.append(tabs);
    const makePane=(url,label,color)=>{const pane=css($("div"),{minWidth:0});pane.append(css($("div",label),{fontSize:"9px",fontWeight:"900",color,marginBottom:"4px"}));const wrap=css($("div"),{height:"180px",border:`1px solid ${color}`,borderRadius:"6px",overflow:"hidden",background:"#05070a"});const v=videoEl(url,true);v.addEventListener("error",()=>{wrap.title="视频加载失败，可尝试刷新页面或重新选择视频";});wrap.append(v);pane.append(wrap);return pane;};
    if(mode==="compare"&&fp&&hd){
      const grid=css($("div"),{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px"});
      grid.append(makePane(fp,s.source_mode==="已有视频"?"A｜源视频":"A｜一采",C.blue),makePane(hd,"B｜二采高清",C.gold));box.append(grid);
      box.append(css($("div","A/B 对比模式：两个视频都可以单独播放、暂停和拖动时间轴。"),{fontSize:"9px",color:C.muted,marginTop:"5px",lineHeight:"1.45"}));
    }else{
      const isHd=mode==="hd"&&!!hd;const url=isHd?hd:fp;box.append(makePane(url,isHd?"B｜二采高清":(s.source_mode==="已有视频"?"A｜源视频":"A｜一采"),isHd?C.gold:C.blue));
      if(hd)box.append(css($("div",isHd?"当前显示二采高清。点击上方 A 可立即切回源视频。":"当前显示源视频。点击上方 B 可立即切回二采高清。"),{fontSize:"9px",color:isHd?C.gold:C.blue,marginTop:"5px",lineHeight:"1.45"}));
      else if(s.source_mode==="生成视频")box.append(css($("div","✓ 一采已完成。先检查人物、动作、镜头和连续性；满意后再手动二采。"),{fontSize:"9px",color:C.green,marginTop:"5px",lineHeight:"1.5",padding:"6px",background:"#0c1c12",border:"1px solid #235735",borderRadius:"5px"}));
    }
  }

  function renderDrawCandidates(s){
    const section=css($("div"),{marginTop:"9px",padding:"8px",border:`1px solid ${C.border}`,borderRadius:"7px",background:"#0a0f16"});
    const selected=selectedCandidate(s);
    const title=css($("div"),{display:"flex",gap:"6px",alignItems:"center",marginBottom:"7px"});
    title.append(css($("b","抽卡候选"),{fontSize:"11px"}),css($("span",selected?`正式版：${selected.candidate_id}｜Seed ${selected.seed||0}`:"正式版：未选择"),{marginLeft:"auto",fontSize:"9px",color:selected?C.green:C.gold,fontWeight:"800"}));
    section.append(title);
    const rounds=s.draw_rounds||[];
    if(!rounds.length){section.append(css($("div","还没有候选。点击“开始抽卡”会按同一个 Prompt / Picture / 参数生成多份结果，只改变 Seed。"),{fontSize:"9px",lineHeight:"1.5",color:C.muted,padding:"8px",border:`1px dashed ${C.border}`,borderRadius:"5px"}));right.append(section);return;}
    rounds.slice().reverse().forEach((round,ri)=>{
      const details=$("details");details.open=ri===0;css(details,{marginTop:"6px"});const sum=$("summary",`第 ${round.round_index} 轮｜${(round.candidates||[]).length} 个候选`);css(sum,{cursor:"pointer",fontSize:"10px",fontWeight:"900",color:C.blue});details.append(sum);
      const grid=css($("div"),{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px",marginTop:"6px"});
      for(const c of (round.candidates||[])){
        const isSel=String(c.candidate_id)===String(s.selected_candidate_id||"");
        const card=css($("div"),{minWidth:0,padding:"5px",border:`1px solid ${isSel?C.green:C.border}`,borderRadius:"6px",background:isSel?"#0c1c12":"#0b1118"});
        card.append(css($("div",`候选 ${c.candidate_index||""}`),{fontSize:"9px",fontWeight:"900",color:isSel?C.green:C.text}),css($("div",`Seed: ${Number(c.seed||0)||"等待生成"}`),{fontSize:"8px",color:C.muted,marginBottom:"4px"}));
        const meta=c.refined_video?.filename?c.refined_video:c.result_video;const url=meta?.filename?outputVideoUrl(meta):"";
        const media=css($("div"),{height:"92px",border:`1px solid ${C.border}`,borderRadius:"5px",overflow:"hidden",background:"#05070a"});
        if(url)media.append(videoEl(url,true));else media.append(css($("div",c.status||"等待生成"),{height:"100%",display:"grid",placeItems:"center",fontSize:"9px",color:C.muted}));card.append(media);
        const row=css($("div"),{display:"flex",gap:"4px",flexWrap:"wrap",marginTop:"5px"});
        const pick=btn(isSel?"✓ 正式版":"设为正式版",isSel?"primary":"blue");css(pick,{padding:"4px 6px",fontSize:"8px"});pick.onclick=()=>{chooseCandidate(s,c.candidate_id);persist();renderAll();toast(`已将候选 ${c.candidate_index||c.candidate_id} 设为正式版`);};row.append(pick);
        if(c.result_video?.filename){const hd=btn(c.refined_video?.filename?"重新二采":"单独二采","gold");css(hd,{padding:"4px 6px",fontSize:"8px"});hd.onclick=()=>{chooseCandidate(s,c.candidate_id);persist();renderAll();toast("已将该候选设为正式版，并开始二采");queue("二采当前视频段");};row.append(hd);}
        const delc=btn("删除","danger");css(delc,{padding:"4px 6px",fontSize:"8px"});delc.onclick=()=>{round.candidates=(round.candidates||[]).filter(x=>String(x.candidate_id)!==String(c.candidate_id));if(isSel)s.selected_candidate_id="";persist();renderAll();};row.append(delc);card.append(row);grid.append(card);
      }
      details.append(grid);section.append(details);
    });
    const ops=css($("div"),{display:"flex",gap:"5px",marginTop:"7px",flexWrap:"wrap"});
    const redraw=btn("重新抽卡","purple");redraw.onclick=()=>{makeDrawRound(s);persist();renderAll();queue("抽卡当前视频段");};
    const clear=btn("清空本轮候选","danger");clear.onclick=()=>{const last=(s.draw_rounds||[]).at(-1);if(!last)return;if((last.candidates||[]).some(c=>String(c.candidate_id)===String(s.selected_candidate_id||"")))s.selected_candidate_id="";s.draw_rounds=s.draw_rounds.slice(0,-1);persist();renderAll();};ops.append(redraw,clear);section.append(ops);right.append(section);
  }



  function renderRules(s){right.innerHTML="";right.append(css($("div","当前视频段"),{fontWeight:"900",fontSize:"12px",marginBottom:"7px"}));const nm=inp();nm.value=s.name||"";nm.oninput=()=>{s.name=nm.value;persist();renderTimeline();};right.append(lab("视频段名称",nm));const groupGrid=css($("div"),{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px",marginTop:"6px"});const epi=inp(),scn=inp();epi.value=s.episode_name||"第1集";scn.value=s.scene_name||"未分场";epi.onchange=()=>{s.episode_name=epi.value.trim()||"第1集";s.episode_id=groupId("EP",s.episode_name,"01");const i=selIndex(node,st.doc);if(groupBoundaryAt(st.doc.shots,i)){s.continuity="独立生成";s.inherit_previous_audio=false;}persist();st.ui.episode="全部";st.ui.scene="全部";st.ui.page=1;renderAll();};scn.onchange=()=>{s.scene_name=scn.value.trim()||"未分场";s.scene_id=groupId("SC",s.scene_name,"01");const i=selIndex(node,st.doc);if(groupBoundaryAt(st.doc.shots,i)){s.continuity="独立生成";s.inherit_previous_audio=false;}persist();st.ui.scene="全部";st.ui.page=1;renderAll();};groupGrid.append(lab("集数分组",epi),lab("场景分组",scn));right.append(groupGrid);const smode=fs(["生成视频","已有视频"],s.source_mode,v=>{if(v!==s.source_mode){s.source_mode=v;s.preview_variant="best";s.refined_video={};s.refine_status="未二采";if(v==="生成视频"){s.existing_video_asset_id="";s.existing_video_name="";s.existing_video_path="";s.existing_video_filename="";s.result_status=(s.result_video?.filename||selectedCandidate(s)?.result_video?.filename)?"已生成":"未生成";}else{s.result_status="等待选择视频";}}persist();renderAll();});const roleSel=fs(["正式视频段","隐藏空间预热（不进成片）"],isHiddenAnchor(s)?"隐藏空间预热（不进成片）":"正式视频段",v=>{const hidden=v.startsWith("隐藏");s.segment_role=hidden?"hidden_anchor":"content";s.include_in_final=!hidden;if(hidden){s.source_mode="生成视频";s.duration=1.0;s.continuity="独立生成";s.inherit_previous_audio=false;s.generation_mode="single";s.spatial_lock_id=s.spatial_lock_id||`LOCK_${String(s.scene_id||"SC").replace(/[^0-9A-Za-z_\-]/g,"_")}_${Date.now().toString().slice(-6)}`;s.refined_video={};s.refine_status="未二采";}persist();renderAll();});right.append(lab("段类型",roleSel),lab("这个卡片放什么",smode));if(isHiddenAnchor(s))right.append(css($("div","生产专用空间预热：约1秒/22帧，只让 H3 看清 2–5 人站位、左右、前后、朝向和轴线；它会参与下一正式段 AddGuide 续写，但合成最终视频时自动删除。"),{fontSize:"9px",lineHeight:"1.55",color:"#c9bcff",background:"#1d1730",border:`1px solid ${C.purple}`,borderRadius:"6px",padding:"8px",marginTop:"7px"}));
    const pv=css($("div"),{marginTop:"7px"});renderVideoPreview(pv,s);right.append(pv);
    if(s.source_mode==="已有视频"){
      const hasExisting=!!(s.existing_video_asset_id||s.existing_video_path||s.existing_video_filename);
      const choose=btn(hasExisting?"更换已有视频":"选择已有视频","blue");css(choose,{width:"100%",marginTop:"7px"});choose.onclick=openVideoPicker;right.append(choose);
      if(s.existing_video_name)right.append(css($("div",`当前：${s.existing_video_name}`),{fontSize:"9px",color:C.green,padding:"6px 2px"}));
      right.append(css($("div","已有视频可以直接作为当前视频段，也可以直接进行二采高清；下一段选择“续写上一段”时，仍会从这个视频尾部提取画面与可选音频引导。"),{fontSize:"9px",lineHeight:"1.5",color:C.muted,marginTop:"6px"}));
      if(hasExisting){const ready=css($("div"),{marginTop:"8px",padding:"8px",border:"1px solid #235735",background:"#0c1c12",borderRadius:"6px"});ready.append(css($("div","✓ 已有视频已就绪"),{fontSize:"10px",fontWeight:"900",color:C.green,marginBottom:"4px"}),css($("div","如果这个视频画面和动作已经满意，可以直接点“二采高清”。不会重新执行一采，也不会改变原始视频文件。"),{fontSize:"9px",lineHeight:"1.5",color:C.muted}));right.append(ready);const hd=btn(refinedVideoUrl(s)?"重新二采高清":"二采高清","gold");css(hd,{width:"100%",marginTop:"7px",padding:"10px",fontWeight:"900"});hd.onclick=()=>queue("二采当前视频段");right.append(hd);}
    }else{
      const dur=inp("number");dur.step="0.1";dur.min="0.2";dur.max="15.1";dur.value=Number(s.duration||5);dur.oninput=()=>{s.duration=Math.max(.2,Math.min(15.1,Number(dur.value||5)));persist();renderTimeline();};right.append(lab(isHiddenAnchor(s)?"预热秒数（推荐 1.0）":"成片目标秒数",dur));
      const genMode=fs(isHiddenAnchor(s)?["单张生成"]:["单张生成","抽卡生成"],s.generation_mode==="draw"?"抽卡生成":"单张生成",v=>{s.generation_mode=v==="抽卡生成"?"draw":"single";persist();renderRules(s);renderTimeline();});right.append(lab("生成模式",genMode));
      if(s.generation_mode==="draw"){
        const dc=fs(["2","4","6","8"],String(s.draw_count||4),v=>{s.draw_count=Number(v);persist();});const dsm=fs(["自动随机","主Seed递增"],s.draw_seed_mode==="increment"?"主Seed递增":"自动随机",v=>{s.draw_seed_mode=v==="主Seed递增"?"increment":"random";persist();});right.append(lab("抽卡数量",dc),lab("抽卡Seed策略",dsm));
        right.append(css($("div","抽卡时 Prompt、Picture、模型、LoRA、时长和采样参数完全相同，只改变 Seed。"),{fontSize:"9px",lineHeight:"1.45",color:C.muted,padding:"6px",border:`1px dashed ${C.border}`,borderRadius:"5px",marginTop:"6px"}));
      }
      const mode=fs(isHiddenAnchor(s)?["独立生成"]:["独立生成","续写上一段"],isHiddenAnchor(s)?"独立生成":s.continuity,v=>{s.continuity=v;persist();renderRules(s);renderTimeline();});right.append(lab("生成关系",mode));
      const box=css($("div"),{marginTop:"7px",padding:"8px",border:`1px solid ${s.continuity==="续写上一段"?"#536b2f":C.border}`,background:s.continuity==="续写上一段"?"#121c0d":"#0c1118",borderRadius:"6px"});box.append(css($("div",s.continuity==="续写上一段"?"续写规则":"独立生成"),{fontWeight:"900",fontSize:"10px",color:s.continuity==="续写上一段"?"#b9e17c":C.blue,marginBottom:"5px"}),css($("div",s.continuity==="续写上一段"?"自动使用上一张卡片的正式版视频 → 取尾部22帧 → AddGuide frame_idx=0 → 保持上一段姿势、位置、动作方向和摄影机连续性。":"本段从独立状态开始，不使用上一张卡片的视频。"),{fontSize:"9px",lineHeight:"1.5",color:C.muted}));right.append(box);
      if(s.continuity==="续写上一段"){const gf=inp("number");gf.value=Number(s.guide_frames||22);gf.oninput=()=>{s.guide_frames=Math.max(5,Number(gf.value||22));persist();renderRules(s);};right.append(lab("尾部画面引导帧",gf));const audioRow=css($("label"),{display:"flex",alignItems:"center",gap:"7px",marginTop:"8px",padding:"8px",border:"1px solid #3c5a35",borderRadius:"6px",background:"#0d1a11",fontSize:"10px",cursor:"pointer"});const ac=$("input");ac.type="checkbox";ac.checked=!!s.inherit_previous_audio;ac.onchange=()=>{s.inherit_previous_audio=ac.checked;persist();renderPrompt(s);renderRules(s);};const at=css($("div"),{display:"flex",flexDirection:"column",gap:"2px"});at.append(css($("b","延续上一段音频 / 人物声音"),{color:"#b9e17c",fontSize:"10px"}),css($("span",`开启后自动取与最后 ${Number(s.guide_frames||22)} 帧对应的尾部音频（约 ${(Number(s.guide_frames||22)/24).toFixed(2)} 秒）送入 AddGuide.audio。`),{color:C.muted,fontSize:"9px",lineHeight:"1.45"}));audioRow.append(ac,at);right.append(audioRow);}
      {const i=selIndex(node,st.doc),boundary=groupBoundaryAt(st.doc.shots,i),prevSeg=i>0?st.doc.shots[i-1]:null,needsPrev=s.continuity==="续写上一段"&&!boundary&&!segmentVideoUrl(prevSeg);if(s.continuity==="续写上一段"&&boundary){const n=css($("div","✓ 当前段是新集/新场景首段，生成时自动按独立生成处理，不会错误继承上一场。"),{marginTop:"7px",padding:"7px",border:"1px solid #235735",background:"#0c1c12",borderRadius:"5px",fontSize:"9px",lineHeight:"1.5",color:C.green});right.append(n);}else if(needsPrev){const w=css($("div"),{marginTop:"7px",padding:"8px",border:`1px solid ${C.gold}`,background:"#2b2310",borderRadius:"6px"});w.append(css($("b","上一段还没有可用视频"),{fontSize:"10px",color:C.gold}),css($("div","现在直接点“生成这个视频”也不会再报错：系统会自动从最近可用视频/独立镜头开始，按顺序补齐缺失的续写链。"),{fontSize:"9px",lineHeight:"1.5",color:C.text,marginTop:"4px"}));const actions=css($("div"),{display:"flex",gap:"5px",marginTop:"6px"});const toCur=btn("生成到当前","blue"),makeInd=btn("改为独立生成");toCur.onclick=()=>queue("生成到当前视频段");makeInd.onclick=()=>{s.continuity="独立生成";s.inherit_previous_audio=false;persist();renderAll();};actions.append(toCur,makeInd);w.append(actions);right.append(w);}}
      const sm=fs(["随机","固定"],s.seed_mode,v=>{s.seed_mode=v;persist();});const sd=inp("number");sd.value=Number(s.seed||0);sd.oninput=()=>{s.seed=Number(sd.value||0);persist();};right.append(lab("主Seed方式",sm),lab("主Seed",sd));
      const hasOfficial=!!selectedCandidate(s)?.result_video?.filename;const hasSingle=!!s.result_video?.filename;
      const g=btn(isHiddenAnchor(s)?(hasSingle?"重新生成空间预热":"生成空间预热（约1秒）"):(s.generation_mode==="draw"?"开始抽卡（一采）":(hasSingle?"重新生成一采":"生成这个视频（一采）")),"primary");css(g,{width:"100%",marginTop:"8px",padding:"9px"});g.onclick=()=>{if(s.generation_mode==="draw"){makeDrawRound(s);persist();renderAll();queue("抽卡当前视频段");}else queue("当前视频段");};right.append(g);
      if(s.generation_mode==="draw")renderDrawCandidates(s);
      const canRefine=!isHiddenAnchor(s)&&(s.generation_mode==="draw"?hasOfficial:hasSingle);
      if(canRefine){const done=css($("div"),{marginTop:"8px",padding:"8px",border:"1px solid #235735",background:"#0c1c12",borderRadius:"6px"});done.append(css($("div",s.generation_mode==="draw"?"✓ 已选择正式版":"✓ 一采生成完成"),{fontSize:"10px",fontWeight:"900",color:C.green,marginBottom:"4px"}),css($("div",s.generation_mode==="draw"?"二采、下一段续写和最终拼接都会使用当前正式版。":"先播放上方一采视频检查效果。满意以后，再手动点击二采高清。"),{fontSize:"9px",lineHeight:"1.5",color:C.muted}));right.append(done);const hd=btn(refinedVideoUrl(s)?"重新二采高清":"二采高清","gold");css(hd,{width:"100%",marginTop:"7px",padding:"10px",fontWeight:"900"});hd.onclick=()=>queue("二采当前视频段");right.append(hd);}else if(s.generation_mode==="draw"&&allCandidates(s).some(c=>c.result_video?.filename)){right.append(css($("div","候选已经生成，请先从上面的候选里选择一个“正式版”，再进行二采、续写或最终拼接。"),{fontSize:"9px",lineHeight:"1.45",color:C.gold,marginTop:"7px",padding:"7px",border:`1px solid ${C.gold}`,borderRadius:"5px"}));}
    }
  }

  function renderAll(){const s=seg();renderManager();renderTimeline();renderTimelineEditor();renderImages(s);renderPrompt(s);renderRules(s);if(s.generation_summary||s.refine_summary){const details=css($("div",[s.generation_summary,s.refine_summary].filter(Boolean).join("\n")),{fontSize:"10px",whiteSpace:"pre-wrap",lineHeight:"1.5",color:C.muted,marginTop:"8px",padding:"8px",border:`1px solid ${C.border}`,borderRadius:"5px"});right.append(details);}updateInfo();updateExternalState();renderHealth();}
  addAnchor.onclick=()=>{const i=selIndex(node,st.doc),base=seg();if(!base)return;if(i>0&&isHiddenAnchor(st.doc.shots[i-1])&&sameStoryGroup(st.doc.shots[i-1],base)){setSeg(i-1);toast("当前正式段前已经有同场景空间预热。","warn",3500);return;}if(isHiddenAnchor(base)){toast("当前卡片本身就是空间预热。请选择一个正式视频段再添加。","warn",4000);return;}const a=makeHiddenAnchorFrom(base,i);st.doc.shots.splice(i,0,a);const formal=st.doc.shots[i+1];if(formal){formal.continuity="续写上一段";formal.inherit_previous_audio=false;formal.spatial_lock_source_id=a.spatial_lock_id;}persist();setSeg(i);toast("已在当前正式段前插入隐藏空间预热。生成后它会给下一段提供22帧定位，并自动从最终成片排除。","ok",6000);};
  add.onclick=()=>{const base=seg(),n=defaultSegment(st.doc.shots.length);if(base){n.episode_id=base.episode_id;n.episode_name=base.episode_name;n.scene_id=base.scene_id;n.scene_name=base.scene_name;}st.doc.shots.push(n);st.ui.episode="全部";st.ui.scene="全部";st.ui.status="全部";st.ui.search="";pageSearch.value="";st.ui.page=Math.ceil(st.doc.shots.length/Number(st.ui.pageSize||12));persist();setSeg(st.doc.shots.length-1);};dup.onclick=()=>{const i=selIndex(node,st.doc),c=JSON.parse(JSON.stringify(st.doc.shots[i]));c.id=`segment-${Date.now()}`;c.name=`${c.name} 复制`;c.result_video={};c.refined_video={};c.draw_rounds=[];c.selected_candidate_id="";c.result_status="未生成";c.refine_status="未二采";st.doc.shots.splice(i+1,0,c);persist();setSeg(i+1);};del.onclick=()=>{if(st.doc.shots.length<=1)return;const i=selIndex(node,st.doc);st.doc.shots.splice(i,1);persist();setSeg(Math.min(i,st.doc.shots.length-1));};prev.onclick=()=>{const arr=filteredEntries().map(x=>x.i),cur=selIndex(node,st.doc),p=arr.indexOf(cur);setSeg(p>0?arr[p-1]:Math.max(0,cur-1));};next.onclick=()=>{const arr=filteredEntries().map(x=>x.i),cur=selIndex(node,st.doc),p=arr.indexOf(cur);setSeg(p>=0&&p<arr.length-1?arr[p+1]:Math.min(st.doc.shots.length-1,cur+1));};
  async function queue(scope){
    clearRuntimeError();
    if(!isLinked("一采模型配置")&&scope!=="合成最终视频"){toast("还没有连接【一采模型配置】节点。","error",5000);return;}
    if(scope==="时间轴局部重绘"){const p=ensurePendingEdit(),a=Number(p.start||0),b=Number(p.end||0),ready=readyTimelineEnd();if(!(b>a)){toast("请先在上方时间轴拖选要修改的范围。","error",5000);return;}if(b>ready+1e-6){toast(`当前只能编辑到 ${ready.toFixed(2)}s，请先生成后面的片段。`,"error",5500);return;}p.id=`edit-${Date.now()}`;p.mode=editMode.value||p.mode||"动作重绘";p.context=Number(editContext.value||p.context||.85);p.prompt=editPrompt.value||p.prompt||"";persist();}
    if(scope==="二采当前视频段"&&!isLinked("二采高清设置")){toast("还没有连接【二采高清设置】节点。先接好二采设置，再开始二采。","error",5000);return;}
    const currentIndex=selIndex(node,st.doc),current=seg();if(scope==="二采当前视频段"&&isHiddenAnchor(current)){toast("隐藏空间预热是生产定位段，不需要二采；请二采正式视频段。","warn",5000);return;}
    if(scope==="当前视频段"||scope==="抽卡当前视频段"||scope==="二采当前视频段"){const v=segmentIssues(current,currentIndex,st.doc.shots);if(v.errors.length){toast(v.errors.join("\n"),"error",6500);renderHealth();return;}if(scope==="二采当前视频段"&&!firstPassVideoUrl(current)){showRuntimeError({index:currentIndex,scope,message:current.generation_mode==="draw"?"当前还没有正式版候选可用于二采。请先选择正式版。":"当前视频段还没有一采完成的视频。请先生成当前视频，满意后再点“二采高清”。",recovery:"generate_first_pass"});return;}if(scope==="抽卡当前视频段"&&!(current.draw_rounds||[]).length){makeDrawRound(current);persist();}if(scope==="当前视频段"&&current.continuity==="续写上一段"&&!groupBoundaryAt(st.doc.shots,currentIndex)&&!segmentVideoUrl(st.doc.shots[currentIndex-1]))toast("上一段未完成：本次会自动补齐缺失的续写链，再生成当前段。","warn",6000);}
    if(scope==="生成到当前视频段"){const bad=[];for(let i=0;i<=currentIndex;i++){const x=st.doc.shots[i];if(x.source_mode!=="生成视频")continue;const v=segmentIssues(x,i,st.doc.shots);if(v.errors.length)bad.push(`视频${i+1}：${v.errors.join("；")}`);}if(bad.length){toast(`生成到当前前请先处理：\n${bad.slice(0,5).join("\n")}`,"error",8000);return;}}
    if(scope==="全部时间线"){const drawSegments=st.doc.shots.map((x,i)=>({x,i})).filter(({x})=>x.source_mode==="生成视频"&&x.generation_mode==="draw");if(drawSegments.length){toast(`生成全部暂不自动抽卡：${drawSegments.map(x=>`视频${x.i+1}`).join("、")} 开启了抽卡模式。请逐段抽卡并选择正式版，这样下一段续写才知道应该接哪一个结果。`,"warn",8000);return;}const bad=[];st.doc.shots.forEach((s,i)=>{if(s.source_mode!=="生成视频")return;const v=segmentIssues(s,i,st.doc.shots);if(v.errors.length)bad.push(`视频${i+1}：${v.errors.join("；")}`);});if(bad.length){toast(`生成全部前请先处理：
${bad.slice(0,5).join("\n")}`,"error",8000);return;}}
    if(scope==="合成最终视频"){const missing=st.doc.shots.map((s,i)=>({s,i})).filter(({s})=>segmentInFinal(s)&&!segmentVideoUrl(s));if(missing.length){toast(`还有 ${missing.length} 个视频段没有正式版/可用视频：${missing.map(x=>`视频${x.i+1}`).join("、")}。抽卡模式请先选正式版，再合成最终视频。`,"error",6500);return;}}
    persist();if(!await inspectModels(scope))return;
    if(scope==="生成到当前视频段"||scope==="全部时间线")st.batch={active:true,text:scope==="生成到当前视频段"?`批量串行生成准备中：1/${currentIndex+1}`:`批量串行生成准备中：1/${st.doc.shots.length}`,mode:scope,current:0,total:scope==="生成到当前视频段"?currentIndex+1:st.doc.shots.length,generated:0,skipped:0};
    setW(node,"generation_scope",scope);if(scope==="当前视频段"){seg().result_status="排队中";}else if(scope==="抽卡当前视频段"){seg().generation_mode="draw";seg().result_status=`抽卡排队中（第 ${(seg().draw_rounds||[]).length} 轮）`;}else if(scope==="二采当前视频段"){seg().refine_status="二采排队中";}else if(scope==="时间轴局部重绘"){toast(`正在重绘 ${Number(st.doc.pending_edit?.start||0).toFixed(2)}–${Number(st.doc.pending_edit?.end||0).toFixed(2)}s；原片不会被覆盖。`,"info",5000);}else if(scope==="生成到当前视频段"){for(let i=0;i<=currentIndex;i++)if(st.doc.shots[i].source_mode==="生成视频"&&!segmentVideoUrl(st.doc.shots[i]))st.doc.shots[i].result_status="串行排队中";}else if(scope==="全部时间线"){for(const s of st.doc.shots)if(s.source_mode==="生成视频")s.result_status="串行排队中";}persist();renderAll();try{await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));if(typeof app.queuePrompt==="function")await app.queuePrompt(0,1);else toast(`已切换为“${scope}”，请点击 ComfyUI 运行按钮。`,`warn`,5000);}catch(e){console.error(e);toast(`已切换为“${scope}”，请点击 ComfyUI 运行按钮。`,`warn`,5000);}}
  genCur.onclick=()=>{const s=seg();if(s.source_mode==="生成视频"&&s.generation_mode==="draw"){makeDrawRound(s);persist();renderAll();queue("抽卡当前视频段");}else queue("当前视频段");};genToCur.onclick=()=>queue("生成到当前视频段");genAll.onclick=()=>queue("全部时间线");finalMix.onclick=()=>queue("合成最终视频");

  if(node._avsSegmentHandler&&api.removeEventListener)try{api.removeEventListener("avs_segment_result",node._avsSegmentHandler);}catch{}
  node._avsSegmentHandler=(ev)=>{const d=ev?.detail||ev||{};if(String(d.node_id)!==String(node.id))return;if(Number(d.index)===-2){if(d.timeline_edit){st.doc.timeline_edits=Array.isArray(st.doc.timeline_edits)?st.doc.timeline_edits:[];const rec=d.timeline_edit,at=st.doc.timeline_edits.findIndex(x=>String(x.id)===String(rec.id));if(at>=0)st.doc.timeline_edits[at]=rec;else st.doc.timeline_edits.push(rec);const keep={...(st.doc.pending_edit||{})};delete keep.id;st.doc.pending_edit=keep;saveDoc(node,st.doc);syncEditFields();renderAll();toast(d.status||"时间轴局部重绘完成","info",6000);}return;}if(Number(d.index)===-1){st.final_video=d.final_video||{};if(d.batch_total){st.batch={active:false,text:d.batch_summary||"批量串行完成",mode:d.batch_mode||"",current:Number(d.batch_total||0),total:Number(d.batch_total||0),generated:Number(d.batch_generated||0),skipped:Number(d.batch_skipped||0)};saveDoc(node,st.doc);renderAll();}return;}const i=Number(d.index);if(!Number.isInteger(i)||!st.doc.shots[i])return;const s=st.doc.shots[i];if(d.batch_total){st.batch={active:true,text:`${d.batch_mode||"批量生成"}：正在串行处理 ${Number(d.batch_current||0)}/${Number(d.batch_total||0)}（当前视频段 ${i+1}）`,mode:d.batch_mode||"",current:Number(d.batch_current||0),total:Number(d.batch_total||0),generated:Number(d.batch_generated||0),skipped:Number(d.batch_skipped||0)};}
    if(d.result_video||d.refined_video||/完成|已有视频/.test(String(d.status||"")))delete s.last_error;
    for(const key of ["generation_summary","generation_dims","refine_summary","refine_dims"])if(d[key]!==undefined)s[key]=d[key];
    if(d.seed!==undefined&&!d.candidate_id){s.seed=Number(d.seed);s.seed_mode=d.seed_mode||"固定";}
    // v0.15.6: 后端若因 ComfyUI 提交时序自动补建了候选轮，前端也自动补同名候选，
    // 避免 candidate_id 找不到后错误落入“普通单张结果”分支。
    let cand=d.candidate_id?candidateById(s,d.candidate_id):null;
    if(d.candidate_id&&!cand){
      s.generation_mode="draw";
      let round=(s.draw_rounds||[]).at(-1);
      if(!round){round={round_index:1,candidates:[]};s.draw_rounds=[round];}
      round.candidates=Array.isArray(round.candidates)?round.candidates:[];
      cand={candidate_id:String(d.candidate_id),round_index:Number(round.round_index||1),candidate_index:round.candidates.length+1,seed:Number(d.seed||0),result_video:{},refined_video:{},status:"等待生成",refine_status:"未二采",is_selected:false};
      round.candidates.push(cand);
    }
    if(cand){if(d.seed!==undefined)cand.seed=Number(d.seed||0);if(d.status)cand.status=String(d.status);if(d.result_video){cand.result_video=d.result_video;cand.refined_video={};cand.refine_status="未二采";}if(d.refined_video){cand.refined_video=d.refined_video;cand.refine_status=d.refine_status||"二采完成";}s.result_status=d.status||s.result_status;}else{if(d.status){if(String(d.status).includes("二采"))s.refine_status=d.status;else s.result_status=d.status;}if(d.result_video){s.result_video=d.result_video;s.source_mode="生成视频";s.refined_video={};s.refine_status="未二采";s.preview_variant="source";}if(d.refined_video){const selected=selectedCandidate(s);if(selected){selected.refined_video=d.refined_video;selected.refine_status=d.refine_status||"二采完成";}else{s.refined_video=d.refined_video;}s.refine_status=d.refine_status||"二采完成";s.preview_variant="hd";}}if(d.existing_video){s.existing_video_asset_id=d.existing_video.asset_id||s.existing_video_asset_id;s.existing_video_name=d.existing_video.name||s.existing_video_name;s.existing_video_path=d.existing_video.path||s.existing_video_path;}saveDoc(node,st.doc);renderAll();};api.addEventListener("avs_segment_result",node._avsSegmentHandler);

  if(node._avsRuntimeErrorHandler&&api.removeEventListener)try{api.removeEventListener("avs_runtime_error",node._avsRuntimeErrorHandler);}catch{}
  node._avsRuntimeErrorHandler=(ev)=>{const d=ev?.detail||ev||{};if(String(d.node_id)!==String(node.id))return;showRuntimeError(d);};api.addEventListener("avs_runtime_error",node._avsRuntimeErrorHandler);
  if(node._avsExecutionErrorHandler&&api.removeEventListener)try{api.removeEventListener("execution_error",node._avsExecutionErrorHandler);}catch{}
  node._avsExecutionErrorHandler=(ev)=>{const d=ev?.detail||ev||{};const nid=d.node_id??d.nodeId??d?.node?.id;if(nid!==undefined&&String(nid)!==String(node.id))return;const msg=d.exception_message||d.message||d.error;if(!msg)return;showRuntimeError({node_id:node.id,index:selIndex(node,st.doc),scope:findW(node,"generation_scope")?.value||"",exception_type:d.exception_type||"",message:msg});};api.addEventListener("execution_error",node._avsExecutionErrorHandler);

  renderAll();
  const dw=node.addDOMWidget("avs_director_workbench_ui","div",root,{serialize:false,hideOnZoom:false,getMinHeight:()=>1405,getMaxHeight:()=>1950});dw.computeSize=(width)=>[Math.max(1180,width||1400),1405];
  const enforce=()=>{removeUnusedResourceInput(node);collapse(node);if(root.parentElement)Object.assign(root.parentElement.style,{margin:"0",padding:"0"});node.graph?.setDirtyCanvas?.(true,true);};
  const oldR=node.onResize;node.onResize=function(size){oldR?.call(this,size);root.style.height=Math.max(1315,(size?.[1]||1465)-45)+"px";setTimeout(enforce,0);};
  const oldC=node.onConfigure;node.onConfigure=function(info){const r=oldC?.call(this,info);setTimeout(()=>{st.doc=readDoc(node);st.ui.episode="全部";st.ui.scene="全部";st.ui.status="全部";st.ui.page=1;st.ui.search="";pageSearch.value="";syncEditFields();renderAll();enforce();},80);return r;};
  const oldExecuted=node.onExecuted;node.onExecuted=function(data){const r=oldExecuted?.call(this,data);for(const plan of data?.avs_model_setup||[])node._avsModelSetup(plan);return r;};
  const oldRemoved=node.onRemoved;node.onRemoved=function(){characterUI.dispose();if(node._avsSegmentHandler&&api.removeEventListener)try{api.removeEventListener("avs_segment_result",node._avsSegmentHandler);}catch{};if(node._avsRuntimeErrorHandler&&api.removeEventListener)try{api.removeEventListener("avs_runtime_error",node._avsRuntimeErrorHandler);}catch{};if(node._avsExecutionErrorHandler&&api.removeEventListener)try{api.removeEventListener("execution_error",node._avsExecutionErrorHandler);}catch{};return oldRemoved?.apply(this,arguments);};
  for(const ms of [0,60,250,700])setTimeout(enforce,ms);
  setTimeout(()=>inspectModels(),900);
  void characterUI.refresh().catch(()=>{});
}

app.registerExtension({name:EXT,setup(){installModelPreflight(app,api);},async beforeRegisterNodeDef(nodeType,nodeData){if(nodeData?.name!=="AVSDirectorStudio")return;const old=nodeType.prototype.onNodeCreated;nodeType.prototype.onNodeCreated=function(){const r=old?.apply(this,arguments);setTimeout(()=>build(this),0);return r;};}});
