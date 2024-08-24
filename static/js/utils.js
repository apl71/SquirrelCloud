// input an integer in bytes, return a user friendly size expression
function user_friendly_size(size) {
    const u = ["Bytes", "KB", "MB", "GB", "TB"];
    var count = 0;
    while (size >= 1024 && count < 4) {
        size /= 1024;
        count += 1;
    }
    return size.toFixed(2) + u[count];
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

async function get_version() {
    const response = await fetch("/api/version", {
        method: "GET"
    });
    const res = await response.json();
    if (res["result"] == "OK") {
        return res["message"];
    } else {
        return "ERROR LOAD VERSION";
    }
}