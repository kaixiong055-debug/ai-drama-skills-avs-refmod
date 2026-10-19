import {chooseLibraryDirectory, useNativePicker} from "/avs/library/folders.js";
(()=>{
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const CATS=["角色","场景","道具","动作","声音"];
  const ICON={"角色":"♙","场景":"▣","道具":"◇","动作":"↗","声音":"◉"};
  const state={lang:"zh-CN",config:{},stats:{image:0,video:0,audio:0,total:0,categories:[]},groupStats:{groups:0,by_category:{},unassigned:0},groups:[],view:"home",category:"",currentGroup:null,assets:[],totalFiltered:0,page:1,limit:48,q:"",type:"all",selected:new Set(),currentAsset:null,editingGroup:null,currentFolder:"",parentFolder:""};

  const T={
    "zh-CN":{
      assetCenter:"素材中心",home:"资源主页",unassigned:"待整理",assetGroups:"资源组",characters:"角色",scenes:"场景",props:"道具",motions:"动作",voices:"声音",library:"资源库",allFiles:"全部文件",currentLibrary:"当前资源库",changeFolder:"更换目录",
      titleHome:"素材中心",subHome:"先把文件整理成“资源组”，以后导演台里直接 @角色、@场景，不需要记每一张图片。",newGroup:"新建资源组",rescan:"重新扫描",libraryPath:"资源库",ready:"就绪",
      heroKicker:"AI VIDEO STUDIO · 素材管理",heroTitle:"不要管理几十张文件，管理“角色、场景、道具”就够了。",heroDesc:"一个资源组可以包含多张图片、视频和音频。例如把苏甜柠的全身、脸部、三视图、声音全部放进“苏甜柠”资源组，以后只需要 @苏甜柠。",organizeNow:"整理待处理素材",createGroup:"新建资源组",
      workflow:"最简单的使用方式",step1:"扫描资源库",step1d:"选择你的永久资源目录，系统只建立索引。",step2:"整理成资源组",step2d:"把同一个角色、场景或道具的文件放在一起。",step3:"以后直接 @引用",step3d:"导演台只需要选择 @苏甜柠、@金色舞台。",
      totalFiles:"全部文件",groups:"资源组",needOrganize:"待整理",images:"图片",recentGroups:"最近资源组",recentGroupsSub:"你以后真正会使用的是这些资源组，而不是单个文件。",viewAll:"查看全部",noGroups:"还没有资源组",noGroupsText:"先新建一个“角色 / 场景 / 道具”等资源组，再把相关素材一次性放进去。",
      titleUnassigned:"待整理素材",subUnassigned:"这里都是还没有加入任何资源组的文件。选中一批后，一次加入角色、场景或道具资源组。",guideTitle:"推荐先整理这里",guideText:"不用给每张图片单独设置分类。选中同一个角色的所有图片 → 加入“角色资源组”，以后它们就是一个整体。",
      titleFiles:"全部文件",subFiles:"查看资源库中的原始文件。通常不需要逐个编辑，优先使用资源组管理。",titleGroups:(c)=>`${c}资源组`,subGroups:(c)=>`这里管理所有“${c}”资产。一个卡片代表一个可被 @引用的完整资源。`,
      search:"搜索素材或文件…",allTypes:"全部类型",image:"图片",video:"视频",audio:"音频",selected:n=>`已选择 ${n} 个`,addToGroup:"加入资源组",removeFromGroup:"从资源组移除",clearSelection:"取消选择",selectAllPage:"选择本页",result:n=>`共 ${n} 个`,prev:"上一页",next:"下一页",
      newGroupTitle:"新建资源组",editGroupTitle:"编辑资源组",assetGroup:"资源组",groupName:"名称",groupAlias:"@别名",groupCategory:"类型",description:"说明",saveGroup:"保存资源组",cancel:"取消",deleteGroup:"删除资源组",editGroup:"编辑资源组",openGroup:"打开资源组",assetsCount:n=>`${n} 个素材`,noAlias:"未设置 @别名",noDescription:"还没有说明",
      organizeAssets:"整理素材",chooseGroup:"选择资源组",createNewGroup:"新建一个资源组",confirmAdd:"确认加入",assignSummary:n=>`准备整理 ${n} 个素材。请选择它们属于哪个资源组。`,noGroupOption:"请先选择资源组",added:n=>`已加入 ${n} 个素材`,removed:n=>`已移除 ${n} 个素材`,groupSaved:"资源组已保存",groupDeleted:"资源组已删除",
      assetDetails:"素材详情",displayName:"显示名称",alias:"单文件 @别名",category:"分类",tags:"标签",fileName:"文件名",size:"大小",resolution:"分辨率",duration:"时长",path:"路径",save:"保存素材信息",saved:"素材信息已保存",
      chooseFolderTitle:"选择永久资源库目录",up:"上一级",useFolder:"使用此目录",scanRunning:"正在扫描…",scanDone:(n,s)=>`扫描完成：${n} 个素材，用时 ${s}s`,scanFail:"扫描失败",folderSaved:"资源库目录已保存",noFolder:"请先选择资源库目录",noSubfolder:"这个目录没有子目录。",
      emptyAssets:"没有找到素材",emptyAssetsSub:"调整搜索条件，或重新扫描资源库。",emptyGroup:"这个资源组还是空的",emptyGroupSub:"回到“待整理”，选中素材并加入这个资源组。",groupTip:"资源组就是未来 @引用的对象",groupTipSub:"例如 @苏甜柠 会代表这一组中的多张参考图，而不是某一张单独图片。",
      openUnassigned:"去待整理",backGroups:"返回资源组",groupCategoryLabel:"资源类型",createAndAssign:"新建资源组并加入",loadFail:"加载失败",confirmDelete:"确定删除这个资源组吗？素材文件不会被删除。",noSelected:"请先选择素材。",language:"中文"
    },
    "en-US":{
      assetCenter:"Asset Center",home:"Home",unassigned:"To Organize",assetGroups:"Asset Groups",characters:"Characters",scenes:"Scenes",props:"Props",motions:"Motion",voices:"Voice",library:"Library",allFiles:"All Files",currentLibrary:"Current Library",changeFolder:"Change Folder",
      titleHome:"Asset Center",subHome:"Organize files into asset groups. Later the Director can use @Character or @Scene instead of individual files.",newGroup:"New Asset Group",rescan:"Rescan",libraryPath:"Library",ready:"Ready",
      heroKicker:"AI VIDEO STUDIO · ASSET MANAGEMENT",heroTitle:"Manage characters and scenes — not dozens of individual files.",heroDesc:"An asset group can contain many images, videos and audio files. Put a character's full-body, face, turnaround and voice into one group, then reference only @CharacterName.",organizeNow:"Organize Unsorted Assets",createGroup:"New Asset Group",
      workflow:"The simplest workflow",step1:"Scan Library",step1d:"Choose a permanent media folder. Only an index is created.",step2:"Build Asset Groups",step2d:"Put files belonging to the same character, scene or prop together.",step3:"Use @ References",step3d:"The Director only needs @Character and @Scene.",
      totalFiles:"All Files",groups:"Asset Groups",needOrganize:"To Organize",images:"Images",recentGroups:"Recent Asset Groups",recentGroupsSub:"These groups — not individual files — are what you will use later.",viewAll:"View All",noGroups:"No asset groups yet",noGroupsText:"Create a Character / Scene / Prop group, then add related files in one batch.",
      titleUnassigned:"Assets To Organize",subUnassigned:"These files have not been added to any asset group yet. Select a batch and add them to a Character, Scene or Prop group.",guideTitle:"Start here",guideText:"Do not classify every image one by one. Select all files for the same character, then add them to one Character group.",
      titleFiles:"All Files",subFiles:"Browse raw files in the library. Usually you should manage groups instead of editing files individually.",titleGroups:(c)=>`${trCat(c)} Groups`,subGroups:(c)=>`Manage all ${trCat(c)} assets. One card represents one complete @ reference.`,
      search:"Search assets or files…",allTypes:"All Types",image:"Image",video:"Video",audio:"Audio",selected:n=>`${n} selected`,addToGroup:"Add to Group",removeFromGroup:"Remove from Group",clearSelection:"Clear Selection",selectAllPage:"Select Page",result:n=>`${n} results`,prev:"Previous",next:"Next",
      newGroupTitle:"New Asset Group",editGroupTitle:"Edit Asset Group",assetGroup:"Asset Group",groupName:"Name",groupAlias:"@Alias",groupCategory:"Type",description:"Description",saveGroup:"Save Group",cancel:"Cancel",deleteGroup:"Delete Group",editGroup:"Edit Group",openGroup:"Open Group",assetsCount:n=>`${n} assets`,noAlias:"No @alias",noDescription:"No description yet",
      organizeAssets:"Organize Assets",chooseGroup:"Choose Asset Group",createNewGroup:"Create New Group",confirmAdd:"Add",assignSummary:n=>`Organizing ${n} assets. Choose the asset group they belong to.`,noGroupOption:"Choose a group first",added:n=>`Added ${n} assets`,removed:n=>`Removed ${n} assets`,groupSaved:"Asset group saved",groupDeleted:"Asset group deleted",
      assetDetails:"Asset Details",displayName:"Display Name",alias:"Single-file @Alias",category:"Category",tags:"Tags",fileName:"File Name",size:"Size",resolution:"Resolution",duration:"Duration",path:"Path",save:"Save Asset",saved:"Asset saved",
      chooseFolderTitle:"Choose Permanent Library Folder",up:"Up",useFolder:"Use This Folder",scanRunning:"Scanning…",scanDone:(n,s)=>`Scan complete: ${n} assets in ${s}s`,scanFail:"Scan failed",folderSaved:"Library folder saved",noFolder:"Choose a library folder first",noSubfolder:"No subfolders here.",
      emptyAssets:"No assets found",emptyAssetsSub:"Change filters or rescan the library.",emptyGroup:"This group is empty",emptyGroupSub:"Go to To Organize, select files and add them to this group.",groupTip:"An asset group is what you will @ reference later",groupTipSub:"For example @Character can represent several reference images rather than one file.",
      openUnassigned:"Go to To Organize",backGroups:"Back to Groups",groupCategoryLabel:"Asset Type",createAndAssign:"Create Group & Add",loadFail:"Load failed",confirmDelete:"Delete this asset group? Media files will not be deleted.",noSelected:"Select some assets first.",language:"English"
    }
  };

  function t(){return T[state.lang]||T["zh-CN"]}
  function trCat(c){if(state.lang!=="en-US")return c;return {"角色":"Character","场景":"Scene","道具":"Prop","动作":"Motion","声音":"Voice","未分类":"Uncategorized"}[c]||c}
  function esc(v){return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]))}
  function bytes(n){n=Number(n)||0;const u=["B","KB","MB","GB","TB"];let i=0;while(n>=1024&&i<u.length-1){n/=1024;i++}return `${n.toFixed(i?1:0)} ${u[i]}`}
  function dur(n){return n?`${Number(n).toFixed(1)}s`:"—"}
  function mediaIcon(type){return type==="video"?"▶":type==="audio"?"♪":"▧"}
  function mediaLabel(type){return type==="video"?t().video:type==="audio"?t().audio:t().image}
  async function request(url,opts={}){const r=await fetch(url,opts);let d={};try{d=await r.json()}catch{}if(!r.ok||d.ok===false)throw new Error(d.error||`${r.status} ${r.statusText}`);return d}
  function toast(msg,error=false){const el=document.createElement("div");el.className=`toast${error?" error":""}`;el.textContent=msg;$("#toastHost").append(el);setTimeout(()=>el.remove(),3500)}
  function debounce(fn,ms=220){let id;return(...a)=>{clearTimeout(id);id=setTimeout(()=>fn(...a),ms)}}

  function applyI18n(){
    $$('[data-i18n]').forEach(el=>{const key=el.dataset.i18n;if(typeof t()[key]==="string")el.textContent=t()[key]});
    $("#languageSelect").value=state.lang;
    document.documentElement.lang=state.lang;
    renderNavCounts();
  }
  function setPage(title,subtitle,breadcrumb=title){$("#pageTitle").textContent=title;$("#pageSubtitle").textContent=subtitle;$("#breadcrumb").textContent=breadcrumb}
  function renderNavCounts(){
    $("#unassignedCount").textContent=state.groupStats.unassigned||0;$("#allCount").textContent=state.stats.total||0;
    for(const c of CATS){const el=document.getElementById(`count${c}`);if(el)el.textContent=state.groupStats.by_category?.[c]||0}
    $("#libraryPath").textContent=state.config.library_path||"—";$("#sidePath").textContent=state.config.library_path||"—";
  }
  function setActiveNav(view,category=""){$$(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===view&&(!b.dataset.category||b.dataset.category===category)))}

  function groupCover(g){const id=g.effective_cover_id||g.cover_asset_id;return id?`<img src="/avs/library/thumb/${encodeURIComponent(id)}" alt="" onerror="this.remove()">`:`<div class="fallback">${ICON[g.category]||"◫"}</div>`}
  function groupCard(g){
    return `<article class="group-card" data-group-id="${esc(g.id)}"><div class="group-cover">${groupCover(g)}<span class="group-type">${esc(trCat(g.category))}</span><span class="group-count">${esc(t().assetsCount(g.member_count||0))}</span></div><div class="group-body"><div class="group-name">${esc(g.name)}</div><div class="group-alias">${g.alias?`@${esc(g.alias)}`:esc(t().noAlias)}</div><div class="group-desc">${esc(g.description||t().noDescription)}</div><div class="group-card-footer"><button class="text-btn open-group">${esc(t().openGroup)}</button><button class="text-btn edit-group">${esc(t().editGroup)}</button></div></div></article>`
  }
  function bindGroupCards(root=$("#mainContent")){
    $$(".group-card",root).forEach(card=>{
      const g=state.groups.find(x=>x.id===card.dataset.groupId);if(!g)return;
      card.onclick=(e)=>{if(e.target.closest(".edit-group")){e.stopPropagation();openGroupModal(g);return}openGroup(g)};
    })
  }

  function renderHome(){
    setPage(t().titleHome,t().subHome,t().home);setActiveNav("home");state.selected.clear();state.currentGroup=null;
    const groups=state.groups.slice(0,8);
    $("#mainContent").innerHTML=`
      <div class="hero"><section class="hero-card"><div class="hero-kicker">${esc(t().heroKicker)}</div><div class="hero-title">${esc(t().heroTitle)}</div><div class="hero-desc">${esc(t().heroDesc)}</div><div class="hero-actions"><button class="btn primary" id="homeOrganizeBtn">${esc(t().organizeNow)}</button><button class="btn ghost" id="homeCreateBtn">＋ ${esc(t().createGroup)}</button></div></section>
      <aside class="workflow-card"><div class="workflow-title">${esc(t().workflow)}</div><div class="workflow-steps"><div class="workflow-step"><div class="step-num">1</div><div class="step-copy"><b>${esc(t().step1)}</b><p>${esc(t().step1d)}</p></div></div><div class="workflow-step"><div class="step-num">2</div><div class="step-copy"><b>${esc(t().step2)}</b><p>${esc(t().step2d)}</p></div></div><div class="workflow-step"><div class="step-num">3</div><div class="step-copy"><b>${esc(t().step3)}</b><p>${esc(t().step3d)}</p></div></div></div></aside></div>
      <div class="stats-row"><div class="stat-card"><div class="stat-label">${esc(t().totalFiles)}</div><div class="stat-value">${state.stats.total||0}</div><div class="stat-note">${state.stats.image||0} ${esc(t().image)} · ${state.stats.video||0} ${esc(t().video)} · ${state.stats.audio||0} ${esc(t().audio)}</div></div><div class="stat-card"><div class="stat-label">${esc(t().groups)}</div><div class="stat-value">${state.groupStats.groups||0}</div><div class="stat-note">${esc(t().groupTip)}</div></div><div class="stat-card"><div class="stat-label">${esc(t().needOrganize)}</div><div class="stat-value">${state.groupStats.unassigned||0}</div><div class="stat-note">${esc(t().guideTitle)}</div></div><div class="stat-card"><div class="stat-label">${esc(t().images)}</div><div class="stat-value">${state.stats.image||0}</div><div class="stat-note">${esc(state.config.library_path?state.config.library_path.split(/[\\/]/).filter(Boolean).pop()||"—":"—")}</div></div></div>
      <section class="section"><div class="section-head"><div><div class="section-title">${esc(t().recentGroups)}</div><div class="section-sub">${esc(t().recentGroupsSub)}</div></div>${state.groups.length?`<button class="btn ghost small" id="viewAllGroupsBtn">${esc(t().viewAll)}</button>`:""}</div>${groups.length?`<div class="group-grid">${groups.map(groupCard).join("")}</div>`:`<div class="empty-panel"><div><div class="empty-icon">◫</div><h3>${esc(t().noGroups)}</h3><p>${esc(t().noGroupsText)}</p><div class="empty-actions"><button class="btn primary" id="emptyCreateBtn">＋ ${esc(t().createGroup)}</button><button class="btn ghost" id="emptyOrganizeBtn">${esc(t().openUnassigned)}</button></div></div></div>`}</section>`;
    $("#homeOrganizeBtn")?.addEventListener("click",()=>showView("unassigned"));$("#homeCreateBtn")?.addEventListener("click",()=>openGroupModal());$("#emptyCreateBtn")?.addEventListener("click",()=>openGroupModal());$("#emptyOrganizeBtn")?.addEventListener("click",()=>showView("unassigned"));$("#viewAllGroupsBtn")?.addEventListener("click",()=>showView("groups","角色"));bindGroupCards();
  }

  function renderGroups(category){
    state.category=category;setPage(t().titleGroups(category),t().subGroups(category),`${t().assetGroups} / ${trCat(category)}`);setActiveNav("groups",category);state.selected.clear();state.currentGroup=null;
    const groups=state.groups.filter(g=>g.category===category);
    $("#mainContent").innerHTML=`<section class="section"><div class="section-head"><div><div class="section-title">${esc(t().titleGroups(category))}</div><div class="section-sub">${esc(t().groupTipSub)}</div></div><div class="section-actions"><button class="btn primary" id="catCreateBtn">＋ ${esc(t().newGroup)}</button></div></div>${groups.length?`<div class="group-grid">${groups.map(groupCard).join("")}</div>`:`<div class="empty-panel"><div><div class="empty-icon">${ICON[category]||"◫"}</div><h3>${esc(t().noGroups)}</h3><p>${esc(t().noGroupsText)}</p><div class="empty-actions"><button class="btn primary" id="catEmptyCreateBtn">＋ ${esc(t().newGroup)}</button><button class="btn ghost" id="catOrganizeBtn">${esc(t().openUnassigned)}</button></div></div></div>`}</section>`;
    $("#catCreateBtn")?.addEventListener("click",()=>openGroupModal(null,category));$("#catEmptyCreateBtn")?.addEventListener("click",()=>openGroupModal(null,category));$("#catOrganizeBtn")?.addEventListener("click",()=>showView("unassigned"));bindGroupCards();
  }

  function assetPreview(a){return a.has_thumbnail?`<img src="/avs/library/thumb/${encodeURIComponent(a.id)}?v=${encodeURIComponent(a.mtime||0)}" alt="">`:`<div class="fallback">${mediaIcon(a.media_type)}</div>`}
  function assetCard(a,selectable=true){const checked=state.selected.has(a.id);return `<article class="asset-card${checked?" selected":""}" data-asset-id="${esc(a.id)}">${selectable?`<input class="asset-select" type="checkbox" ${checked?"checked":""}>`:""}<span class="asset-type">${esc(mediaLabel(a.media_type))}</span><div class="asset-preview">${assetPreview(a)}</div><div class="asset-body"><div class="asset-name" title="${esc(a.display_name)}">${esc(a.display_name)}</div><div class="asset-subline"><span>${esc(trCat(a.category||"未分类"))}</span><span>${bytes(a.size_bytes)}</span></div><div class="asset-alias">${a.alias?`@${esc(a.alias)}`:""}</div><div class="asset-path" title="${esc(a.relative_path)}">${esc(a.relative_path)}</div></div></article>`}
  function bindAssetCards(){
    $$(".asset-card",$("#mainContent")).forEach(card=>{const a=state.assets.find(x=>x.id===card.dataset.assetId);if(!a)return;const check=$(".asset-select",card);if(check)check.onclick=e=>{e.stopPropagation();toggleSelected(a.id,e.target.checked)};card.onclick=e=>{if(e.target.closest(".asset-select"))return;openAssetDrawer(a)}})
  }
  function toggleSelected(id,on){if(on)state.selected.add(id);else state.selected.delete(id);renderSelectionBarOnly();$$(`.asset-card[data-asset-id="${id}"]`).forEach(c=>c.classList.toggle("selected",on))}
  function paginationHtml(){const pages=Math.max(1,Math.ceil(state.totalFiltered/state.limit));return `<div class="pagination"><button class="btn ghost small" id="prevBtn" ${state.page<=1?"disabled":""}>${esc(t().prev)}</button><span class="page-text">${state.page} / ${pages}</span><button class="btn ghost small" id="nextBtn" ${state.page>=pages?"disabled":""}>${esc(t().next)}</button></div>`}
  function toolbarHtml(mode){return `<div class="toolbar-card"><div class="toolbar-row"><div class="search-box"><span>⌕</span><input id="searchInput" value="${esc(state.q)}" placeholder="${esc(t().search)}"></div><select id="typeSelect" class="control"><option value="all">${esc(t().allTypes)}</option><option value="image">${esc(t().image)}</option><option value="video">${esc(t().video)}</option><option value="audio">${esc(t().audio)}</option></select><span class="view-meta">${esc(t().result(state.totalFiltered))}</span></div><div id="selectionBarHost"></div></div>`}
  function selectionBarHtml(mode){if(!state.selected.size)return"";const primary=mode==="group"?t().removeFromGroup:t().addToGroup;return `<div class="selection-bar"><div><strong>${esc(t().selected(state.selected.size))}</strong></div><div class="selection-actions"><button class="btn ghost small" id="selectPageBtn">${esc(t().selectAllPage)}</button><button class="btn ${mode==="group"?"danger":"primary"} small" id="selectionActionBtn">${esc(primary)}</button><button class="btn ghost small" id="clearSelectionBtn">${esc(t().clearSelection)}</button></div></div>`}
  function renderSelectionBarOnly(){const host=$("#selectionBarHost");if(!host)return;const mode=state.view==="group"?"group":"assign";host.innerHTML=selectionBarHtml(mode);bindSelectionBar(mode)}
  function bindSelectionBar(mode){$("#selectPageBtn")?.addEventListener("click",()=>{state.assets.forEach(a=>state.selected.add(a.id));renderAssetViewCurrent()});$("#clearSelectionBtn")?.addEventListener("click",()=>{state.selected.clear();renderAssetViewCurrent()});$("#selectionActionBtn")?.addEventListener("click",()=>{if(mode==="group")removeSelectedFromCurrentGroup();else openAssignModal()})}
  function bindAssetToolbar(){const deb=debounce(v=>{state.q=v;state.page=1;loadCurrentAssets()},220);$("#searchInput")?.addEventListener("input",e=>deb(e.target.value.trim()));const type=$("#typeSelect");if(type){type.value=state.type;type.onchange=e=>{state.type=e.target.value;state.page=1;loadCurrentAssets()}}$("#prevBtn")?.addEventListener("click",()=>{if(state.page>1){state.page--;loadCurrentAssets()}});$("#nextBtn")?.addEventListener("click",()=>{const pages=Math.max(1,Math.ceil(state.totalFiltered/state.limit));if(state.page<pages){state.page++;loadCurrentAssets()}})}
  function renderAssetGrid(emptyTitle=t().emptyAssets,emptySub=t().emptyAssetsSub){return state.assets.length?`<div class="asset-grid">${state.assets.map(a=>assetCard(a,true)).join("")}</div>${paginationHtml()}`:`<div class="empty-panel"><div><div class="empty-icon">▦</div><h3>${esc(emptyTitle)}</h3><p>${esc(emptySub)}</p></div></div>`}

  function renderUnassigned(){
    setPage(t().titleUnassigned,t().subUnassigned,`${t().home} / ${t().unassigned}`);setActiveNav("unassigned");state.currentGroup=null;
    $("#mainContent").innerHTML=`<div class="guide-banner"><div class="guide-icon">!</div><div class="guide-copy"><b>${esc(t().guideTitle)}</b><p>${esc(t().guideText)}</p></div></div>${toolbarHtml("assign")}<div id="assetView">${renderAssetGrid()}</div>`;
    renderSelectionBarOnly();bindAssetToolbar();bindAssetCards();
  }
  function renderFiles(){setPage(t().titleFiles,t().subFiles,`${t().library} / ${t().allFiles}`);setActiveNav("files");state.currentGroup=null;$("#mainContent").innerHTML=`${toolbarHtml("assign")}<div id="assetView">${renderAssetGrid()}</div>`;renderSelectionBarOnly();bindAssetToolbar();bindAssetCards()}
  function renderGroupDetail(){
    const g=state.currentGroup;if(!g)return renderHome();setPage(g.name,t().groupTipSub,`${trCat(g.category)} / ${g.name}`);setActiveNav("groups",g.category);
    $("#mainContent").innerHTML=`<div class="group-header"><div class="group-header-cover">${groupCover(g)}</div><div><div class="group-header-title">${esc(g.name)}</div><div class="group-header-alias">${g.alias?`@${esc(g.alias)}`:esc(t().noAlias)}</div><div class="group-header-desc">${esc(g.description||t().noDescription)}</div></div><div class="group-header-actions"><button class="btn ghost" id="backGroupsBtn">← ${esc(t().backGroups)}</button><button class="btn secondary" id="editCurrentGroupBtn">${esc(t().editGroup)}</button><button class="btn primary" id="addToCurrentGroupBtn">＋ ${esc(t().addToGroup)}</button></div></div><div class="guide-banner"><div class="guide-icon">@</div><div class="guide-copy"><b>${esc(t().groupTip)}</b><p>${esc(t().groupTipSub)}</p></div></div>${toolbarHtml("group")}<div id="assetView">${renderAssetGrid(t().emptyGroup,t().emptyGroupSub)}</div>`;
    $("#backGroupsBtn").onclick=()=>showView("groups",g.category);$("#editCurrentGroupBtn").onclick=()=>openGroupModal(g);$("#addToCurrentGroupBtn").onclick=()=>{state.view="unassigned";state.page=1;state.q="";state.type="all";state.selected.clear();loadCurrentAssets().then(()=>renderUnassigned())};renderSelectionBarOnly();bindAssetToolbar();bindAssetCards();
  }
  function renderAssetViewCurrent(){if(state.view==="unassigned")renderUnassigned();else if(state.view==="files")renderFiles();else if(state.view==="group")renderGroupDetail()}

  async function loadCurrentAssets(){
    const p=new URLSearchParams({q:state.q,type:state.type,limit:String(state.limit),offset:String((state.page-1)*state.limit)});if(state.view==="unassigned")p.set("unassigned","1");else if(state.view==="group"&&state.currentGroup)p.set("group_id",state.currentGroup.id);
    const d=await request(`/avs/library/assets?${p}`);state.assets=d.assets||[];state.totalFiltered=d.total_filtered||0;state.stats=d.stats||state.stats;state.groupStats=d.group_stats||state.groupStats;renderNavCounts();renderAssetViewCurrent();
  }
  async function loadGroups(){const d=await request("/avs/library/groups");state.groups=d.groups||[];state.groupStats=d.group_stats||state.groupStats;renderNavCounts()}
  async function refreshStatus(){const d=await request("/avs/library/status");state.nativePicker=useNativePicker(d);state.config=d.config||{};state.stats=d.stats||state.stats;state.groupStats=d.group_stats||state.groupStats;if(d.config?.language)state.lang=d.config.language;renderNavCounts();applyI18n();const server=$("#chooseServerFolderBtn");if(server){server.textContent=state.lang==="en-US"?"Server Folder":"选择服务器目录";server.style.display=state.nativePicker?"none":"";}}

  async function showView(view,category=""){
    state.view=view;state.category=category;state.currentGroup=null;state.selected.clear();state.currentAsset=null;state.page=1;state.q="";state.type="all";
    try{if(view==="home")renderHome();else if(view==="groups")renderGroups(category);else{await loadCurrentAssets()}}catch(e){toast(`${t().loadFail}: ${e.message}`,true)}
  }
  async function openGroup(g){state.view="group";state.currentGroup=g;state.category=g.category;state.selected.clear();state.page=1;state.q="";state.type="all";await loadCurrentAssets()}

  function openGroupModal(group=null,category="角色"){
    state.editingGroup=group;$("#groupModalTitle").textContent=group?t().editGroupTitle:t().newGroupTitle;$("#groupName").value=group?.name||"";$("#groupAlias").value=group?.alias||"";$("#groupDescription").value=group?.description||"";$("#groupCategory").innerHTML=CATS.map(c=>`<option value="${c}">${esc(trCat(c))}</option>`).join("");$("#groupCategory").value=group?.category||category||"角色";$("#groupModal").classList.remove("hidden");
  }
  function closeGroupModal(){$("#groupModal").classList.add("hidden");state.editingGroup=null}
  async function saveGroup(){
    const body={name:$("#groupName").value.trim(),alias:$("#groupAlias").value.trim(),category:$("#groupCategory").value,description:$("#groupDescription").value.trim()};if(!body.name)return toast(state.lang==="zh-CN"?"请输入资源组名称":"Enter a group name",true);
    try{let d;if(state.editingGroup)d=await request(`/avs/library/group/${state.editingGroup.id}/update`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});else d=await request("/avs/library/group/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const saved=d.group;closeGroupModal();toast(t().groupSaved);await loadGroups();await refreshStatus();if(state.view==="group"&&state.currentGroup?.id===saved.id){state.currentGroup=saved;await loadCurrentAssets()}else if(state.view==="groups")renderGroups(state.category);else renderHome()}catch(e){toast(e.message,true)}
  }
  async function deleteCurrentGroup(){if(!state.editingGroup)return;if(!confirm(t().confirmDelete))return;try{await request(`/avs/library/group/${state.editingGroup.id}/delete`,{method:"POST"});closeGroupModal();toast(t().groupDeleted);await loadGroups();await refreshStatus();showView("home")}catch(e){toast(e.message,true)}}

  function openAssignModal(){if(!state.selected.size)return toast(t().noSelected,true);const groups=state.groups;$("#assignSummary").textContent=t().assignSummary(state.selected.size);$("#assignGroupSelect").innerHTML=`<option value="">${esc(t().noGroupOption)}</option>`+groups.map(g=>`<option value="${esc(g.id)}">${esc(trCat(g.category))} · ${esc(g.name)}${g.alias?` (@${esc(g.alias)})`:""}</option>`).join("");$("#assignModal").classList.remove("hidden")}
  function closeAssignModal(){$("#assignModal").classList.add("hidden")}
  async function confirmAssign(){const gid=$("#assignGroupSelect").value;if(!gid)return toast(t().noGroupOption,true);try{const d=await request(`/avs/library/group/${gid}/assets/add`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids:[...state.selected]})});toast(t().added(d.changed||0));state.selected.clear();closeAssignModal();await loadGroups();await refreshStatus();await loadCurrentAssets()}catch(e){toast(e.message,true)}}
  async function removeSelectedFromCurrentGroup(){if(!state.currentGroup||!state.selected.size)return;try{const d=await request(`/avs/library/group/${state.currentGroup.id}/assets/remove`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids:[...state.selected]})});toast(t().removed(d.changed||0));state.selected.clear();await loadGroups();state.currentGroup=state.groups.find(g=>g.id===state.currentGroup.id)||state.currentGroup;await refreshStatus();await loadCurrentAssets()}catch(e){toast(e.message,true)}}

  function openAssetDrawer(a){state.currentAsset=a;$("#drawerTitle").textContent=a.display_name;const file=`/avs/library/file/${encodeURIComponent(a.id)}`;let preview=`<div class="fallback">${mediaIcon(a.media_type)}</div>`;if(a.media_type==="image")preview=`<img src="${file}" alt="">`;else if(a.media_type==="video")preview=`<video src="${file}" controls preload="metadata"></video>`;else preview=`<audio src="${file}" controls preload="metadata"></audio>`;
    $("#drawerContent").innerHTML=`<div class="preview-large">${preview}</div><div class="detail-grid"><div class="detail-chip"><div class="detail-chip-label">${esc(t().fileName)}</div><div class="detail-chip-value">${esc(a.file_name)}</div></div><div class="detail-chip"><div class="detail-chip-label">${esc(t().size)}</div><div class="detail-chip-value">${bytes(a.size_bytes)}</div></div><div class="detail-chip"><div class="detail-chip-label">${esc(t().resolution)}</div><div class="detail-chip-value">${a.width&&a.height?`${a.width} × ${a.height}`:"—"}</div></div><div class="detail-chip"><div class="detail-chip-label">${esc(t().duration)}</div><div class="detail-chip-value">${dur(a.duration)}</div></div></div><div class="form-stack"><label>${esc(t().displayName)}<input id="assetName" class="form-input" value="${esc(a.display_name)}"></label><label>${esc(t().alias)}<div class="input-prefix"><b>@</b><input id="assetAlias" class="form-input" value="${esc(a.alias||"")}"></div></label><label>${esc(t().category)}<select id="assetCategory" class="form-input">${[...CATS,"未分类"].map(c=>`<option value="${c}" ${c===a.category?"selected":""}>${esc(trCat(c))}</option>`).join("")}</select></label><label>${esc(t().tags)}<input id="assetTags" class="form-input" value="${esc((a.tags||[]).join(", "))}"></label><label>${esc(t().path)}<input class="form-input" value="${esc(a.relative_path)}" readonly></label></div><div class="drawer-actions"><button id="saveAssetBtn" class="btn primary">${esc(t().save)}</button></div>`;
    $("#saveAssetBtn").onclick=saveCurrentAsset;$("#assetDrawer").classList.remove("hidden")
  }
  function closeAssetDrawer(){$("#assetDrawer").classList.add("hidden");state.currentAsset=null}
  async function saveCurrentAsset(){const a=state.currentAsset;if(!a)return;try{const d=await request(`/avs/library/asset/${a.id}/meta`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({display_name:$("#assetName").value,alias:$("#assetAlias").value,category:$("#assetCategory").value,tags:$("#assetTags").value})});state.currentAsset=d.asset;toast(t().saved);closeAssetDrawer();await refreshStatus();if(["unassigned","files","group"].includes(state.view))await loadCurrentAssets()}catch(e){toast(e.message,true)}}

  function openFolderModal(){$("#folderModal").classList.remove("hidden");loadFolder(state.config.library_path||"")}
  function chooseFolder(){chooseLibraryDirectory({request,nativePicker:state.nativePicker,initialPath:state.config.library_path,lang:state.lang,onProgress:message=>{$("#scanState").textContent=message;},onSelect:async path=>{const d=await request("/avs/library/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({library_path:path})});state.config.library_path=d.library_path;toast(t().folderSaved);await scan();}}).catch(error=>toast(error.message,true));}
  function closeFolderModal(){$("#folderModal").classList.add("hidden")}
  async function loadFolder(path){$("#useFolderBtn").disabled=true;try{const d=await request(`/avs/library/dirs?path=${encodeURIComponent(path||"")}`);state.currentFolder=d.path;state.parentFolder=d.parent||"";$("#folderPath").textContent=d.path;$("#rootSelect").innerHTML=(d.roots||[]).map(r=>`<option value="${esc(r)}">${esc(r)}</option>`).join("");const match=(d.roots||[]).find(r=>d.path.toLowerCase().startsWith(r.toLowerCase()));if(match)$("#rootSelect").value=match;$("#folderGrid").innerHTML=(d.dirs||[]).map(n=>`<button class="folder-item" data-name="${esc(n)}">📁 ${esc(n)}</button>`).join("")||`<div class="notice-card">${esc(t().noSubfolder)}</div>`;$$('.folder-item').forEach(b=>b.onclick=()=>{const sep=d.path.includes("\\")?"\\":"/";loadFolder(d.path.replace(/[\\/]$/,"")+sep+b.dataset.name)});$("#useFolderBtn").disabled=false;}catch(e){toast(e.message,true)}}
  async function useFolder(){if(!state.currentFolder)return;try{const d=await request("/avs/library/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({library_path:state.currentFolder})});state.config.library_path=d.library_path;closeFolderModal();toast(t().folderSaved);await scan()}catch(e){toast(e.message,true)}}
  async function scan(){if(!state.config.library_path)return toast(t().noFolder,true);$("#scanState").textContent=t().scanRunning;$("#scanBtn").disabled=true;try{const d=await request("/avs/library/scan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({library_path:state.config.library_path})});toast(t().scanDone(d.scanned,d.seconds));await refreshStatus();await loadGroups();$("#scanState").textContent=t().ready;if(state.view==="home")renderHome();else if(state.view==="groups")renderGroups(state.category);else await loadCurrentAssets()}catch(e){toast(e.message,true);$("#scanState").textContent=t().scanFail}finally{$("#scanBtn").disabled=false}}
  async function saveLanguage(){await request("/avs/settings/language",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({language:state.lang})})}

  function bindGlobal(){
    $$(".nav-item").forEach(b=>b.onclick=()=>showView(b.dataset.view,b.dataset.category||""));$("#newGroupBtn").onclick=()=>openGroupModal(null,state.category||"角色");$("#scanBtn").onclick=scan;$("#chooseFolderBtnSide").onclick=chooseFolder;const server=document.createElement("button");server.id="chooseServerFolderBtn";server.className="btn ghost";server.onclick=openFolderModal;$("#chooseFolderBtnSide").after(server);
    $("#languageSelect").onchange=async e=>{state.lang=e.target.value;applyI18n();await saveLanguage();if(state.view==="home")renderHome();else if(state.view==="groups")renderGroups(state.category);else renderAssetViewCurrent()};
    $$('[data-close-drawer]').forEach(x=>x.onclick=closeAssetDrawer);$$('[data-close-group-modal]').forEach(x=>x.onclick=closeGroupModal);$$('[data-close-assign-modal]').forEach(x=>x.onclick=closeAssignModal);$$('[data-close-folder-modal]').forEach(x=>x.onclick=closeFolderModal);
    $("#saveGroupBtn").onclick=saveGroup;$("#confirmAssignBtn").onclick=confirmAssign;$("#createWhileAssignBtn").onclick=()=>{closeAssignModal();openGroupModal(null,"角色")};$("#folderUpBtn").onclick=()=>state.parentFolder&&loadFolder(state.parentFolder);$("#rootSelect").onchange=e=>loadFolder(e.target.value);$("#useFolderBtn").onclick=useFolder;
  }

  async function init(){bindGlobal();try{await refreshStatus();await loadGroups();renderHome()}catch(e){toast(`${t().loadFail}: ${e.message}`,true)}}
  init();
})();
