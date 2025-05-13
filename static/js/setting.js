async function register() {
    const register_form = document.getElementById("register_form");
    const form_data = new FormData(register_form);
    form_data.append("admin", document.getElementById("admin_checkbox").checked)
    const form_json = JSON.stringify(Object.fromEntries(form_data.entries()));
    const response = await fetch("/api/register", {
        method: "PUT",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        },
        body: form_json
    });
    const res = await response.json();
    if (res["result"] != "OK") {
        alert("Fail to register user. " + res["message"]);
    } else {
        alert("Success.");
    }
}

async function load_settings() {
    load_theme();
    // hide admin panel
    if (getCookie("admin") == "false") {
        const admin_panel = document.getElementsByClassName("admin_panel");
        for (let i = 0; i < admin_panel.length; i++) {
            admin_panel[i].style.display = "none";
        }
    }
    // load tags
    load_tags();
    // load replica setting
    load_replica_setting();
    load_upload_filter_table()
}

async function load_tags() {
    // clear all tags
    document.getElementById("tag_list").innerHTML = "";
    // fetch tags
    fetch("/api/tag", {
        method: "GET"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            alert("Fail to load tags. " + response["message"]);
            return;
        }
        response["tags"].forEach(element => {
            var tag_list = document.getElementById("tag_list");
            var tag_li = document.createElement("li");
            tag_li.innerText = element;
            tag_li.className = "tag_li";
            // remove button
            var remove_button = document.createElement("button");
            remove_button.innerText = "x";
            remove_button.onclick = function() {
                remove_tag(element);
            };
            tag_li.appendChild(remove_button);
            tag_list.appendChild(tag_li);
        });
    });
}

async function create_tag() {
    const new_tag = prompt("Enter new tag.");
    params = new URLSearchParams({
        "tag": new_tag
    }).toString();
    fetch("/api/tag?" + params, {
        method: "PUT",
        mode: "cors"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_tags();
            return;
        } else {
            alert("Fail to create tag. " + response["message"]);
            return;
        }
    });
}

function remove_tag(tag) {
    params = new URLSearchParams({
        "tag": tag
    }).toString();
    fetch("/api/tag?" + params, {
        method: "DELETE"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_tags();
            return;
        } else {
            alert("Fail to remove tag. " + response["message"]);
            return;
        }
    });
}

function save_replica_setting() {
    // save replica setting in cookie
    value = document.getElementById("replica_checkbox").checked;
    document.cookie = "replica=" + value;
}

function load_replica_setting() {
    // on the load of page, load the setting from cookie
    value = (getCookie("replica") == "true");
    document.getElementById("replica_checkbox").checked = value;
}

