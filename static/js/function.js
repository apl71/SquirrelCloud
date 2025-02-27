function load_function() {
    load_theme();
    load_external_links();
    load_http_download_tasks();
    load_notification();
    // update http download status per second
    setInterval(() => {
        load_http_download_tasks();
    }, 1000);
    // update notification per minute
    setInterval(() => {
        load_notification();
    }, 60 * 1000);
}

function find_replicas() {
    // remove table
    document.getElementById("replica_table").innerHTML = "";
    // show loading
    document.getElementById("loading").style.display = "block";
    // get replicas
    fetch("/api/replica_list", {
        method: "GET"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to get replicas.");
            return;
        }
        // hide loading
        document.getElementById("loading").style.display = "none";
        // show replicas
        const table = document.getElementById("replica_table");
        const thead = document.createElement("thead");
        const header_row = document.createElement("tr");
        const th1 = document.createElement("th");
        th1.textContent = "Path";
        header_row.appendChild(th1);
        const th4 = document.createElement("th");
        th4.textContent = "Remove";
        header_row.appendChild(th4);
        const th2 = document.createElement("th");
        th2.textContent = "Hash(truncated)";
        header_row.appendChild(th2);
        const th3 = document.createElement("th");
        th3.textContent = "Size";
        header_row.appendChild(th3);
        thead.appendChild(header_row);
        table.insertBefore(thead, table.firstChild);
        
        const tbody = document.createElement("tbody");
        table.insertBefore(tbody, table.firstChild);
        const replicas = result["files"];
        replicas.sort((a, b) => b["size"] - a["size"]);
        replicas.forEach(replica => {
            const path_len = replica["paths"].length;
            replica["paths"].forEach((path, index) => {
                const row = tbody.insertRow(-1);
                const path_cell = row.insertCell(0);
                path_cell.innerHTML = path;
                const remove_cell = row.insertCell(1);
                remove_cell.className = "center_cell";
                const remove_button = document.createElement("button");
                remove_cell.appendChild(remove_button);
                remove_button.textContent = "X";
                remove_button.onclick = function() {
                    // TODO: side effect: call to load_files()
                    delete_file_or_directory(path);
                    find_replicas();
                };
                if (index == 0) {
                    const hash_cell = row.insertCell(2);
                    hash_cell.innerHTML = replica["hash"].substring(0, 16);
                    hash_cell.rowSpan = path_len;
                    hash_cell.title = replica["hash"];
                    hash_cell.className = "center_cell";
                    const size_cell = row.insertCell(3);
                    size_cell.innerHTML = user_friendly_size(parseInt(replica["size"]));
                    size_cell.rowSpan = path_len;
                    size_cell.className = "center_cell";
                }
            });
        });
    })
}

async function get_host() {
    const response = await fetch("/api/host", {
        method: "GET"
    });
    const result = await response.json();
    if (result["result"] != "OK") {
        alert("Failed to get host.");
        return "HOST";
    }
    return result["host"];
}

async function load_external_links() {
    const host = await get_host();
    fetch("/api/all_external_links", {
        method: "GET"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to get external links.");
            return;
        }
        const external_links = result["links"];
        const table = document.getElementById("external_link_table");
        table.innerHTML = "";
        // table header
        const thead = document.createElement("thead");
        const header_row = document.createElement("tr");
        const th1 = document.createElement("th");
        th1.textContent = "Path";
        header_row.appendChild(th1);
        const th2 = document.createElement("th");
        th2.textContent = "Link";
        header_row.appendChild(th2);
        const th3 = document.createElement("th");
        th3.textContent = "Expire Time";
        header_row.appendChild(th3);
        const th4 = document.createElement("th");
        th4.textContent = "Remove";
        header_row.appendChild(th4);
        thead.appendChild(header_row);
        table.insertBefore(thead, table.firstChild);
        // table body
        const tbody = document.createElement("tbody");
        table.appendChild(tbody);
        tbody.innerHTML = "";
        external_links.forEach(link => {
            const row = tbody.insertRow(-1);
            const path_cell = row.insertCell(0);
            path_cell.innerHTML = link["path"];
            const url_cell = row.insertCell(1);
            const url = document.createElement("a");
            url_cell.appendChild(url);
            url.innerHTML = "https://" + host + "/api/external_link?key=" + link["key"];
            url.href = url.innerHTML;
            const expire_cell = row.insertCell(2);
            expire_cell.innerHTML = link["expire"];
            const remove_cell = row.insertCell(3);
            remove_cell.className = "center_cell";
            const remove_button = document.createElement("button");
            remove_cell.appendChild(remove_button);
            remove_button.textContent = "X";
            remove_button.onclick = function() {
                delete_external_link(link["key"]);
                load_external_links();
            };
        });
    });
}

