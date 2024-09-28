function initialize_server_status() {
    load_disk_usage();
    load_server_version();
}

function load_disk_usage() {
    fetch("/api/disk_usage", {
        method: "GET"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            return;
        } else {
            document.getElementById("total_space").innerText = user_friendly_size(response["total_space"]);
            document.getElementById("used_space").innerText = user_friendly_size(response["used_space"]);
            document.getElementById("app_used_space").innerText = user_friendly_size(response["app_used_space"]);
        }
    });
}

function load_server_version() {
    load_current_version();
    load_latest_version();
}

async function load_current_version() {
    const version = await get_version();
    document.getElementById("current_version").innerText = version;
}

async function load_latest_version() {
    const version = await get_latest_version();
    document.getElementById("latest_version").innerText = version;
}

async function update_server() {
    document.getElementById("update_message").innerText = "Checking version...";
    const current_version = await get_version();
    const latest_version = await get_latest_version();
    if (current_version == latest_version) {
        document.getElementById("update_message").innerText = "No new version.";
        return;
    }
    document.getElementById("update_message").innerText = "Updating... Please hold on.";
    var response = await fetch("/api/check_update", {
        method: "GET"
    });
    response = await response.json();
    document.getElementById("latest_version").innerText = response["message"];
}