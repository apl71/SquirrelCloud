async function login() {
    const login_form = document.getElementById("login_form");
    const form_data = new FormData(login_form);
    const form_json = JSON.stringify(Object.fromEntries(form_data.entries()));
    const response = await fetch("/api/login", {
        method: "POST",
        mode: "cors",
        headers: {
            "Content-Type": "application/json"
        },
        body: form_json
    });
    const res = await response.json();
    if (res["result"] != "OK") {
        alert("Login Failed. Check username and password.");
    } else {
        window.location = "/app.html";
    }
}