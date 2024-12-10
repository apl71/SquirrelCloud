async function load_preview() {
    const vpath = new URLSearchParams(new URL(window.location.href).search).get("path");
    const extension = vpath.split('.').pop();
    // get file
    const response = await fetch("/api/download?file=" + encodeURIComponent(vpath));
    const type = response.headers.get("Content-Type");
    // show preview
    if (isImageExtension(extension)) {
        const blob = await response.blob();
        const imgURL = URL.createObjectURL(blob);
        const img = document.getElementById("image_preview");
        img.src = imgURL;
        img.style.display = "block";
    } else if (extension == "pdf") {
        const blob = await response.blob();
        const pdfURL = URL.createObjectURL(blob);
        const pdf = document.getElementById("pdf_preview");
        pdf.src = pdfURL;
        pdf.style.display = "block";
    } else if (isVideoExtension(extension)) {
        const blob = await response.blob();
        const vidURL = URL.createObjectURL(blob);
        const vid = document.getElementById("vid_preview");
        vid.src = vidURL;
        vid.style.display = "block";
    } else if (isTextFile(type) || isTextExtension(extension)) {
        const cnter = document.getElementById("text_preview_container");
        cnter.style.display = "flex";
        txt = document.getElementById("text_preview");
        txt.innerHTML = (await response.text());
    } else {
        alert("No preview for this kind of file. Type: " + type);
        window.close();
    }
}

function isTextFile(contenttype) {
    // 检查 MIME 类型
    return contenttype.indexOf("text") >= 0 || contenttype.indexOf("json") >= 0;
}

function isTextExtension(ext) {
    ext = ext.toLowerCase();
    const txtexts = [
        "txt", "rtf", "md", "html", "csv", "json", "xml", "yaml",
        "yml", "log", "swift", "c", "cpp", "h", "hpp", "java", "css",
        "js", "conf", "py"
    ];

    return txtexts.includes(ext);
}

function isImageExtension(ext) {
    ext = ext.toLowerCase();
    const imgexts = [
        "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "tiff", "tif", "ico"
    ];

    return imgexts.includes(ext);
}

function isVideoExtension(ext) {
    ext = ext.toLowerCase();
    const imgexts = [
        "mp4", "mov", "wmv", "flv", "avi", "webm", "avchd", "mkv"
    ];

    return imgexts.includes(ext);
}

async function save_text() {
    const vpath = new URLSearchParams(new URL(window.location.href).search).get("path");
    const filename = Date.now().toString() + "_" + vpath.split('/').pop();
    const base_path = get_parent_directory(vpath);
    // dup of file.js: upload_file()
    // TODO: refactor
    const form_data = new FormData();
    form_data.append("path", base_path);
    const text_blob = new Blob([document.getElementById("text_preview").value], { type: "text/plain" });
    form_data.append("file", text_blob, filename);
    if (getCookie("replica") == "true") {
        form_data.append("replica", true);
    }
    const response = await fetch("/api/upload", {
        method: "POST",
        body: form_data
    });
    const res = await response.json();
    if (res["result"] == "OK") {
        alert("Saved.");
    } else {
        alert("Fail to upload file: " + res["message"]);
    }
}