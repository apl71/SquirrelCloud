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