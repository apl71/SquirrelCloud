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