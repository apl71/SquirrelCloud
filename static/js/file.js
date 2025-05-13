async function load() {
    load_files();
    set_right_click_menu();
    load_theme();
}

function set_right_click_menu() {
    const file_table = document.getElementById("file_table");
    const menu = document.getElementById("right_click_menu");
    let selected_file_path = null;
    // add right click event listener to the table
    file_table.addEventListener("contextmenu", (event) => {
        if (event.target.className == "filename") {
            event.preventDefault();
            selected_file_path = event.target.dataset.path;
            menu.style.left = event.clientX + "px";
            menu.style.top = event.clientY + "px";
            menu.style.display = "block";
        }
    });

    document.addEventListener("click", () => {
        menu.style.display = "none";
    });

    // add event listener to the menu items
    document.getElementById("menu_download").addEventListener("click", () => {
        menu.style.display = "none";
        download_file(selected_file_path);
    });
    document.getElementById("menu_rename").addEventListener("click", () => {
        menu.style.display = "none";
        rename(selected_file_path);
    });
    document.getElementById("menu_move").addEventListener("click", () => {
        menu.style.display = "none";
        move(selected_file_path);
    });
    document.getElementById("menu_delete").addEventListener("click", async () => {
        menu.style.display = "none";
        if (selected_file_path.startsWith("/recycle")) {
            if (confirm("Are you sure to permenently delete this file?")) {
                delete_file_or_directory(selected_file_path);
            }
        } else {
            let path = "/recycle/" + selected_file_path.substring(selected_file_path.lastIndexOf("/") + 1);
            let count = 1;
            while ((await search(path))["files"].length != 0) {
                path = "/recycle/" + selected_file_path.substring(selected_file_path.lastIndexOf("/") + 1) + "(" + count + ")";
                count++;
            }
            move_to_path(selected_file_path, path);
        }
    });
    document.getElementById("menu_pin").addEventListener("click", () => {
        menu.style.display = "none";
        pin_file(selected_file_path, true);
    });
    document.getElementById("menu_unpin").addEventListener("click", () => {
        menu.style.display = "none";
        pin_file(selected_file_path, false);
    });
    document.getElementById("menu_preview").addEventListener("click", () => {
        menu.style.display = "none";
        open_preview(selected_file_path);
    });
    document.getElementById("menu_share").addEventListener("click", () => {
        menu.style.display = "none";
        const username = prompt("Enter the username.");
        send_share_request(selected_file_path, username);
    });
    document.getElementById("menu_link").addEventListener("click", () => {
        menu.style.display = "none";
        create_external_link(selected_file_path);
    });
    document.getElementById("menu_size").addEventListener("click", () => {
        menu.style.display = "none";
        compute_size(selected_file_path);
    });
}

function compute_size(path) {
    params = new URLSearchParams({
        "path": path
    }).toString();
    fetch("/api/directory_size?" + params, {
        method: "GET"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            size_cell = document.getElementById(path + "_size");
            size_cell.innerText = user_friendly_size(response["size"]);
        } else {
            alert("Fail to compute the size. " + response["message"]);
        }
    });
}

async function load_files() {
    const path = document.getElementById("current_path").value;
    // check if the path exists
    params = new URLSearchParams({
        "type": "TYPE_DIR",
        "path": path
    }).toString();
    var response = await fetch("/api/file_exist?" + params, {
        method: "GET",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        }
    });
    response = await response.json();
    if (response["result"] != "OK") {
        alert("Interface error: /api/file_exist returns non-OK: " + result["message"]);
    }
    if (!response["exist"]) {
        alert("Directory does not exist.");
        // load root path into table
        document.getElementById("current_path").value = "/";
        load_files();
        return;
    }
    // get files under the path
    params = new URLSearchParams({
        "path": path
    }).toString();
    response = await fetch("/api/list?" + params, {
        method: "GET",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        }
    });
    // load data into table
    load_file_table(await response.json());
    document.getElementById("current_path").value = path;
}

