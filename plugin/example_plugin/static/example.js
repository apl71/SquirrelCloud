let start = 0;
// Number of images to load at a time
const num = 10;

async function initialize_page() {
    // load theme
    load_theme();
    // load meta
    const meta = await get_meta();
    document.getElementById("plugin_name").innerText = meta["name"];
    document.getElementById("plugin_version").innerText = meta["version"];
    document.getElementById("plugin_desc").innerText = meta["description"];
    document.getElementById("plugin_author").innerText = meta["author"];
    // load images
    load_images();
    // lazy load images
    window.addEventListener("scroll", () => {
        if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight) {
            load_images();
        }
    });
}

async function get_meta() {
    const url = "/plugin/example/info";
    const meta = await fetch(url, {
        method: "GET",
    }).then((response) => {
        return response.json();
    });
    return meta;
}

function load_images() {
    fetch("/plugin/example/get_images?start=" + String(start) + "&num=" + String(num))
        .then((response) => response.json())
        .then((data) => {
            const images = data["images"];
            images.forEach(src => {
                const photo = document.createElement("div");
                photo.classList.add("photo");
                const img = document.createElement("img");
                // api from squirrelcloud may be used
                img.setAttribute("data-src", "/api/download?file=" + src);
                img.classList.add("lazy-load");
                photo.appendChild(img);
                document.getElementById("gallery").appendChild(photo);

                const observer = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.getAttribute("data-src");
                            img.classList.remove("lazy-load");
                            observer.unobserve(img);
                        }
                    });
                }, { rootMargin: "0px 0px 100px 0px", threshold: 0.1 });
                observer.observe(img);
            });
            start += num;
        })
        .catch((error) => {
            console.error("Error:", error);
        });
}