function load_upload_filter_table() {
    // load upload filter table
    const upload_filter_table = document.getElementById("uploading_filters_table");
    upload_filter_table.innerHTML = "";
    fetch("/api/upload_filter", {
        method: "GET"
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] != "OK") {
            alert("Fail to load upload filter. " + response["message"]);
            return;
        }
        // generate header
        const thead = document.createElement("thead");
        const header_row = document.createElement("tr");
        const th1 = document.createElement("th");
        th1.innerText = "Filter";
        const th2 = document.createElement("th");
        th2.innerText = "Type";
        const th3 = document.createElement("th");
        th3.innerText = "Value";
        const th4 = document.createElement("th");
        th4.innerText = "Activation";
        const th5 = document.createElement("th");
        th5.innerText = "Action";
        header_row.appendChild(th1);
        header_row.appendChild(th2);
        header_row.appendChild(th3);
        header_row.appendChild(th4);
        header_row.appendChild(th5);
        thead.appendChild(header_row);
        upload_filter_table.appendChild(thead);
        // generate body
        response["filters"].forEach(element => {
            var row = upload_filter_table.insertRow();
            var filter_cell = row.insertCell(0);
            var type_cell = row.insertCell(1);
            var value_cell = row.insertCell(2);
            var activation_cell = row.insertCell(3);
            var action_cell = row.insertCell(4);
            filter_cell.innerHTML = element["filter"];
            type_cell.innerHTML = element["type"];
            value_cell.innerHTML = element["value"];
            activation_cell.innerHTML = "<input type='checkbox' " + (element["active"] ? "checked" : "") + ">";
            activation_cell.firstChild.onclick = function() {
                change_upload_filter_activation(element["uuid"], activation_cell.firstChild.checked);
            }
            // add remove button
            var remove_button = document.createElement("button");
            remove_button.innerText = "x";
            remove_button.onclick = function() {
                remove_upload_filter(element["uuid"]);
            };
            action_cell.appendChild(remove_button);
        });
        // generate row for adding new filter
        var row = upload_filter_table.insertRow();
        var filter_cell = row.insertCell(0);
        var type_cell = row.insertCell(1);
        var value_cell = row.insertCell(2);
        var activation_cell = row.insertCell(3);
        var action_cell = row.insertCell(4);
        // a picker for filter
        filter_cell.appendChild(generate_filter_picker("new_filter"));
        type_cell.appendChild(generate_type_picker("new_type"));
        value_cell.innerHTML = "<input type='text' id='new_value' placeholder='Value'>";
        activation_cell.innerHTML = "<input type='checkbox' id='new_activation' disabled checked>";
        action_cell.innerHTML = "<button id='add_filter_button'>Add</button>";
        document.getElementById("add_filter_button").onclick = function() {
            create_upload_filter();
        };
    });
}

function generate_filter_picker(cell_id) {
    // generate a picker for filter
    var filter_picker = document.createElement("select");
    filter_picker.id = cell_id;
    filter_picker.innerHTML = "<option value=''>Select filter</option>";
    const filters = ["file_name", "file_size", "extension"];
    filters.forEach(element => {
        var option = document.createElement("option");
        option.value = element;
        option.innerText = element;
        filter_picker.appendChild(option);
    });
    return filter_picker;
}

function generate_type_picker(cell_id) {
    // generate a picker for type
    var type_picker = document.createElement("select");
    type_picker.id = cell_id;
    type_picker.innerHTML = "<option value=''>Select type</option>";
    const types = ["IS", "IS_NOT", "CONTAINS", "NOT_CONTAINS", "GREATER", "LESS"];
    types.forEach(element => {
        var option = document.createElement("option");
        option.value = element;
        option.innerText = element;
        type_picker.appendChild(option);
    });
    return type_picker;
}

function change_upload_filter_activation(uuid, active) {
    fetch("/api/upload_filter", {
        method: "POST",
        mode: "cors",
        body: JSON.stringify({
            "uuid": uuid,
            "active": active
        }),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_upload_filter_table();
            return;
        } else {
            alert("Fail to change upload filter activation. " + response["message"]);
            return;
        }
    });
}

function remove_upload_filter(uuid) {
    fetch("/api/upload_filter", {
        method: "DELETE",
        mode: "cors",
        body: JSON.stringify({
            "uuid": uuid
        }),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_upload_filter_table();
            return;
        } else {
            alert("Fail to remove upload filter. " + response["message"]);
            return;
        }
    });
}

function create_upload_filter() {
    const new_filter = document.getElementById("new_filter").value;
    const new_type = document.getElementById("new_type").value;
    const new_value = document.getElementById("new_value").value;
    params = {
        "filter": new_filter,
        "type": new_type,
        "value": new_value
    };
    fetch("/api/upload_filter?" + params, {
        method: "PUT",
        mode: "cors",
        body: JSON.stringify(params),
        headers: {
            "Content-Type": "application/json"
        }
    }).then(response => {
        return response.json();
    }).then(response => {
        if (response["result"] == "OK") {
            load_upload_filter_table();
            return;
        } else {
            alert("Fail to create upload filter. " + response["message"]);
            return;
        }
    });

}