export function loading (state) {
    const loader = $(".loader");
    if (state == "off") {
        loader.css("display", "none");
    } else {
        loader.css("display", "flex");
    }
}
