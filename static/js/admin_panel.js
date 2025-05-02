function initialize_server_status() {
    load_disk_usage();
    load_server_version();
    load_users();
    load_plugins();
    load_theme();
    load_config();
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
    var response = await fetch("/api/update", {
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

function load_plugins() {
    fetch("/api/get_remote_plugins", {
        method: "GET"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            return;
        } else {
            const plugins = response["plugins"];
            const plugin_table = document.getElementById("plugin_table");
            plugins.forEach(plugin => {
                const tr = document.createElement("tr");
                const td1 = document.createElement("td");
                td1.innerText = plugin["name"];
                tr.appendChild(td1);
                const td2 = document.createElement("td");
                td2.innerText = plugin["version"];
                tr.appendChild(td2);
                const td3 = document.createElement("td");
                const install_button = document.createElement("button");
                install_button.innerText = "Install";
                install_button.onclick = function() {
                    install_plugin(plugin["name"], plugin["version"]);
                }
                td3.appendChild(install_button);
                tr.appendChild(td3);
                plugin_table.appendChild(tr);
            });
        }
    });
}

function install_plugin(name, version) {
    const params = {
        "name": name,
        "version": version,
        "reinstall": false
    };
    const url_params = new URLSearchParams(params);
    fetch("/api/install_plugin?" + url_params.toString(), {
        method: "POST",
        body: JSON.stringify({
            "name": name,
            "version": version,
            "reinstall": false
        })
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            alert("Failed to install plugin.");
            return;
        }
        alert("Plugin installed.");
    });
}

function load_config() {
    fetch("/api/config", {
        method: "GET"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            return;
        } else {
            const config = response["config"];
            const config_table = document.getElementById("config_table");
            for (const key in config) {
                const tr = document.createElement("tr");
                const td1 = document.createElement("td");
                td1.innerText = key;
                tr.appendChild(td1);
                const td2 = document.createElement("td");
                const input = document.createElement("input");
                input.type = "text";
                input.value = config[key];
                td2.appendChild(input);
                tr.appendChild(td2);
                const td3 = document.createElement("td");
                const save_button = document.createElement("button");
                save_button.innerText = "Save";
                save_button.onclick = function() {
                    const value = input.value;
                    update_config(key, value);
                }
                td3.appendChild(save_button);
                const remove_button = document.createElement("button");
                remove_button.innerText = "Remove";
                remove_button.onclick = function() {
                    const value = input.value;
                    // TODO: remove config
                    update_config(key, null);
                }
                td3.appendChild(remove_button);
                tr.appendChild(td3);
                config_table.appendChild(tr);
                if (key == "DB_PWD") {
                    input.type = "password";
                }
            }
        }
    });
}

function update_config(key, value) {
    const configUpdate = {};
    configUpdate[key] = value;

    fetch("/api/config", {
        method: "POST",
        body: JSON.stringify(configUpdate),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            alert("Failed to update config.");
            return;
        }
        alert("Config updated. Restarting...");
    });

}