async function load_file_table(data) {
    var table = document.getElementById("file_table");
    // clear table
    while (table.children.length > 1) {
        table.removeChild(table.lastChild);
    }
    // put pinned file or directory on the top
    data["files"].sort((a, b) => {
        if (a["pinned"] && b["pinned"]) {
            return 0;
        } else if (a["pinned"]) {
            return -1;
        } else if (b["pinned"]) {
            return 1;
        }
        return 0;
    });
    // create a select view for tag
    var tag_list = await get_tag_list();
    data["files"].forEach(element => {
        let row = document.createElement("tr");
        // ------------------------------------ icon ------------------------------------
        let icon_td = document.createElement("td");
        let icon = document.createElement("img");
        icon.className = "icon"
        icon_td.appendChild(icon);
        // ------------------------------------ filename ------------------------------------
        let filename_td = document.createElement("td");
        const full_path = element["path"];
        let filename = document.createElement("label");
        // save full path for later use
        filename.dataset.path = full_path;
        filename.innerText = full_path.substring(full_path.lastIndexOf("/") + 1);
        filename.className = "filename";
        filename_td.appendChild(filename);
        // ------------------------------------ file size ------------------------------------
        let size = document.createElement("td");
        size.id = full_path + "_size";
        if (element["size"]) {
            size.innerText = user_friendly_size(Number(element["size"]));
        }
        // ------------------------------------ tags ------------------------------------
        let tags_td = document.createElement("td");
        element["tags"].forEach(tag => {
            // create span for tag
            let tag_span = document.createElement("span");
            tag_span.innerText = tag;
            tag_span.className = "tag";
            tags_td.appendChild(tag_span);
            // create remove button for tag
            let tag_remove_button = document.createElement("button");
            tag_remove_button.textContent = "x";
            tag_remove_button.onclick = function() {
                remove_tag(full_path, tag);

            }
            tag_span.appendChild(tag_remove_button);
        });
        let selector = get_tag_selector(tag_list);
        selector.innerHTML = '<option value="">Add tag</option>' + selector.innerHTML;
        selector.onchange = function() {
            if (this.value != "") {
                attach_tag_to_file(full_path, this.value);
            }
        };
        tags_td.appendChild(selector);
        // ------------------------------------ remark ------------------------------------
        let remark = document.createElement("td");
        let remark_edit = document.createElement("input");
        remark_edit.value = element["remark"];
        remark_edit.id = full_path + "_remark"; // use full path as id
        let remark_upload = document.createElement("button");
        remark_upload.innerText = "✔";
        remark_upload.onclick = function() {
            update_remark(full_path);
        }
        remark.id = full_path + "_remark_container";
        remark.appendChild(remark_edit);
        remark.appendChild(remark_upload);
        // ------------------------------------ create time ------------------------------------
        let created = document.createElement("td");
        created.className = "create_time";
        created.innerText = convertDateFormat(element["create_at"]);
        // ------------------------------------ delete ------------------------------------
        // let delete_td = document.createElement("td");
        // let delete_button = document.createElement("button");
        // delete_td.className = "delete_td";
        // delete_button.innerText = "❌";
        // delete_td.appendChild(delete_button);
        // ------------------------------------ pinned ------------------------------------
        let pin_td = document.createElement("td");
        pin_td.className = "pin_td";
        let pin_button = document.createElement("button");
        if (element["pinned"]) {
            pin_button.innerText = "📎";
            pin_button.onclick = function() {
                pin_file(full_path, false);
            }
        } else {
            pin_button.innerText = "🧷";
            pin_button.onclick = function() {
                pin_file(full_path, true);
            }
        }
        pin_td.appendChild(pin_button);

        row.appendChild(icon_td);
        row.appendChild(filename_td);
        row.appendChild(size);
        row.appendChild(tags_td);
        row.appendChild(remark);
        row.appendChild(created);
        row.appendChild(pin_td);
        table.appendChild(row);
        if (element["type"] == "TYPE_FILE") {
            filename_td.ondblclick = function() {
                download_file(element["path"]);
            };
            icon.onclick = function() {
                open_preview(element["path"]);
            };
            icon.src = "/img/file.ico";
        } else if (element["type"] == "TYPE_DIR" || element["type"] == "TYPE_LINK") {
            row.ondblclick = function() {
                document.getElementById("current_path").value = element["path"];
                load_files(element["path"]);
            };
            icon.src = "/img/dir.ico";
        }
    });
}

