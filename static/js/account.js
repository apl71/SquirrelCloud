function load_account() {
    load_theme();
}

async function reset_password() {
    const reset_password_form = document.getElementById("reset_password_form");
    const form_data = new FormData(reset_password_form);
    const new_password = form_data.get("new_password");
    const confirm_password = form_data.get("confirm_password");
    if (new_password != confirm_password) {
        alert("You typed different passwords. Check it please.");
        return;
    }
    const data = {
        "old_password": form_data.get("old_password"),
        "new_password": new_password
    };
    const response = await fetch("/api/password", {
        method: "POST",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });
    const res = await response.json();
    if (res["result"] == "OK") {
        alert(res["message"]);
        window.location.href = "/login.html";
    } else {
        alert(res["message"]);
    }
}