function load_plugin() {
    load_theme();
    load_plugin_list();
}

async function get_plugin_list() {
    const response = await fetch("/api/get_plugins", {
        method: "GET",
        headers: {
            "Content-Type": "application/json"
        },
    }).then(response => response.json());
    const result = response["result"];
    if (result !== "OK") {
        alert("Failed to get plugin list: " + response["message"]);
        return;
    }
    return response["plugins"];
}

async function load_plugin_list() {
    const plugins = await get_plugin_list();
    const plugin_list_ul = document.getElementById("plugin_list_ul");
    plugins.forEach(plugin_item => {
        const plugin_li = document.createElement("li");
        const plugin_a = document.createElement("a");
        plugin_a.onclick = function() {
            to_plugin(plugin_item["root"]);
        }
        plugin_a.innerText = plugin_item["name"];
        plugin_li.appendChild(plugin_a);
        plugin_list_ul.appendChild(plugin_li);
    });
}

function to_plugin(plugin_root) {
    document.getElementById("plugin_frame").src = "";
    document.getElementById("plugin_frame").src = plugin_root + "/index.html";
}