function download_file(vpath) {
    window.location = "/api/download?file=" + encodeURIComponent(vpath);
}

async function open_preview(vpath) {
    window.open("/preview.html?path=" + encodeURIComponent(vpath), "_blank");
}

async function upload_common(inputElementId, apiEndpoint, isDirectory = false) {
    const input = document.getElementById(inputElementId);
    const container = document.getElementById('progress_bar_container');
    const progress_bar = document.getElementById('progress_bar');
    const progress_bytes = document.getElementById('progress_bytes');
    const progress_speed = document.getElementById('progress_speed');
    const progress_percent = document.getElementById('progress_percent');
    const progress_remaining = document.getElementById('progress_remaining');
    container.style.display = "flex"; // Show progress bar

    // Disable upload buttons
    const upload_file_button = document.getElementById("upload_file_button");
    const upload_directory_button = document.getElementById("upload_directory_button");
    upload_file_button.disabled = true;
    upload_directory_button.disabled = true;

    const files = input.files;
    if (files.length === 0) {
        alert(isDirectory ? "No directory selected." : "No file selected.");
        return;
    }

    const form_data = new FormData();
    form_data.append("path", document.getElementById("current_path").value);

    let filtered_files = [];

    if (isDirectory) {
        progress_bytes.innerText = "We are checking the filters... Please wait.";
        let filters = await get_all_filters();
        if (filters["result"] != "OK") {
            alert("Fail to get filters: " + filters["message"] + ". No filters will be applied.");
            return;
        } else {
            filters = filters["filters"];
        }
        let file_index = 0;
        // Add files with relative paths for directory upload
        for (const [_, file] of Array.from(files).entries()) {
            const filtered = await check_file_filtered(filters, file);
            if (filtered) {
                filtered_files.push(file.name);
            } else {
                form_data.append(`file${file_index}`, file, file.webkitRelativePath);
                file_index++;
            }
        }
        form_data.append("file_num", file_index);
        progress_bytes.innerText = "";
    } else {
        // Add single file for file upload
        form_data.append("file", files[0]);
    }

    if (getCookie("replica") === "true") {
        form_data.append("replica", true);
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', apiEndpoint, true);

    let last_loaded = 0;
    let last_timestamp = Date.now();

    xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && (Date.now() - last_timestamp > 1000 || last_loaded === 0)) {
            const percent = (event.loaded / event.total) * 100;
            progress_bar.value = percent;
            progress_bytes.innerText = user_friendly_size(event.loaded) + "/" + user_friendly_size(event.total);
            progress_percent.innerText = percent.toFixed(1) + "%";
            progress_speed.innerText = user_friendly_size((event.loaded - last_loaded) / ((Date.now() - last_timestamp) / 1000)) + "/s";
            const speed = (event.loaded - last_loaded) / ((Date.now() - last_timestamp) / 1000);
            progress_remaining.innerText = ((event.total - event.loaded) / speed).toFixed(0) + "s remaining";
            last_loaded = event.loaded;
            last_timestamp = Date.now();
        }
    };

    xhr.onload = () => {
        if (xhr.status === 200) {
            progress_bar.value = 100;
            const result = JSON.parse(xhr.responseText);
            if (result["result"] === "OK") {
                load_files();
            } else {
                alert("Fail to upload: " + result["message"]);
            }
            // Enable upload buttons
            upload_file_button.disabled = false;
            upload_directory_button.disabled = false;
            setTimeout(() => {
                container.style.display = "none"; // Hide progress bar after 5 seconds
                progress_bar.value = 0; // Reset progress bar value
            }, 3000);
        } else {
            alert('Upload failed.');
        }
    };

    xhr.onerror = () => {
        alert('Error uploading.');
    };

    xhr.send(form_data);
    if (filtered_files.length > 0 && isDirectory) {
        alert("The following " + filtered_files.length + " file(s) are filtered: " + filtered_files.join(", "));
    }
}

