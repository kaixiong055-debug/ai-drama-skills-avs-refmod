const mediaExtension = /\.(png|jpe?g|webp|bmp|gif|tiff?|mp4|mov|mkv|webm|avi|m4v|mpg|mpeg|ts|mts|wav|mp3|flac|m4a|aac|ogg|opus|wma)$/i;

export function serverPathCompatible(path, platform) {
    if (!path || !platform) return true;
    return platform === "nt" ? !/^\/(?!\/)/.test(path) : !/^[a-z]:|\\/i.test(path);
}

export function useNativePicker(status) {
    return Boolean(status?.native_picker && ["localhost", "127.0.0.1", "[::1]", "::1"].includes(window.location.hostname));
}

export async function chooseLibraryDirectory({request, nativePicker, initialPath, onSelect, onProgress, lang="zh-CN"}) {
    const english = lang === "en-US";
    if (nativePicker) {
        const data = await request("/avs/library/pick-directory", {
            method:"POST", headers:{"Content-Type":"application/json"},
            body:JSON.stringify({initial_path:initialPath || ""})
        });
        if (!data.cancelled && data.path) await onSelect(data.path);
        return;
    }
    // This click happens before any await, preserving browser user activation.
    const picker = document.createElement("input");
    picker.type="file";picker.multiple=true;picker.webkitdirectory=true;
    picker.setAttribute("webkitdirectory", "");
    picker.style.display="none";
    document.body.append(picker);
    picker.oncancel=()=>picker.remove();
    picker.onchange=async()=>{
        const files=Array.from(picker.files || []).filter(file=>mediaExtension.test(file.name));
        picker.remove();
        if (!files.length) {onProgress(english ? "No supported media in the selected folder." : "所选文件夹中没有可导入的图片、视频或音频。");return;}
        const progress=document.createElement("div");
        Object.assign(progress.style,{position:"fixed",bottom:"24px",left:"24px",zIndex:"100005",padding:"14px",background:"#202228",color:"white",borderRadius:"8px"});
        document.body.append(progress);
        let id="", path="";
        try {
            for (let index=0;index<files.length;index++) {
                const message=english ? `Uploading selected media ${index+1}/${files.length}` : `正在上传所选素材 ${index+1}/${files.length}`;
                progress.textContent=message;onProgress(message);
                const form=new FormData();form.append("file",files[index]);
                const params=new URLSearchParams({import_id:id,relative_path:files[index].webkitRelativePath});
                const data=await request(`/avs/library/import-folder?${params}`,{method:"POST",body:form});
                id=data.import_id;path=data.library_path;
            }
            await onSelect(path, true);
        } catch(error) {onProgress(error.message);}
        finally {progress.remove();}
    };
    picker.click();
}
