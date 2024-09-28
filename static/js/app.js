function to_page(page) {
    document.getElementById("frame").src = page;
}

async function load_app() {
    // check login status
    await fetch("/api/session_status", {
        method: "GET",
        redirect: "follow",
        mode: "cors"
    }).then((response) => {
        if (response.redirected) {
            window.location.href = response.url;
        }
    });
    let version = await get_version();
    document.getElementById("version_number").innerText = version;
}

async function logout() {
    var response = await fetch("/api/logout", {
        method: "DELETE",
    });
    response = await response.json();
    if (response["result"] == "OK") {
        alert("Success. Redirecting.");
        window.location.href = "/login.html";
    } else {
        alert("Fail to logout.");
    }
}