async function upload_file() {
    upload_common('file', '/api/upload', false);
}

async function upload_directory() {
    upload_common('directory', '/api/upload_directory', true);
}

function mkdir() {
    const new_dir = prompt("Enter your folder name.");
    if (new_dir.indexOf("/") > -1) {
        alert("'/' cannot appear in a folder name.");
        return;
    }
    const current_path = document.getElementById("current_path").value;
    const full_dir = current_path + (current_path == "/" ? "" : "/") + new_dir;
    params = new URLSearchParams({
        "path": full_dir
    }).toString();
    fetch("/api/mkdir?" + params, {
        method: "POST"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_files();
        } else {
            alert("Fail to create directory: " + response["message"]);
        }
    });
}

async function delete_file_or_directory(path) {
    params = new URLSearchParams({
        "file": path
    }).toString();
    const response = await fetch("/api/delete?" + params, {
        method: "DELETE",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        }
    });
    const res = await response.json();
    if (res["result"] == "OK") {
        load_files();
    } else {
        alert("Fail to remove file or directory: " + res["message"]);
    }
}

async function search(query) {
    const params = new URLSearchParams({
        "query": query
    }).toString();
    const json = await fetch("/api/search?" + params.toString(), {
        method: "GET",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        }
    });
    const result = await json.json();
    return result;
}

function search_file() {
    const query = document.getElementById("search").value;
    result = search(query);
    if (result["result"] == "OK") {
        load_file_table(result);
    } else {
        alert(result["message"]);
    }
    // params = new URLSearchParams({
    //     "query": query.value
    // }).toString();
    // fetch("/api/search?" + params, {
    //     method: "GET"
    // }).then(response => {
    //     return response.json();
    // }).then(response => {
    //     if (response["result"] == "OK") {
    //         load_file_table(response);
    //     } else {
    //         alert(response["message"]);
    //     }
    // });
}

async function update_remark(path) {
    const data = {
        "remark": document.getElementById(path + "_remark").value,
        "file": path
    };
    const response = await fetch("/api/remark", {
        method: "POST",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    const res = await response.json();
    if (res["result"] == "OK") {
        load_files();
    } else {
        alert("Fail to update the remark. " + res["message"]);
    }
}

async function pin_file(full_path, pin) {
    params = new URLSearchParams({
        "path": full_path,
        "pin": pin
    }).toString();
    const response = await fetch("/api/pin?" + params, {
        method: "POST",
        mode: "cors"
    });
    const res = await response.json();
    if (res["result"] == "OK") {
        load_files();
    } else {
        alert("Fail to pin or unpin file: " + res["message"]);
    }
}

function convertDateFormat(gmtDateStr) {
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const date = new Date(gmtDateStr);

    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const hour = date.getHours().toString().padStart(2, '0');
    const minute = date.getMinutes().toString().padStart(2, '0');
    const second = date.getSeconds().toString().padStart(2, '0');
    const dayOfWeek = days[date.getDay()];

    return `${year}/${month}/${day} ${hour}:${minute}:${second} ${dayOfWeek}`;
}

async function get_tag_list() {
    const response = await fetch("/api/tag", {
        method: "GET"
    });
    const data = await response.json();
    return data["tags"];
}

function get_tag_selector(tag_list) {
    let selector = document.createElement("select");
    tag_list.forEach(tag => {
        let option = document.createElement("option");
        option.value = option.innerText = tag;
        selector.appendChild(option);
    });
    return selector;
}

function attach_tag_to_file(file, tag) {
    params = new URLSearchParams({
        "tag": tag,
        "path": file
    }).toString();
    fetch("/api/file_tag?" + params, {
        method: "PUT"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_files();
        } else {
            alert("Fail to attach tag. " + response["message"]);
        }
    });
}

function remove_tag(file, tag) {
    params = new URLSearchParams({
        "tag": tag,
        "path": file
    }).toString();
    fetch("/api/file_tag?" + params, {
        method: "DELETE"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_files();
        } else {
            alert("Fail to remove tag. " + response["message"]);
        }
    });
}