function delete_external_link(key) {
    fetch("/api/remove_external_link?key=" + key, {
        method: "DELETE"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to delete external link.");
            return;
        }
    });
}

function download_http() {
    const url = document.getElementById("downloader_url").value;
    fetch("/api/http_download?url=" + url, {
        method: "POST"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to download http file.");
            return;
        }
        load_http_download_tasks();
    });
}

function load_http_download_tasks() {
    fetch("/api/http_download_tasks", {
        method: "GET"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to get http download tasks.");
            return;
        }
        const tasks = result["tasks"];
        const table = document.getElementById("download_task_table");
        table.innerHTML = "";
        // table header
        const thead = document.createElement("thead");
        const header_row = document.createElement("tr");
        const th1 = document.createElement("th");
        th1.textContent = "URL";
        header_row.appendChild(th1);
        const th2 = document.createElement("th");
        th2.textContent = "Progress";
        header_row.appendChild(th2);
        const th3 = document.createElement("th");
        th3.textContent = "Remove";
        header_row.appendChild(th3);
        thead.appendChild(header_row);
        table.insertBefore(thead, table.firstChild);
        // table body
        const tbody = document.createElement("tbody");
        table.appendChild(tbody);
        tbody.innerHTML = "";
        tasks.forEach(task => {
            const row = tbody.insertRow(-1);
            const url_cell = row.insertCell(0);
            url_cell.innerHTML = task["url"];
            const status_cell = row.insertCell(1);
            const percent = (task["downloaded"] * 100 / task["total"]).toFixed(2);
            status_cell.innerHTML = user_friendly_size(task["downloaded"]) + " / " + user_friendly_size(task["total"]) + " (" + percent + "%)";
            const remove_cell = row.insertCell(2);
            remove_cell.className = "center_cell";
            const remove_button = document.createElement("button");
            remove_cell.appendChild(remove_button);
            remove_button.textContent = "X";
            remove_button.onclick = function() {
                delete_http_download_task(task["task_id"]);
                load_http_download_tasks();
            };
        });
    });
}

function delete_http_download_task(id) {
    fetch("/api/http_download_stop?task_id=" + id, {
        method: "DELETE"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to delete http download task.");
            return;
        }
    });
}

function load_notification() {
    fetch("/api/notification", {
        method: "GET"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to get notification.");
            return;
        }
        const notifications = result["notifications"];
        // create notification table
        const table = document.getElementById("notification_table");
        table.innerHTML = "";
        // table header
        const thead = document.createElement("thead");
        const header_row = document.createElement("tr");
        const th1 = document.createElement("th");
        th1.textContent = "Title";
        header_row.appendChild(th1);
        const th2 = document.createElement("th");
        th2.textContent = "Content";
        header_row.appendChild(th2);
        const th3 = document.createElement("th");
        th3.textContent = "Time";
        header_row.appendChild(th3);
        const th4 = document.createElement("th");
        th4.textContent = "Operation";
        header_row.appendChild(th4);
        thead.appendChild(header_row);
        table.insertBefore(thead, table.firstChild);
        // table body
        const tbody = document.createElement("tbody");
        table.appendChild(tbody);
        tbody.innerHTML = "";
        notifications.forEach(notification => {
            const row = tbody.insertRow(-1);
            const title_cell = row.insertCell(0);
            title_cell.innerHTML = notification["title"];
            const content_cell = row.insertCell(1);
            content_cell.innerHTML = notification["content"];
            const time_cell = row.insertCell(2);
            time_cell.innerHTML = notification["create_at"];
            const operation_cell = row.insertCell(3);
            operation_cell.className = "center_cell";
            if (notification["type"] == "TYPE_SHARE_REQUEST") {
                const accept_button = document.createElement("button");
                operation_cell.appendChild(accept_button);
                accept_button.textContent = "Accept";
                accept_button.onclick = function() {
                    // get path
                    const path = prompt("Please enter the path to share:");
                    accept_share_request(notification["uuid"], path);
                };
            }
            const dismiss_button = document.createElement("button");
            operation_cell.appendChild(dismiss_button);
            dismiss_button.textContent = "Dismiss";
            dismiss_button.onclick = function() {
                remove_notification(notification["uuid"]);
            };
        });
    });
}

function remove_notification(uuid) {
    fetch("/api/notification", {
        method: "DELETE",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "uuid": uuid
        })
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to remove notification.");
            return;
        } else {
            load_notification();
        }
    });
}

function accept_share_request(uuid, path) {
    fetch("/api/share_request", {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "notification_uuid": uuid,
            "path": path
        })
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to accept share request: " + result["message"]);
            return;
        } else {
            load_notification();
        }
    });
}