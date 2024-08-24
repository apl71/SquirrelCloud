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