function rename(path) {
    const new_name = prompt("Enter new name.", path.substring(path.lastIndexOf("/") + 1)).trim();
    if (new_name === null) {
        return;
    }
    const current_path = document.getElementById("current_path").value;
    const new_path = current_path + (current_path == "/" ? "" : "/") + new_name;
    const data = {
        "path": path,
        "new_path":  new_path
    };
    fetch("/api/rename", {
        method: "POST",
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_files();
        } else {
            alert("Fail to rename. " + response["message"]);
        }
    });
}

function move(path) {
    let target_path = prompt("Enter path.").trim();
    if (target_path === null) {
        return;
    }
    const filename = path.substring(path.lastIndexOf("/") + 1);
    if (target_path.slice(-1) == '/') {
        target_path = target_path + filename;
    } else {
        target_path = target_path + "/" + filename;
    }
    move_to_path(path, target_path);
}

function move_to_path(src, dest) {
    const data = {
        "path": src,
        "new_path":  dest
    };
    fetch("/api/rename", {
        method: "POST",
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_files();
        } else {
            alert("Fail to move. " + response["message"]);
        }
    });
}

function to_parent() {
    const current_path = document.getElementById("current_path").value;
    if (current_path == "/") {
        return;
    }
    let parent_path = current_path.substring(0, current_path.lastIndexOf('/'));
    if (parent_path == "") {
        parent_path = "/";
    }
    document.getElementById("current_path").value = parent_path;
    load_files();
}

function to_home() {
    document.getElementById("current_path").value = "/";
    load_files();
}

function create_external_link(fullpath) {
    fetch("/api/external_link", {
        method: "POST",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "path": fullpath,
            "expire": Math.floor((Date.now() + (10 * 24 * 60 * 60 * 1000)) / 1000)
        })
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            alert("Fail to create external link. " + response["message"]);
        } else {
            alert("The link will expire in 10 days: " + response["link"]);
        }
    });
}

function send_share_request(selected_file_path, username) {
    fetch("/api/share_request", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "share_path": selected_file_path,
            "target_user": username
        })
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            alert("Fail to share the file. " + response["message"]);
        } else {
            alert("Share request sent.");
        }
    });
}

async function get_all_filters() {
    const response = await fetch("/api/upload_filter", {
        method: "GET"
    });
    const data = await response.json();
    return data;
}

async function check_file_filtered(filters, file) {
    for (const filter of filters) {
        if (filter["filter"] === "file_name" && filter["active"]) {
            if (filter["type"] === "IS" && file.name === filter["value"]) {
                return true;
            } else if (filter["type"] === "IS_NOT" && file.name !== filter["value"]) {
                return true;
            } else if (filter["type"] === "CONTAINS" && file.name.includes(filter["value"])) {
                return true;
            } else if (filter["type"] === "NOT_CONTAINS" && !file.name.includes(filter["value"])) {
                return true;
            }
        }
        if (filter["filter"] === "file_size" && filter["active"]) {
            if (filter["type"] === "GREATER" && file.size > parseInt(filter["value"])) {
                return true;
            } else if (filter["type"] === "LESS" && file.size < parseInt(filter["value"])) {
                return true;
            }
        }
        if (filter["filter"] === "extension" && filter["active"]) {
            if (filter["type"] === "IS" && file.name.endsWith(filter["value"])) {
                return true;
            } else if (filter["type"] === "IS_NOT" && !file.name.endsWith(filter["value"])) {
                return true;
            }
        }
    }
    return false;
}