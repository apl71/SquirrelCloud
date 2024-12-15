function initialize_server_status() {
    load_disk_usage();
    load_server_version();
    load_users();
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

function load_users() {
    // remove table
    document.getElementById("user_table").innerHTML = "";
    // get replicas
    fetch("/api/all_users", {
        method: "GET"
    }).then(
        response => response.json()
    ).then(result => {
        if (result["result"] != "OK") {
            alert("Failed to get users.");
            return;
        }
        // create table
        const table = document.getElementById("user_table");
        const thead = document.createElement("thead");
        const header_row = document.createElement("tr");
        // create header
        const th1 = document.createElement("th");
        th1.textContent = "UUID";
        header_row.appendChild(th1);
        const th4 = document.createElement("th");
        th4.textContent = "Username";
        header_row.appendChild(th4);
        const th2 = document.createElement("th");
        th2.textContent = "Email";
        header_row.appendChild(th2);
        const th3 = document.createElement("th");
        th3.textContent = "Role";
        header_row.appendChild(th3);
        const th5 = document.createElement("th");
        th5.textContent = "Created at";
        header_row.appendChild(th5);
        thead.appendChild(header_row);
        table.insertBefore(thead, table.firstChild);
        // create body
        const tbody = document.createElement("tbody");
        table.insertBefore(tbody, table.firstChild);
        const users = result["users"];
        users.forEach(user => {
            const row = tbody.insertRow(-1);
            // uuid
            const uuid_cell = row.insertCell(0);
            uuid_cell.innerHTML = user["uuid"];
            uuid_cell.className = "center_cell";
            // username
            const username_cell = row.insertCell(1);
            username_cell.innerHTML = user["username"];
            // email
            const email_cell = row.insertCell(2);
            email_cell.innerHTML = user["email"];
            // role
            const role_cell = row.insertCell(3);
            role_cell.innerHTML = user["role"];
            role_cell.className = "center_cell";
            // created at
            const created_at_cell = row.insertCell(4);
            created_at_cell.innerHTML = user["create_at"];
            created_at_cell.className = "center_cell";
        });
    })
}